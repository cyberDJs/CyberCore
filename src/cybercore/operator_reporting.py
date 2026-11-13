"""Presentation-only compact Czech operator reports for governed CyberCore work.

The caller MUST supply authenticated, sanitized evidence. This module performs no
provider acquisition, messaging, authorization, scheduling, or approval.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

_SHA = re.compile(r"[0-9a-f]{40}", re.ASCII)
_STATES = frozenset({"VERIFIED", "READY_FOR_MERGE", "BLOCKED", "FAILED", "UNKNOWN"})
_MATERIAL_EVENTS = frozenset(
    {
        "checks_failed",
        "checks_recovered",
        "security_finding",
        "review_finding",
        "source_drift",
        "merge_conflict",
        "merged",
        "milestone",
        "approval_required",
        "critical_evidence_missing",
    }
)


@dataclass(frozen=True)
class OperatorUpdate:
    event_kind: str
    subject: str
    sha: str
    state: str
    what: str
    why: str
    impact: str
    next_action: str
    evidence_url: str
    approval_required: bool
    changed: bool


def _brief(value: str) -> str:
    """Compact already-sanitized display text; not a secret scanner."""
    if not isinstance(value, str):
        raise ValueError("INVALID_DISPLAY_TEXT")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("EMPTY_DISPLAY_TEXT")
    return normalized[:240]


def format_operator_update(event: OperatorUpdate) -> str | None:
    """Render one meaningful event; never infer approval or CI PASS."""
    if type(event) is not OperatorUpdate:
        raise ValueError("INVALID_EVENT")
    if type(event.changed) is not bool:
        raise ValueError("INVALID_CHANGED_FLAG")
    if event.event_kind not in _MATERIAL_EVENTS or not event.changed:
        return None
    if _SHA.fullmatch(event.sha) is None:
        raise ValueError("INVALID_SHA")
    if event.state not in _STATES:
        raise ValueError("INVALID_STATE")
    if type(event.approval_required) is not bool:
        raise ValueError("INVALID_APPROVAL_FLAG")
    if not event.evidence_url.startswith("https://github.com/cyberDJs/CyberCore/"):
        raise ValueError("INVALID_EVIDENCE_URL")
    return "\n".join(
        (
            f"{_brief(event.subject)} — {event.state} · {event.sha[:12]}",
            f"Co: {_brief(event.what)}",
            f"Proč: {_brief(event.why)}",
            f"Dopad: {_brief(event.impact)}",
            f"Dál: {_brief(event.next_action)}",
            f"Souhlas: {'vyžadován' if event.approval_required else 'nyní není nutný'}",
            f"Důkaz: {event.evidence_url}",
        )
    )
