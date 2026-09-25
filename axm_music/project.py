from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from typing import Any


class ProjectValidationError(ValueError):
    """Raised when canonical AXM music state is internally inconsistent."""


_ALLOWED_ORIGINS = {"human", "deterministic", "ai", "imported"}
_ALLOWED_EVENT_KINDS = {"note", "voice_line"}
_ALLOWED_QUANTIZE = {"immediate", "beat", "bar"}


def _fail(message: str) -> None:
    raise ProjectValidationError(message)


def _require(mapping: dict[str, Any], key: str, where: str) -> Any:
    if key not in mapping:
        _fail(f"{where}: missing required field '{key}'")
    return mapping[key]


def _require_id(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{where}: id must be a non-empty string")
    return value


def _require_non_negative_int(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        _fail(f"{where}: expected non-negative integer")
    return value


def _require_positive_int(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        _fail(f"{where}: expected positive integer")
    return value


def _validate_provenance(provenance: Any, where: str) -> None:
    if not isinstance(provenance, dict):
        _fail(f"{where}: provenance must be an object")
    origin = _require(provenance, "origin", where)
    if origin not in _ALLOWED_ORIGINS:
        _fail(f"{where}: unsupported provenance origin '{origin}'")
    source_id = _require(provenance, "source_id", where)
    if not isinstance(source_id, str) or not source_id.strip():
        _fail(f"{where}: provenance source_id must be a non-empty string")


def _validate_event(event: Any, clip_id: str, clip_length_ticks: int, seen: set[str]) -> None:
    where = f"clip '{clip_id}' event"
    if not isinstance(event, dict):
        _fail(f"{where}: event must be an object")
    event_id = _require_id(_require(event, "id", where), where)
    if event_id in seen:
        _fail(f"clip '{clip_id}': duplicate event id '{event_id}'")
    seen.add(event_id)

    kind = _require(event, "kind", f"event '{event_id}'")
    if kind not in _ALLOWED_EVENT_KINDS:
        _fail(f"event '{event_id}': unsupported kind '{kind}'")

    start_tick = _require_non_negative_int(
        _require(event, "start_tick", f"event '{event_id}'"),
        f"event '{event_id}' start_tick",
    )
    duration_ticks = _require_positive_int(
        _require(event, "duration_ticks", f"event '{event_id}'"),
        f"event '{event_id}' duration_ticks",
    )
    if start_tick + duration_ticks > clip_length_ticks:
        _fail(f"event '{event_id}': extends beyond clip '{clip_id}'")

    _validate_provenance(_require(event, "provenance", f"event '{event_id}'"), f"event '{event_id}'")

    if kind == "note":
        pitch = _require(event, "pitch_midi", f"event '{event_id}'")
        velocity = _require(event, "velocity", f"event '{event_id}'")
        if not isinstance(pitch, int) or isinstance(pitch, bool) or not 0 <= pitch <= 127:
            _fail(f"event '{event_id}': pitch_midi must be 0..127")
        if not isinstance(velocity, int) or isinstance(velocity, bool) or not 1 <= velocity <= 127:
            _fail(f"event '{event_id}': velocity must be 1..127")

    if kind == "voice_line":
        text = _require(event, "text", f"event '{event_id}'")
        speaker_id = _require(event, "speaker_id", f"event '{event_id}'")
        if not isinstance(text, str) or not text.strip():
            _fail(f"event '{event_id}': voice text must be non-empty")
        if not isinstance(speaker_id, str) or not speaker_id.strip():
            _fail(f"event '{event_id}': speaker_id must be non-empty")
        if "voice_identity" in event and not event.get("consent_ref"):
            _fail(f"event '{event_id}': identity-sensitive voice_identity requires consent_ref")


def _index_unique(items: Any, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        _fail(f"{label}: expected a list")
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            _fail(f"{label}[{index}]: expected an object")
        item_id = _require_id(_require(item, "id", f"{label}[{index}]"), f"{label}[{index}]")
        if item_id in result:
            _fail(f"{label}: duplicate id '{item_id}'")
        result[item_id] = item
    return result


def validate_project(project: dict[str, Any]) -> dict[str, Any]:
    """Validate and return a deep copy of canonical AXM music-project/v1 state."""
    if not isinstance(project, dict):
        _fail("project must be an object")
    if _require(project, "schema", "project") != "axm.music-project/v1":
        _fail("project: schema must be 'axm.music-project/v1'")

    _require_id(_require(project, "id", "project"), "project")
    tempo = _require(project, "tempo_bpm", "project")
    if (not isinstance(tempo, (int, float)) or isinstance(tempo, bool)
            or tempo <= 0 or (isinstance(tempo, float) and not math.isfinite(tempo))):
        _fail("project: tempo_bpm must be positive and finite")
    ppq = _require_positive_int(_require(project, "ppq", "project"), "project ppq")

    meter = _require(project, "meter", "project")
    if not isinstance(meter, dict):
        _fail("project: meter must be an object")
    numerator = _require_positive_int(_require(meter, "numerator", "meter"), "meter numerator")
    denominator = _require_positive_int(_require(meter, "denominator", "meter"), "meter denominator")
    if denominator not in {1, 2, 4, 8, 16}:
        _fail("meter: denominator must be one of 1, 2, 4, 8, 16")
    if (ppq * 4 * numerator) % denominator != 0:
        _fail("meter: ppq cannot represent this bar length exactly")

    _validate_provenance(_require(project, "provenance", "project"), "project")

    clips = _index_unique(_require(project, "clips", "project"), "clips")
    for clip_id, clip in clips.items():
        clip_length = _require_positive_int(
            _require(clip, "length_ticks", f"clip '{clip_id}'"),
            f"clip '{clip_id}' length_ticks",
        )
        _validate_provenance(_require(clip, "provenance", f"clip '{clip_id}'"), f"clip '{clip_id}'")
        events = _require(clip, "events", f"clip '{clip_id}'")
        if not isinstance(events, list):
            _fail(f"clip '{clip_id}': events must be a list")
        seen_events: set[str] = set()
        for event in events:
            _validate_event(event, clip_id, clip_length, seen_events)

    stems = _index_unique(_require(project, "stems", "project"), "stems")
    for stem_id, stem in stems.items():
        role = _require(stem, "role", f"stem '{stem_id}'")
        if not isinstance(role, str) or not role.strip():
            _fail(f"stem '{stem_id}': role must be non-empty")
        clip_ids = _require(stem, "clip_ids", f"stem '{stem_id}'")
        if not isinstance(clip_ids, list) or not clip_ids:
            _fail(f"stem '{stem_id}': clip_ids must be a non-empty list")
        for clip_id in clip_ids:
            if clip_id not in clips:
                _fail(f"stem '{stem_id}': unknown clip '{clip_id}'")

    sections = _index_unique(_require(project, "sections", "project"), "sections")
    for section_id, section in sections.items():
        _require_positive_int(
            _require(section, "length_bars", f"section '{section_id}'"),
            f"section '{section_id}' length_bars",
        )
        stem_ids = _require(section, "stem_ids", f"section '{section_id}'")
        if not isinstance(stem_ids, list) or not stem_ids:
            _fail(f"section '{section_id}': stem_ids must be a non-empty list")
        for stem_id in stem_ids:
            if stem_id not in stems:
                _fail(f"section '{section_id}': unknown stem '{stem_id}'")

    states = _index_unique(_require(project, "states", "project"), "states")
    for state_id, state in states.items():
        section_id = _require(state, "section_id", f"state '{state_id}'")
        if section_id not in sections:
            _fail(f"state '{state_id}': unknown section '{section_id}'")

    initial_state = _require(project, "initial_state", "project")
    if initial_state not in states:
        _fail(f"project: unknown initial_state '{initial_state}'")

    transitions = _index_unique(_require(project, "transitions", "project"), "transitions")
    for transition_id, transition in transitions.items():
        from_state = _require(transition, "from_state", f"transition '{transition_id}'")
        to_state = _require(transition, "to_state", f"transition '{transition_id}'")
        if from_state != "*" and from_state not in states:
            _fail(f"transition '{transition_id}': unknown from_state '{from_state}'")
        if to_state not in states:
            _fail(f"transition '{transition_id}': unknown to_state '{to_state}'")
        trigger = _require(transition, "trigger", f"transition '{transition_id}'")
        if not isinstance(trigger, str) or not trigger.strip():
            _fail(f"transition '{transition_id}': trigger must be non-empty")
        quantize = _require(transition, "quantize", f"transition '{transition_id}'")
        if quantize not in _ALLOWED_QUANTIZE:
            _fail(f"transition '{transition_id}': unsupported quantize '{quantize}'")
        priority = _require(transition, "priority", f"transition '{transition_id}'")
        if not isinstance(priority, int) or isinstance(priority, bool):
            _fail(f"transition '{transition_id}': priority must be an integer")

    return deepcopy(project)


def canonical_json(project: dict[str, Any]) -> str:
    validated = validate_project(project)
    return json.dumps(validated, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def project_hash(project: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(project).encode("utf-8")).hexdigest()
