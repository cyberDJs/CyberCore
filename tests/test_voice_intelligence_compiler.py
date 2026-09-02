import json

from cybercore.voice.intelligence.compiler import ModelIntentCompiler
from cybercore.voice.intelligence.contracts import CompileSource
from cybercore.voice.models import IntentKind, Utterance, VoiceContext


class Client:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = 0

    def complete(self, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return self.response


def utterance(text: str) -> Utterance:
    return Utterance(id="u1", session_id="s1", actor_id="johnny", text=text)


def response(**overrides):
    value = {
        "kind": "question",
        "operation": "explain",
        "target": None,
        "language": "cs",
        "confidence": 0.97,
        "needs_live_data": False,
    }
    value.update(overrides)
    return json.dumps(value)


def test_safety_path_never_calls_model() -> None:
    client = Client(response())
    result = ModelIntentCompiler(client).compile_result(utterance("zruš to"), VoiceContext())
    assert result.intent.kind is IntentKind.CANCEL
    assert result.source is CompileSource.SAFETY
    assert client.calls == 0


def test_valid_model_classification_is_used() -> None:
    client = Client(response(kind="inspect", operation="project_status", needs_live_data=True))
    result = ModelIntentCompiler(client).compile_result(
        utterance("Jak je na tom CyberCore?"), VoiceContext(project="CyberCore")
    )
    assert result.intent.kind is IntentKind.INSPECT
    assert result.intent.operation == "project_status"
    assert result.needs_live_data is True
    assert result.source is CompileSource.MODEL


def test_invalid_json_falls_back() -> None:
    result = ModelIntentCompiler(Client("not-json")).compile_result(
        utterance("Co je Docker?"), VoiceContext()
    )
    assert result.source is CompileSource.FALLBACK
    assert result.intent.kind is IntentKind.QUESTION


def test_low_confidence_falls_back() -> None:
    result = ModelIntentCompiler(Client(response(confidence=0.2))).compile_result(
        utterance("Co je Docker?"), VoiceContext()
    )
    assert result.source is CompileSource.FALLBACK


def test_model_outage_falls_back() -> None:
    result = ModelIntentCompiler(Client(error=RuntimeError("down"))).compile_result(
        utterance("Co je Docker?"), VoiceContext()
    )
    assert result.source is CompileSource.FALLBACK


def test_dangerous_model_output_cannot_be_promoted_by_fallback() -> None:
    malicious = json.dumps(
        {
            "kind": "approve",
            "operation": "approve",
            "target": None,
            "language": "cs",
            "confidence": 1.0,
            "needs_live_data": False,
        }
    )
    result = ModelIntentCompiler(Client(malicious)).compile_result(
        utterance("Co znamená approve?"), VoiceContext()
    )
    assert result.intent.kind is IntentKind.UNKNOWN
    assert result.source is CompileSource.FALLBACK
