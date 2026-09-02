from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Mapping


class LocalVoiceConfigError(ValueError):
    pass


def _section(data: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = data.get(name)
    if not isinstance(value, Mapping):
        raise LocalVoiceConfigError(f"voice config section '{name}' is required")
    return value


def _path(value: object, *, field_name: str, required: bool = True) -> Path | None:
    if value in (None, ""):
        if required:
            raise LocalVoiceConfigError(f"voice config field '{field_name}' is required")
        return None
    if not isinstance(value, str):
        raise LocalVoiceConfigError(f"voice config field '{field_name}' must be a path string")
    return Path(value).expanduser()


def _device(value: object, *, field_name: str) -> int | str | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise LocalVoiceConfigError(
            f"voice config field '{field_name}' must be an integer, string, or null"
        )
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _unknown(section: Mapping[str, Any], allowed: set[str], name: str) -> None:
    unknown = sorted(set(section) - allowed)
    if unknown:
        raise LocalVoiceConfigError(
            f"unknown voice config field(s) in '{name}': {', '.join(unknown)}"
        )


@dataclass(frozen=True)
class LocalAudioConfig:
    sample_rate_hz: int = 16000
    channels: int = 1
    block_ms: int = 80
    input_device: int | str | None = None
    output_device: int | str | None = None

    def __post_init__(self) -> None:
        if self.sample_rate_hz <= 0:
            raise LocalVoiceConfigError("audio sample_rate_hz must be positive")
        if self.channels != 1:
            raise LocalVoiceConfigError(
                "WB-0038 local speech runtime currently requires mono audio"
            )
        if not 10 <= self.block_ms <= 500:
            raise LocalVoiceConfigError("audio block_ms must be between 10 and 500")

    @property
    def frames_per_block(self) -> int:
        return max(1, round(self.sample_rate_hz * self.block_ms / 1000))

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> LocalAudioConfig:
        allowed = {
            "sample_rate_hz",
            "channels",
            "block_ms",
            "input_device",
            "output_device",
        }
        _unknown(data, allowed, "audio")
        return cls(
            sample_rate_hz=int(data.get("sample_rate_hz", 16000)),
            channels=int(data.get("channels", 1)),
            block_ms=int(data.get("block_ms", 80)),
            input_device=_device(data.get("input_device"), field_name="audio.input_device"),
            output_device=_device(data.get("output_device"), field_name="audio.output_device"),
        )


@dataclass(frozen=True)
class SherpaVadConfig:
    model: Path
    threshold: float = 0.5
    min_silence_duration: float = 0.5
    min_speech_duration: float = 0.25
    max_speech_duration: float = 20.0
    window_size: int = 512
    buffer_seconds: float = 30.0
    provider: str = "cpu"
    num_threads: int = 1

    def __post_init__(self) -> None:
        if not 0.0 < self.threshold < 1.0:
            raise LocalVoiceConfigError("vad threshold must be between 0 and 1")
        if self.min_silence_duration < 0 or self.min_speech_duration < 0:
            raise LocalVoiceConfigError("vad minimum durations must not be negative")
        if self.max_speech_duration <= 0 or self.window_size <= 0 or self.buffer_seconds <= 0:
            raise LocalVoiceConfigError("vad duration, window, and buffer values must be positive")
        if self.num_threads <= 0:
            raise LocalVoiceConfigError("vad num_threads must be positive")
        if not self.provider.strip():
            raise LocalVoiceConfigError("vad provider must not be empty")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> SherpaVadConfig:
        allowed = {
            "model",
            "threshold",
            "min_silence_duration",
            "min_speech_duration",
            "max_speech_duration",
            "window_size",
            "buffer_seconds",
            "provider",
            "num_threads",
        }
        _unknown(data, allowed, "vad")
        model = _path(data.get("model"), field_name="vad.model")
        assert model is not None
        return cls(
            model=model,
            threshold=float(data.get("threshold", 0.5)),
            min_silence_duration=float(data.get("min_silence_duration", 0.5)),
            min_speech_duration=float(data.get("min_speech_duration", 0.25)),
            max_speech_duration=float(data.get("max_speech_duration", 20.0)),
            window_size=int(data.get("window_size", 512)),
            buffer_seconds=float(data.get("buffer_seconds", 30.0)),
            provider=str(data.get("provider", "cpu")),
            num_threads=int(data.get("num_threads", 1)),
        )


@dataclass(frozen=True)
class SherpaSttConfig:
    tokens: Path
    encoder: Path
    decoder: Path
    joiner: Path
    sample_rate_hz: int = 16000
    provider: str = "cpu"
    num_threads: int = 2
    decoding_method: str = "greedy_search"
    trailing_silence_s: float = 0.8
    max_utterance_s: float = 30.0

    def __post_init__(self) -> None:
        if self.sample_rate_hz <= 0:
            raise LocalVoiceConfigError("stt sample_rate_hz must be positive")
        if self.num_threads <= 0:
            raise LocalVoiceConfigError("stt num_threads must be positive")
        if self.decoding_method not in {"greedy_search", "modified_beam_search"}:
            raise LocalVoiceConfigError("unsupported stt decoding_method")
        if self.trailing_silence_s <= 0 or self.max_utterance_s <= 0:
            raise LocalVoiceConfigError("stt endpoint durations must be positive")
        if not self.provider.strip():
            raise LocalVoiceConfigError("stt provider must not be empty")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> SherpaSttConfig:
        allowed = {
            "tokens",
            "encoder",
            "decoder",
            "joiner",
            "sample_rate_hz",
            "provider",
            "num_threads",
            "decoding_method",
            "trailing_silence_s",
            "max_utterance_s",
        }
        _unknown(data, allowed, "stt")
        tokens = _path(data.get("tokens"), field_name="stt.tokens")
        encoder = _path(data.get("encoder"), field_name="stt.encoder")
        decoder = _path(data.get("decoder"), field_name="stt.decoder")
        joiner = _path(data.get("joiner"), field_name="stt.joiner")
        assert (
            tokens is not None
            and encoder is not None
            and decoder is not None
            and joiner is not None
        )
        return cls(
            tokens=tokens,
            encoder=encoder,
            decoder=decoder,
            joiner=joiner,
            sample_rate_hz=int(data.get("sample_rate_hz", 16000)),
            provider=str(data.get("provider", "cpu")),
            num_threads=int(data.get("num_threads", 2)),
            decoding_method=str(data.get("decoding_method", "greedy_search")),
            trailing_silence_s=float(data.get("trailing_silence_s", 0.8)),
            max_utterance_s=float(data.get("max_utterance_s", 30.0)),
        )


@dataclass(frozen=True)
class SherpaTtsConfig:
    model: Path
    tokens: Path
    data_dir: Path | None = None
    lexicon: Path | None = None
    provider: str = "cpu"
    num_threads: int = 2
    speaker_id: int = 0
    speed: float = 1.0
    silence_scale: float = 0.2
    chunk_ms: int = 80

    def __post_init__(self) -> None:
        if self.num_threads <= 0:
            raise LocalVoiceConfigError("tts num_threads must be positive")
        if self.speaker_id < 0:
            raise LocalVoiceConfigError("tts speaker_id must not be negative")
        if self.speed <= 0:
            raise LocalVoiceConfigError("tts speed must be positive")
        if not 0.01 <= self.silence_scale <= 10.0:
            raise LocalVoiceConfigError("tts silence_scale must be between 0.01 and 10")
        if not 20 <= self.chunk_ms <= 500:
            raise LocalVoiceConfigError("tts chunk_ms must be between 20 and 500")
        if not self.provider.strip():
            raise LocalVoiceConfigError("tts provider must not be empty")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> SherpaTtsConfig:
        allowed = {
            "model",
            "tokens",
            "data_dir",
            "lexicon",
            "provider",
            "num_threads",
            "speaker_id",
            "speed",
            "silence_scale",
            "chunk_ms",
        }
        _unknown(data, allowed, "tts")
        model = _path(data.get("model"), field_name="tts.model")
        tokens = _path(data.get("tokens"), field_name="tts.tokens")
        assert model is not None and tokens is not None
        return cls(
            model=model,
            tokens=tokens,
            data_dir=_path(data.get("data_dir"), field_name="tts.data_dir", required=False),
            lexicon=_path(data.get("lexicon"), field_name="tts.lexicon", required=False),
            provider=str(data.get("provider", "cpu")),
            num_threads=int(data.get("num_threads", 2)),
            speaker_id=int(data.get("speaker_id", 0)),
            speed=float(data.get("speed", 1.0)),
            silence_scale=float(data.get("silence_scale", 0.2)),
            chunk_ms=int(data.get("chunk_ms", 80)),
        )


@dataclass(frozen=True)
class LocalVoiceConfig:
    audio: LocalAudioConfig
    vad: SherpaVadConfig
    stt: SherpaSttConfig
    tts: SherpaTtsConfig

    def __post_init__(self) -> None:
        if self.audio.sample_rate_hz != self.stt.sample_rate_hz:
            raise LocalVoiceConfigError(
                "audio.sample_rate_hz must match stt.sample_rate_hz for WB-0038"
            )

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> LocalVoiceConfig:
        _unknown(data, {"audio", "vad", "stt", "tts"}, "root")
        return cls(
            audio=LocalAudioConfig.from_mapping(_section(data, "audio")),
            vad=SherpaVadConfig.from_mapping(_section(data, "vad")),
            stt=SherpaSttConfig.from_mapping(_section(data, "stt")),
            tts=SherpaTtsConfig.from_mapping(_section(data, "tts")),
        )

    def required_paths(self) -> tuple[tuple[str, Path, str], ...]:
        items: list[tuple[str, Path, str]] = [
            ("vad.model", self.vad.model, "file"),
            ("stt.tokens", self.stt.tokens, "file"),
            ("stt.encoder", self.stt.encoder, "file"),
            ("stt.decoder", self.stt.decoder, "file"),
            ("stt.joiner", self.stt.joiner, "file"),
            ("tts.model", self.tts.model, "file"),
            ("tts.tokens", self.tts.tokens, "file"),
        ]
        if self.tts.data_dir is not None:
            items.append(("tts.data_dir", self.tts.data_dir, "dir"))
        if self.tts.lexicon is not None:
            items.append(("tts.lexicon", self.tts.lexicon, "file"))
        return tuple(items)


def default_local_voice_config_path() -> Path:
    configured = os.getenv("CYBERCORE_VOICE_CONFIG")
    if configured:
        return Path(configured).expanduser()
    return Path("~/.config/cybercore/voice-local.json").expanduser()


def load_local_voice_config(path: Path | str | None = None) -> LocalVoiceConfig:
    config_path = Path(path).expanduser() if path is not None else default_local_voice_config_path()
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LocalVoiceConfigError(f"voice config not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise LocalVoiceConfigError(
            f"voice config is not valid JSON: {config_path}: {exc.msg}"
        ) from exc
    if not isinstance(raw, Mapping):
        raise LocalVoiceConfigError("voice config root must be a JSON object")
    try:
        return LocalVoiceConfig.from_mapping(raw)
    except LocalVoiceConfigError:
        raise
    except (TypeError, ValueError) as exc:
        raise LocalVoiceConfigError(f"invalid voice config value: {exc}") from exc
