from cybercore.integrations.howedo import ContinuityDecision, ContinuityResult
from cybercore.integrations.oathdo import GovernanceDecision, GovernanceResult
from cybercore.voice.approval import ApprovalCheck
from cybercore.voice.models import (
    ActionRequest,
    ActionRisk,
    ResponseStatus,
    Utterance,
    VoiceContext,
)
from cybercore.voice.router import VoiceRouter
from cybercore.voice.session import SessionStatus, VoiceSession


class Planner:
    def __init__(self, action: ActionRequest) -> None:
        self.action = action

    def plan(self, intent, context):
        return self.action


class Howedo:
    def __init__(self, decision: ContinuityDecision) -> None:
        self.decision = decision

    def evaluate(self, action, context):
        return ContinuityResult(self.decision, f"continuity={self.decision.value}")


class Oathdo:
    def __init__(self, decision: GovernanceDecision) -> None:
        self.decision = decision

    def evaluate(self, action, context):
        return GovernanceResult(self.decision, f"governance={self.decision.value}")


class Approval:
    def __init__(self, authorized: bool) -> None:
        self.authorized = authorized

    def verify(self, action):
        return ApprovalCheck(
            self.authorized,
            "approval ok" if self.authorized else "matching CCL approval required",
            "approval-1" if self.authorized else None,
        )


def make_utterance(text: str) -> Utterance:
    return Utterance(id="u1", session_id="s1", actor_id="johnny", text=text)


def test_read_only_action_can_become_ready() -> None:
    router = VoiceRouter(
        planner=Planner(ActionRequest("i", "inspect", ActionRisk.READ_ONLY)),
        howedo=Howedo(ContinuityDecision.CONTINUE),
        oathdo=Oathdo(GovernanceDecision.ALLOW),
    )

    response = router.handle(make_utterance("inspect staging"), VoiceContext())

    assert response.status is ResponseStatus.READY
    assert response.approval_id is None


def test_mutation_never_becomes_ready_without_ccl_approval() -> None:
    router = VoiceRouter(
        planner=Planner(
            ActionRequest(
                "i",
                "deploy",
                ActionRisk.MUTATION,
                plan_id="plan-1",
                plan_revision="1",
            )
        ),
        howedo=Howedo(ContinuityDecision.CONTINUE),
        oathdo=Oathdo(GovernanceDecision.ALLOW),
        approval_verifier=Approval(False),
    )

    response = router.handle(make_utterance("execute deploy"), VoiceContext())

    assert response.status is ResponseStatus.APPROVAL_REQUIRED


def test_mutation_with_matching_approval_can_become_ready() -> None:
    router = VoiceRouter(
        planner=Planner(
            ActionRequest(
                "i",
                "deploy",
                ActionRisk.MUTATION,
                plan_id="plan-1",
                plan_revision="1",
            )
        ),
        howedo=Howedo(ContinuityDecision.CONTINUE),
        oathdo=Oathdo(GovernanceDecision.ALLOW),
        approval_verifier=Approval(True),
    )

    response = router.handle(make_utterance("execute deploy"), VoiceContext())

    assert response.status is ResponseStatus.READY
    assert response.approval_id == "approval-1"


def test_voice_approve_is_only_captured_intent() -> None:
    router = VoiceRouter(
        planner=Planner(
            ActionRequest(
                "i",
                "deploy",
                ActionRisk.MUTATION,
                plan_id="plan-1",
                plan_revision="1",
            )
        ),
        howedo=Howedo(ContinuityDecision.CONTINUE),
        oathdo=Oathdo(GovernanceDecision.APPROVAL_REQUIRED),
        approval_verifier=Approval(True),
    )

    response = router.handle(make_utterance("approve this plan"), VoiceContext())

    assert response.status is ResponseStatus.APPROVAL_INTENT_CAPTURED
    assert response.approval_intent_id == "voice-approval:u1"
    assert response.approval_id is None


def test_howedo_revalidate_blocks_before_governance() -> None:
    router = VoiceRouter(
        planner=Planner(ActionRequest("i", "inspect", ActionRisk.READ_ONLY)),
        howedo=Howedo(ContinuityDecision.REVALIDATE),
        oathdo=Oathdo(GovernanceDecision.ALLOW),
    )

    response = router.handle(make_utterance("inspect staging"), VoiceContext())

    assert response.status is ResponseStatus.BLOCKED_CONTINUITY
    assert response.continuity_decision == "REVALIDATE"


def test_cancel_stops_session_without_planning() -> None:
    session = VoiceSession("s1")
    router = VoiceRouter()

    response = router.handle(make_utterance("cancel"), VoiceContext(), session=session)

    assert response.status is ResponseStatus.CANCELLED
    assert session.status is SessionStatus.CANCELLED
