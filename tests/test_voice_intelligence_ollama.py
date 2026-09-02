import json
import pytest

from cybercore.voice.intelligence.config import IntelligenceConfig
from cybercore.voice.intelligence.ollama import ModelTransportError, OllamaModelClient


def config(**kwargs):
    values = {"enabled": True, "model": "qwen3:4b"}
    values.update(kwargs)
    return IntelligenceConfig(**values)


def test_ollama_rejects_remote_endpoint() -> None:
    with pytest.raises(ValueError, match="loopback"):
        OllamaModelClient(config(base_url="http://example.com:11434"))


def test_ollama_rejects_credentials_in_url() -> None:
    with pytest.raises(ValueError, match="credentials"):
        OllamaModelClient(config(base_url="http://user:pass@127.0.0.1:11434"))


def test_ollama_sends_nonstreaming_schema_request() -> None:
    captured = {}

    def transport(url, payload, timeout):
        captured.update(url=url, payload=json.loads(payload), timeout=timeout)
        return json.dumps({"message": {"content": '{"ok":true}'}}).encode()

    client = OllamaModelClient(config(), transport=transport)
    result = client.complete(
        system="system",
        user="user",
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
    )
    assert result == '{"ok":true}'
    assert captured["url"] == "http://127.0.0.1:11434/api/chat"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["think"] is False
    assert captured["payload"]["format"]["type"] == "object"


def test_ollama_rejects_invalid_response_envelope() -> None:
    client = OllamaModelClient(config(), transport=lambda *_: b"{}")
    with pytest.raises(ModelTransportError, match="invalid response"):
        client.complete(system="s", user="u")
