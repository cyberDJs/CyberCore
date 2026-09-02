from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SessionStatus(StrEnum):
    ACTIVE = "active"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"


@dataclass
class VoiceSession:
    session_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    active_intent_id: str | None = None
    interruption_reason: str | None = None
    references: dict[str, str] = field(default_factory=dict)

    def remember(self, name: str, value: str) -> None:
        if self.status is SessionStatus.CANCELLED:
            raise RuntimeError("cannot update a cancelled voice session")
        if not name.strip() or not value.strip():
            raise ValueError("session references require a non-empty name and value")
        self.references[name] = value

    def resolve(self, name: str) -> str | None:
        return self.references.get(name)

    def mark_intent(self, intent_id: str) -> None:
        if self.status is SessionStatus.CANCELLED:
            raise RuntimeError("cannot activate an intent on a cancelled voice session")
        if not intent_id.strip():
            raise ValueError("intent id must not be empty")
        self.active_intent_id = intent_id

    def interrupt(self, reason: str) -> None:
        if self.status is SessionStatus.CANCELLED:
            return
        self.status = SessionStatus.INTERRUPTED
        self.interruption_reason = reason.strip() or "operator interruption"

    def resume(self) -> None:
        if self.status is SessionStatus.CANCELLED:
            raise RuntimeError("cannot resume a cancelled voice session")
        self.status = SessionStatus.ACTIVE
        self.interruption_reason = None

    def cancel(self) -> None:
        self.status = SessionStatus.CANCELLED
        self.active_intent_id = None
