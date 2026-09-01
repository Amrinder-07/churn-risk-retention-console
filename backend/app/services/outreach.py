"""Outreach state-machine rules."""

from __future__ import annotations

from typing import Dict, List


OUTREACH_STATES = ("NOT_CONTACTED", "IN_PROGRESS", "RESOLVED")

ALLOWED_TRANSITIONS: Dict[str, List[str]] = {
    "NOT_CONTACTED": ["IN_PROGRESS"],
    "IN_PROGRESS": ["RESOLVED"],
    "RESOLVED": [],
}


def normalize_status(status: str) -> str:
    if not isinstance(status, str):
        raise ValueError("outreach status must be a string")
    normalized = status.strip().upper()
    if normalized not in OUTREACH_STATES:
        raise ValueError(
            f"Unknown outreach status '{status}'. Expected one of: {', '.join(OUTREACH_STATES)}"
        )
    return normalized


def validate_transition(current_status: str, requested_status: str) -> str:
    current = normalize_status(current_status)
    requested = normalize_status(requested_status)

    # Treat a repeated PATCH as an idempotent no-op.
    if current == requested:
        return requested

    if requested not in ALLOWED_TRANSITIONS[current]:
        allowed = ALLOWED_TRANSITIONS[current]
        allowed_text = ", ".join(allowed) if allowed else "none"
        raise ValueError(
            f"Invalid outreach transition: {current} -> {requested}. "
            f"Allowed next status(es): {allowed_text}."
        )
    return requested


def allowed_next_statuses(current_status: str) -> List[str]:
    current = normalize_status(current_status)
    return list(ALLOWED_TRANSITIONS[current])


def get_state_machine_info() -> Dict[str, object]:
    return {
        "states": list(OUTREACH_STATES),
        "allowed_transitions": {key: list(value) for key, value in ALLOWED_TRANSITIONS.items()},
        "idempotent_updates": True,
    }
