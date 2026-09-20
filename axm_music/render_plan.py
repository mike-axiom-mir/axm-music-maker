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


def _realization_requirement(event: dict[str, Any], stem_id: str) -> dict[str, Any]:
    if event["kind"] == "note":
        return {
            "status": "unbound",
            "kind": "instrument",
            "binding_scope": "stem",
            "binding_key": stem_id,
            "target": "axm-audio-fabric",
        }
    return {
        "status": "unbound",
        "kind": "voice_performance",
        "binding_scope": "event",
        "binding_key": event["id"],
        "target": "axm-audio-fabric",
    }


def build_render_plan(project: dict[str, Any], state_id: str) -> dict[str, Any]:
    """Build one explicit section-relative render plan for a named adaptive state.

    v1 intentionally supports exactly one clip per stem because the canonical
    music model does not yet represent clip placement or looping. Silently
    sequencing or repeating multiple clips here would invent musical state that
    is not present in the project.

    The returned plan is deterministic for the same validated project + state.
    It is suitable as an integration contract for Audio Fabric, but it is not an
    Audio Fabric cue and it does not claim that any event is renderable until an
    explicit realization binding exists.
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

    plan_stems: list[dict[str, Any]] = []
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
            events.append(
                {
                    "event_id": event["id"],
                    "clip_id": clip_id,
                    "kind": event["kind"],
                    "start_tick": event["start_tick"],
                    "duration_ticks": event["duration_ticks"],
                    "provenance": deepcopy(event["provenance"]),
                    "payload": _event_payload(event),
                    "realization": _realization_requirement(event, stem_id),
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
        "stems": plan_stems,
        "truth_boundary": {
            "audio_rendered": False,
            "realizations_bound": False,
            "looping_inferred": False,
            "mix_decisions_inferred": False,
        },
    }
