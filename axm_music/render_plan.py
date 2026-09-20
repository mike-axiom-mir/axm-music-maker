"""Deterministic bridge from canonical music state to an explicit audio render plan.

The plan deliberately stops before synthesis/rendering. Music Maker owns musical
intent and timing; Audio Fabric owns audio realization. A plan therefore carries
all source identities/provenance and explicit realization requirements without
inventing hidden instruments, voice takes, looping, or mix decisions.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .project import ProjectValidationError, project_hash, validate_project


RENDER_PLAN_SCHEMA = "axm.music-audio-render-plan/v1"


def _index(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in items}


def _bar_ticks(project: dict[str, Any]) -> int:
    meter = project["meter"]
    return project["ppq"] * 4 * meter["numerator"] // meter["denominator"]


def _event_payload(event: dict[str, Any]) -> dict[str, Any]:
    if event["kind"] == "note":
        return {
            "pitch_midi": event["pitch_midi"],
            "velocity": event["velocity"],
        }

    payload = {
        "speaker_id": event["speaker_id"],
        "text": event["text"],
    }
    for key in ("voice_identity", "consent_ref"):
        if key in event:
            payload[key] = deepcopy(event[key])
    return payload


def _normalize_realization_bindings(
    bindings: list[dict[str, Any]] | None,
    *,
    valid_stem_ids: set[str],
    valid_event_ids: set[str],
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    """Validate caller-provided realization bindings without inventing defaults.

    Bindings are external realization intent, not part of the canonical music
    project. They are copied into the render plan so the selected realization is
    inspectable and can carry its own provenance.
    """
    if bindings is None:
        return [], {}
    if not isinstance(bindings, list):
        raise ProjectValidationError("render plan: realization_bindings must be an array")

    normalized: list[dict[str, Any]] = []
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for position, binding in enumerate(bindings):
        label = f"render plan: realization_bindings[{position}]"
        if not isinstance(binding, dict):
            raise ProjectValidationError(f"{label} must be an object")
        scope = binding.get("scope")
        if scope not in {"stem", "event"}:
            raise ProjectValidationError(f"{label}.scope must be 'stem' or 'event'")
        key = binding.get("key")
        if not isinstance(key, str) or not key.strip():
            raise ProjectValidationError(f"{label}.key must be a non-empty string")
        binding_ref = binding.get("binding_ref")
        if not isinstance(binding_ref, str) or not binding_ref.strip():
            raise ProjectValidationError(f"{label}.binding_ref must be a non-empty string")

        valid_keys = valid_stem_ids if scope == "stem" else valid_event_ids
        if key not in valid_keys:
            raise ProjectValidationError(
                f"{label} references unknown {scope} '{key}' in the selected state"
            )
        identity = (scope, key)
        if identity in indexed:
            raise ProjectValidationError(f"{label} duplicates {scope} binding '{key}'")

        record = {
            "scope": scope,
            "key": key,
            "binding_ref": binding_ref,
        }
        if "provenance" in binding:
            if not isinstance(binding["provenance"], dict):
                raise ProjectValidationError(f"{label}.provenance must be an object when supplied")
            record["provenance"] = deepcopy(binding["provenance"])
        normalized.append(record)
        indexed[identity] = record

    normalized.sort(key=lambda item: (item["scope"], item["key"], item["binding_ref"]))
    return normalized, indexed


def _realization_requirement(
    event: dict[str, Any],
    stem_id: str,
    binding_index: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    kind = "instrument" if event["kind"] == "note" else "voice_performance"
    event_binding = binding_index.get(("event", event["id"]))
    stem_binding = binding_index.get(("stem", stem_id)) if event["kind"] == "note" else None

    if event_binding is not None and stem_binding is not None:
        raise ProjectValidationError(
            f"render plan: event '{event['id']}' is ambiguously bound by both event and stem scope"
        )

    binding = event_binding or stem_binding
    if binding is None:
        return {
            "status": "unbound",
            "kind": kind,
            "binding_scope": "stem" if event["kind"] == "note" else "event",
            "binding_key": stem_id if event["kind"] == "note" else event["id"],
            "target": "axm-audio-fabric",
        }

    result = {
        "status": "bound",
        "kind": kind,
        "binding_scope": binding["scope"],
        "binding_key": binding["key"],
        "binding_ref": binding["binding_ref"],
        "target": "axm-audio-fabric",
    }
    if "provenance" in binding:
        result["binding_provenance"] = deepcopy(binding["provenance"])
    return result


def build_render_plan(
    project: dict[str, Any],
    state_id: str,
    realization_bindings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build one explicit section-relative render plan for a named adaptive state.

    v1 intentionally supports exactly one clip per stem because the canonical
    music model does not yet represent clip placement or looping. Silently
    sequencing or repeating multiple clips here would invent musical state that
    is not present in the project.

    ``realization_bindings`` are optional caller-provided refs. Omitting them
    preserves the original unbound plan. A stem binding applies only to note
    events in that stem. An event binding applies to exactly one event. Supplying
    both scopes for the same note is rejected rather than silently choosing a
    precedence rule.

    The returned plan is deterministic for the same validated project + state +
    bindings. It is suitable as an integration contract for Audio Fabric, but it
    is not itself an Audio Fabric cue and does not synthesize any audio.
    """
    if not isinstance(state_id, str) or not state_id.strip():
        raise ProjectValidationError("render plan: state_id must be a non-empty string")

    canonical = validate_project(project)
    clips = _index(canonical["clips"])
    stems = _index(canonical["stems"])
    sections = _index(canonical["sections"])
    states = _index(canonical["states"])

    if state_id not in states:
        raise ProjectValidationError(f"render plan: unknown state '{state_id}'")

    section_id = states[state_id]["section_id"]
    section = sections[section_id]
    section_length_ticks = section["length_bars"] * _bar_ticks(canonical)

    valid_stem_ids = set(section["stem_ids"])
    valid_event_ids: set[str] = set()
    for stem_id in section["stem_ids"]:
        for clip_id in stems[stem_id]["clip_ids"]:
            valid_event_ids.update(event["id"] for event in clips[clip_id]["events"])

    normalized_bindings, binding_index = _normalize_realization_bindings(
        realization_bindings,
        valid_stem_ids=valid_stem_ids,
        valid_event_ids=valid_event_ids,
    )

    plan_stems: list[dict[str, Any]] = []
    event_count = 0
    bound_event_count = 0
    for stem_id in section["stem_ids"]:
        stem = stems[stem_id]
        clip_ids = stem["clip_ids"]
        if len(clip_ids) != 1:
            raise ProjectValidationError(
                f"render plan: stem '{stem_id}' has {len(clip_ids)} clips; "
                "v1 requires exactly one clip because placement/loop semantics are not canonical yet"
            )

        clip_id = clip_ids[0]
        clip = clips[clip_id]
        if clip["length_ticks"] > section_length_ticks:
            raise ProjectValidationError(
                f"render plan: clip '{clip_id}' exceeds section '{section_id}' length"
            )

        events: list[dict[str, Any]] = []
        for event in sorted(clip["events"], key=lambda item: (item["start_tick"], item["id"])):
            realization = _realization_requirement(event, stem_id, binding_index)
            event_count += 1
            if realization["status"] == "bound":
                bound_event_count += 1
            events.append(
                {
                    "event_id": event["id"],
                    "clip_id": clip_id,
                    "kind": event["kind"],
                    "start_tick": event["start_tick"],
                    "duration_ticks": event["duration_ticks"],
                    "provenance": deepcopy(event["provenance"]),
                    "payload": _event_payload(event),
                    "realization": realization,
                }
            )

        plan_stems.append(
            {
                "stem_id": stem_id,
                "role": stem["role"],
                "clip_id": clip_id,
                "clip_provenance": deepcopy(clip["provenance"]),
                "playback_policy": "once_at_section_start",
                "clip_length_ticks": clip["length_ticks"],
                "uncovered_tail_ticks": section_length_ticks - clip["length_ticks"],
                "events": events,
            }
        )

    return {
        "schema": RENDER_PLAN_SCHEMA,
        "target": "axm-audio-fabric",
        "project_id": canonical["id"],
        "project_sha256": project_hash(canonical),
        "project_provenance": deepcopy(canonical["provenance"]),
        "state_id": state_id,
        "section_id": section_id,
        "tempo_bpm": canonical["tempo_bpm"],
        "ppq": canonical["ppq"],
        "meter": deepcopy(canonical["meter"]),
        "section_length_ticks": section_length_ticks,
        "timing_scope": "section_relative_ticks",
        "realization_bindings": normalized_bindings,
        "stems": plan_stems,
        "truth_boundary": {
            "audio_rendered": False,
            "realizations_bound": event_count > 0 and bound_event_count == event_count,
            "bound_event_count": bound_event_count,
            "event_count": event_count,
            "looping_inferred": False,
            "mix_decisions_inferred": False,
        },
    }
