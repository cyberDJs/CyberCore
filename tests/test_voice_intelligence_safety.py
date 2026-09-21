import pytest

from cybercore.voice.intelligence.safety import SafetyIntentGuard
from cybercore.voice.models import IntentKind, Utterance, VoiceContext


def utterance(text: str) -> Utterance:
    return Utterance(id="u1", session_id="s1", actor_id="johnny", text=text)


@pytest.mark.parametrize(
    "text",
    [
        "stop",
        "Please cancel this",
        "zruš to",
        "prosím abort",
        "can you stop now",
        "could you please cancel this",
        "můžeš prosím zrušit to",
        "I need you to stop",
        "hey, stop",
        "Stop!",
        "I would like you to stop",
        "Cyber, stop",
        "Could you maybe stop this now",
        "Don't wait; stop now",
        "Please just stop now",
        "Could you quickly stop now?",
        "Just stop now",
        "Stop the process if it is running",
        "Please, Cyber, stop now",
        "Please don't wait, stop now",
        "If you're still speaking, stop now",
        "When you are done, stop",
    ],
)
def test_cancel_is_deterministic(text: str) -> None:
    result = SafetyIntentGuard().compile(utterance(text), VoiceContext())
    assert result is not None and result.kind is IntentKind.CANCEL


@pytest.mark.parametrize("text", ["schvaluju", "ano schvaluji plán", "jo udělej to", "yes do it"])
def test_approval_is_deterministic(text: str) -> None:
    result = SafetyIntentGuard().compile(utterance(text), VoiceContext())
    assert result is not None and result.kind is IntentKind.APPROVE


@pytest.mark.parametrize(
    "text", ["execute deploy", "spusť kontrolu", "proveď změnu", "run diagnostics"]
)
def test_execute_is_deterministic(text: str) -> None:
    result = SafetyIntentGuard().compile(utterance(text), VoiceContext())
    assert result is not None and result.kind is IntentKind.EXECUTE


@pytest.mark.parametrize(
    "text",
    [
        "What does approve mean?",
        "Explain the word stop",
        "Je run anglicky běžet?",
        "Please do not stop",
        "Don't cancel this",
        'Is "stop" a verb?',
        "Je „stop“ anglické sloveso?",
        "Is stop a verb?",
        "Can I cancel the deployment?",
        "The stop button is red",
        "You should not stop",
        "You must not cancel this",
        "You shouldn't stop",
        "Stop is a verb",
        "Cancel is the operation name",
        "Stop button is red",
        "Could you please not stop",
        "Stop this is what the button says",
        "Cancel the deployment is an option",
        "Don't, please, stop",
        "Do not, under any circumstances, stop",
    ],
)
def test_mentions_are_not_authority(text: str) -> None:
    assert SafetyIntentGuard().compile(utterance(text), VoiceContext()) is None
