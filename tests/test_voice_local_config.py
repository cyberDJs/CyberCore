from pathlib import Path

import pytest

from cybercore.voice.local_config import (
    LocalVoiceConfig,
    LocalVoiceConfigError,
    default_local_voice_config_path,
)


def config_mapping(tmp_path: Path) -> dict[str, object]:
    return {
        "audio": {"sample_rate_hz": 16000, "channels": 1, "block_ms": 80},
        "vad": {"model": str(tmp_path / "silero.onnx")},
        "stt": {
            "tokens": str(tmp_path / "tokens.txt"),
            "encoder": str(tmp_path / "encoder.onnx"),
            "decoder": str(tmp_path / "decoder.onnx"),
            "joiner": str(tmp_path / "joiner.onnx"),
            "sample_rate_hz": 16000,
        },
        "tts": {
            "model": str(tmp_path / "tts.onnx"),
            "tokens": str(tmp_path / "tts-tokens.txt"),
            "data_dir": str(tmp_path / "espeak-ng-data"),
        },
    }


def test_local_voice_config_parses_and_reports_required_paths(tmp_path: Path) -> None:
    config = LocalVoiceConfig.from_mapping(config_mapping(tmp_path))

    assert config.audio.frames_per_block == 1280
    assert config.stt.sample_rate_hz == 16000
    required = {name: (path, kind) for name, path, kind in config.required_paths()}
    assert required["vad.model"] == (tmp_path / "silero.onnx", "file")
    assert required["tts.data_dir"] == (tmp_path / "espeak-ng-data", "dir")


def test_local_voice_config_rejects_sample_rate_mismatch(tmp_path: Path) -> None:
    raw = config_mapping(tmp_path)
    raw["stt"]["sample_rate_hz"] = 8000  # type: ignore[index]

    with pytest.raises(LocalVoiceConfigError, match="must match"):
        LocalVoiceConfig.from_mapping(raw)


def test_local_voice_config_rejects_unknown_keys(tmp_path: Path) -> None:
    raw = config_mapping(tmp_path)
    raw["audio"]["mystery"] = True  # type: ignore[index]

    with pytest.raises(LocalVoiceConfigError, match="unknown voice config field"):
        LocalVoiceConfig.from_mapping(raw)


def test_default_config_path_honors_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CYBERCORE_VOICE_CONFIG", "~/voice-test.json")

    assert default_local_voice_config_path() == Path("~/voice-test.json").expanduser()


def test_load_config_wraps_invalid_numeric_values(tmp_path: Path) -> None:
    import json

    from cybercore.voice.local_config import load_local_voice_config

    raw = config_mapping(tmp_path)
    raw["audio"]["sample_rate_hz"] = "not-a-number"  # type: ignore[index]
    path = tmp_path / "voice.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(LocalVoiceConfigError, match="invalid voice config value"):
        load_local_voice_config(path)
