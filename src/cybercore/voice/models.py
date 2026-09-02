from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping


class IntentKind(StrEnum):
    QUESTION = "question"
    SEARCH = "search"
    INSPECT = "inspect"
    PLAN = "plan"
    EXECUTE = "execute"
    APPROVE = "approve"
    CANCEL = "cancel"
    MONITOR = "monitor"
    UNKNOWN = "unknown"


class ActionRisk(StrEnum):
    READ_ONLY = "read_only"
    MUTATION = "mutation"
    CONSEQUENTIAL = "consequential"


class ResponseStatus(StrEnum):
    READY = "ready"
    NEEDS_CONTEXT = "needs_context"
    BLOCKED_CONTINUITY = "blocked_continuity"
    BLOCKED_GOVERNANCE = "blocked_governance"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_INTENT_CAPTURED = "approval_intent_captured"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Utterance:
    id: str
    session_id: str
    actor_id: str
    text: str

    def __post_init__(self) -> None:
        for name, value in (
            ("id", self.id),
            ("session_id", self.session_id),
            ("actor_id", self.actor_id),
            ("text", self.text),
        ):
            if not value.strip():
                raise ValueError(f"utterance {name} must not be empty")


@dataclass(frozen=True)
class VoiceIntent:
    id: str
    utterance_id: str
    kind: IntentKind
    operation: str
    target: str | None = None
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("intent confidence must be between 0 and 1")
        if not self.operation.strip():
            raise ValueError("intent operation must not be empty")


@dataclass(frozen=True)
class VoiceContext:
    project: str | None = None
    machine: str | None = None
    active_plan_id: str | None = None
    active_plan_revision: str | None = None
    references: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionRequest:
    intent_id: str
    operation: str
    risk: ActionRisk
    target: str | None = None
    plan_id: str | None = None
    plan_revision: str | None = None
    scope: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    @property
    def mutating(self) -> bool:
        return self.risk in {ActionRisk.MUTATION, ActionRisk.CONSEQUENTIAL}

    @property
    def has_bound_plan(self) -> bool:
        return bool(self.plan_id and self.plan_revision)


@dataclass(frozen=True)
class VoiceResponse:
    status: ResponseStatus
    message: str
    intent: VoiceIntent
    action: ActionRequest | None = None
    continuity_decision: str | None = None
    governance_decision: str | None = None
    approval_id: str | None = None
    approval_intent_id: str | None = None
