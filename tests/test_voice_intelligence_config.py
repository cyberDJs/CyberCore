import json

import pytest

from cybercore.voice.intelligence.config import (
    IntelligenceConfigError,
    load_intelligence_config,
)


def test_missing_default_config_keeps_intelligence_disabled(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CYBERCORE_VOICE_INTELLIGENCE_CONFIG", raising=False)

    config = load_intelligence_config()

    assert config.enabled is False
    assert config.provider == "ollama"


def test_explicit_missing_config_fails_closed(tmp_path) -> None:
    with pytest.raises(IntelligenceConfigError, match="not found"):
        load_intelligence_config(tmp_path / "missing.json")


def test_unknown_config_field_is_rejected(tmp_path) -> None:
    path = tmp_path / "voice-intelligence.json"
    path.write_text(json.dumps({"enabled": True, "surprise": "nope"}), encoding="utf-8")

    with pytest.raises(IntelligenceConfigError, match="unknown intelligence config field"):
        load_intelligence_config(path)


def test_enabled_loopback_ollama_config_loads(tmp_path) -> None:
    path = tmp_path / "voice-intelligence.json"
    path.write_text(
        json.dumps(
            {
                "enabled": True,
                "provider": "ollama",
                "model": "qwen3:4b",
                "base_url": "http://127.0.0.1:11434",
                "timeout_s": 5,
                "min_confidence": 0.8,
                "max_answer_chars": 900,
            }
        ),
        encoding="utf-8",
    )

    config = load_intelligence_config(path)

    assert config.enabled is True
    assert config.model == "qwen3:4b"
    assert config.min_confidence == 0.8
