from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from cybercore.voice.models import ActionRequest, VoiceContext


class GovernanceDecision(StrEnum):
    ALLOW = "ALLOW"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    DENY = "DENY"


@dataclass(frozen=True)
class GovernanceResult:
    decision: GovernanceDecision
    reason: str
    evidence_id: str | None = None


class OathdoGateway(Protocol):
    def evaluate(self, action: ActionRequest, context: VoiceContext) -> GovernanceResult: ...


class FailClosedOathdoGateway:
    def evaluate(self, action: ActionRequest, context: VoiceContext) -> GovernanceResult:
        return GovernanceResult(
            decision=GovernanceDecision.DENY,
            reason="OATHDO governance gateway is not configured",
        )


def normalize_oathdo_decision(
    value: str,
    *,
    reason: str = "OATHDO governance decision",
    evidence_id: str | None = None,
) -> GovernanceResult:
    try:
        decision = GovernanceDecision(value.strip().upper())
    except (AttributeError, ValueError):
        return GovernanceResult(
            decision=GovernanceDecision.DENY,
            reason="unrecognized OATHDO decision; failed closed",
            evidence_id=evidence_id,
        )
    return GovernanceResult(decision=decision, reason=reason, evidence_id=evidence_id)
