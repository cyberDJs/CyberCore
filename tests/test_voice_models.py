import pytest

from cybercore.voice.models import ActionRequest, ActionRisk, IntentKind, Utterance, VoiceIntent


def test_utterance_rejects_empty_text() -> None:
    with pytest.raises(ValueError):
        Utterance(id="u1", session_id="s1", actor_id="a1", text="   ")


def test_action_mutation_and_plan_binding() -> None:
    action = ActionRequest(
        intent_id="i1",
        operation="deploy",
        risk=ActionRisk.MUTATION,
        plan_id="plan-1",
        plan_revision="7",
    )
    assert action.mutating is True
    assert action.has_bound_plan is True


def test_intent_confidence_is_bounded() -> None:
    with pytest.raises(ValueError):
        VoiceIntent(
            id="i1",
            utterance_id="u1",
            kind=IntentKind.INSPECT,
            operation="inspect",
            confidence=1.1,
        )
