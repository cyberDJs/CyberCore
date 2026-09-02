from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cybercore.voice.models import ActionRequest, Utterance


@dataclass(frozen=True)
class ApprovalCheck:
    authorized: bool
    reason: str
    approval_id: str | None = None


class ApprovalVerifier(Protocol):
    def verify(self, action: ActionRequest) -> ApprovalCheck: ...


class DenyAllApprovalVerifier:
    def verify(self, action: ActionRequest) -> ApprovalCheck:
        return ApprovalCheck(
            authorized=False,
            reason="no matching CyberCore approval verifier was configured",
        )


@dataclass(frozen=True)
class VoiceApprovalIntent:
    id: str
    session_id: str
    actor_id: str
    utterance_id: str
    plan_id: str
    plan_revision: str
    scope: tuple[str, ...]

    @property
    def is_authorization(self) -> bool:
        return False


def capture_voice_approval_intent(
    utterance: Utterance,
    action: ActionRequest,
) -> VoiceApprovalIntent:
    if not action.plan_id or not action.plan_revision:
        raise ValueError("voice approval intent requires an exact plan id and revision")
    return VoiceApprovalIntent(
        id=f"voice-approval:{utterance.id}",
        session_id=utterance.session_id,
        actor_id=utterance.actor_id,
        utterance_id=utterance.id,
        plan_id=action.plan_id,
        plan_revision=action.plan_revision,
        scope=action.scope,
    )
