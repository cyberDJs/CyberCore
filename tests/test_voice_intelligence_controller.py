import json

from cybercore.voice.intelligence.compiler import ModelIntentCompiler
from cybercore.voice.intelligence.composer import ModelResponseComposer
from cybercore.voice.intelligence.controller import IntelligentVoiceController
from cybercore.voice.models import IntentKind, Utterance, VoiceContext
from cybercore.voice.session import SessionStatus, VoiceSession


class SequenceClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def complete(self, **kwargs):
        self.calls += 1
        return self.responses.pop(0)


def intent(kind="question", needs_live_data=False, language="cs"):
    return json.dumps(
        {
            "kind": kind,
            "operation": "project_status" if kind == "inspect" else "explain",
            "target": "CyberCore" if kind == "inspect" else None,
            "language": language,
            "confidence": 0.98,
            "needs_live_data": needs_live_data,
        }
    )


def utterance(text):
    return Utterance(id="u1", session_id="s1", actor_id="johnny", text=text)


def controller(client):
    return IntelligentVoiceController(
        compiler=ModelIntentCompiler(client),
        composer=ModelResponseComposer(client),
    )


def test_general_question_gets_model_answer() -> None:
    client = SequenceClient([intent(), "Docker is a container platform."])
    response = controller(client).handle(utterance("Co je Docker?"), VoiceContext())
    assert response.status == "answered"
    assert response.message.startswith("Docker")
    assert client.calls == 2


def test_live_question_is_not_answered_from_model_memory() -> None:
    client = SequenceClient([intent(kind="inspect", needs_live_data=True)])
    response = controller(client).handle(
        utterance("Jak je na tom CyberCore?"), VoiceContext(project="CyberCore")
    )
    assert response.status == "needs_live_data"
    assert "nic si nebudu domýšlet" in response.message
    assert client.calls == 1


def test_cancel_uses_existing_router_and_cancels_session() -> None:
    client = SequenceClient([])
    session = VoiceSession("s1")
    response = controller(client).handle(utterance("stop"), VoiceContext(), session=session)
    assert response.cancelled is True
    assert session.status is SessionStatus.CANCELLED
    assert client.calls == 0


def test_non_question_model_intent_remains_bounded_by_router() -> None:
    client = SequenceClient([intent(kind="plan", needs_live_data=False)])
    response = controller(client).handle(utterance("Naplánuj kontrolu"), VoiceContext())
    assert response.intent.kind is IntentKind.PLAN
    assert response.status == "needs_context"
