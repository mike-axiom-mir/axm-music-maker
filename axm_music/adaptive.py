from __future__ import annotations

from typing import Any

from .project import project_hash, validate_project


def _quantized_tick(project: dict[str, Any], request_tick: int, quantize: str) -> int:
    if quantize == "immediate":
        return request_tick

    ppq = project["ppq"]
    if quantize == "beat":
        quantum = ppq
    else:
        meter = project["meter"]
        quantum = ppq * 4 * meter["numerator"] // meter["denominator"]

    if request_tick % quantum == 0:
        return request_tick
    return ((request_tick // quantum) + 1) * quantum


def resolve_transition(
    project: dict[str, Any],
    *,
    current_state: str,
    trigger: str,
    request_tick: int,
) -> dict[str, Any]:
    """Resolve one explicit adaptive-music trigger into an inspectable receipt.

    Selection is deterministic: highest integer priority wins; equal priority is
    broken by lexicographically smallest transition id. No hidden random choice
    or model inference occurs here.
    """
    canonical = validate_project(project)
    states = {state["id"] for state in canonical["states"]}
    if current_state not in states:
        raise ValueError(f"unknown current_state '{current_state}'")
    if not isinstance(trigger, str) or not trigger.strip():
        raise ValueError("trigger must be a non-empty string")
    if not isinstance(request_tick, int) or isinstance(request_tick, bool) or request_tick < 0:
        raise ValueError("request_tick must be a non-negative integer")

    candidates = [
        transition
        for transition in canonical["transitions"]
        if transition["trigger"] == trigger
        and transition["from_state"] in {current_state, "*"}
    ]
    candidates.sort(key=lambda transition: (-transition["priority"], transition["id"]))

    base_receipt = {
        "schema": "axm.adaptive-transition-receipt/v1",
        "project_id": canonical["id"],
        "project_hash": project_hash(canonical),
        "current_state": current_state,
        "trigger": trigger,
        "request_tick": request_tick,
    }

    if not candidates:
        return {
            **base_receipt,
            "status": "no_transition",
            "transition_id": None,
            "next_state": current_state,
            "effective_tick": request_tick,
        }

    selected = candidates[0]
    return {
        **base_receipt,
        "status": "scheduled",
        "transition_id": selected["id"],
        "next_state": selected["to_state"],
        "effective_tick": _quantized_tick(canonical, request_tick, selected["quantize"]),
        "quantize": selected["quantize"],
        "priority": selected["priority"],
    }
