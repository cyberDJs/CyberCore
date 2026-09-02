import pytest

from cybercore.voice.approval import capture_voice_approval_intent
from cybercore.voice.models import ActionRequest, ActionRisk, Utterance


def test_voice_approval_intent_is_never_authorization() -> None:
    utterance = Utterance(id="u1", session_id="s1", actor_id="johnny", text="approve")
    action = ActionRequest(
        intent_id="i1",
        operation="deploy",
        risk=ActionRisk.MUTATION,
        plan_id="plan-1",
        plan_revision="3",
        scope=("staging",),
    )

    captured = capture_voice_approval_intent(utterance, action)

    assert captured.plan_id == "plan-1"
    assert captured.plan_revision == "3"
    assert captured.scope == ("staging",)
    assert captured.is_authorization is False


def test_voice_approval_requires_exact_plan_revision() -> None:
    utterance = Utterance(id="u1", session_id="s1", actor_id="johnny", text="approve")
    action = ActionRequest(
        intent_id="i1",
        operation="deploy",
        risk=ActionRisk.MUTATION,
        plan_id="plan-1",
    )

    with pytest.raises(ValueError):
        capture_voice_approval_intent(utterance, action)
