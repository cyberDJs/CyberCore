import pytest

from cybercore.voice.intelligence.safety import SafetyIntentGuard
from cybercore.voice.models import IntentKind, Utterance, VoiceContext


def utterance(text: str) -> Utterance:
    return Utterance(id="u1", session_id="s1", actor_id="johnny", text=text)


@pytest.mark.parametrize("text", ["stop", "Please cancel this", "zruš to", "prosím abort"])
def test_cancel_is_deterministic(text: str) -> None:
    result = SafetyIntentGuard().compile(utterance(text), VoiceContext())
    assert result is not None and result.kind is IntentKind.CANCEL


@pytest.mark.parametrize("text", ["schvaluju", "ano schvaluji plán", "jo udělej to", "yes do it"])
def test_approval_is_deterministic(text: str) -> None:
    result = SafetyIntentGuard().compile(utterance(text), VoiceContext())
    assert result is not None and result.kind is IntentKind.APPROVE


@pytest.mark.parametrize(
    "text",
    ["execute deploy", "spusť kontrolu", "proveď změnu", "run diagnostics"],
)
def test_execute_is_deterministic(text: str) -> None:
    result = SafetyIntentGuard().compile(utterance(text), VoiceContext())
    assert result is not None and result.kind is IntentKind.EXECUTE


@pytest.mark.parametrize(
    "text",
    ["What does approve mean?", "Explain the word stop", "Je run anglicky běžet?"],
)
def test_mentions_are_not_authority(text: str) -> None:
    assert SafetyIntentGuard().compile(utterance(text), VoiceContext()) is None
