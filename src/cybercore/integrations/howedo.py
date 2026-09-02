from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from cybercore.voice.models import ActionRequest, VoiceContext


class ContinuityDecision(StrEnum):
    CONTINUE = "CONTINUE"
    PAUSE = "PAUSE"
    REVALIDATE = "REVALIDATE"
    ABORT = "ABORT"
    RECOVER = "RECOVER"


@dataclass(frozen=True)
class ContinuityResult:
    decision: ContinuityDecision
    reason: str
    witness_id: str | None = None

    @property
    def allows_standard_progress(self) -> bool:
        return self.decision is ContinuityDecision.CONTINUE


class HowedoGateway(Protocol):
    def evaluate(self, action: ActionRequest, context: VoiceContext) -> ContinuityResult: ...


class FailClosedHowedoGateway:
    def evaluate(self, action: ActionRequest, context: VoiceContext) -> ContinuityResult:
        return ContinuityResult(
            decision=ContinuityDecision.ABORT,
            reason="HOWEDO continuity gateway is not configured",
        )


def normalize_howedo_decision(
    value: str,
    *,
    reason: str = "HOWEDO continuity decision",
    witness_id: str | None = None,
) -> ContinuityResult:
    try:
        decision = ContinuityDecision(value.strip().upper())
    except (AttributeError, ValueError):
        return ContinuityResult(
            decision=ContinuityDecision.ABORT,
            reason="unrecognized HOWEDO decision; failed closed",
            witness_id=witness_id,
        )
    return ContinuityResult(decision=decision, reason=reason, witness_id=witness_id)
