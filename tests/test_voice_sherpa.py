from pathlib import Path
from types import SimpleNamespace

import pytest

from cybercore.voice.audio import AudioFormat, AudioFrame
from cybercore.voice.local_config import SherpaSttConfig, SherpaTtsConfig, SherpaVadConfig
from cybercore.voice.providers.sherpa import (
    SherpaSttAdapter,
    SherpaTtsAdapter,
    SherpaVadAdapter,
    floats_to_pcm_s16le,
    pcm_s16le_to_floats,
)


class FakeSileroConfig:
    pass


class FakeVadModelConfig:
    def __init__(self) -> None:
        self.silero_vad = FakeSileroConfig()

    def validate(self) -> bool:
        return True


class FakeVadDetector:
    def __init__(self, config, buffer_size_in_seconds: float) -> None:
        self.speech = False

    def accept_waveform(self, samples) -> None:
        self.speech = any(abs(sample) > 0.01 for sample in samples)

    def is_speech_detected(self) -> bool:
        return self.speech

    def empty(self) -> bool:
        return True

    def pop(self) -> None:
        pass


class FakeStream:
    def __init__(self) -> None:
        self.count = 0
        self.ready = False
        self.finished = False

    def accept_waveform(self, sample_rate: int, samples) -> None:
        self.count += 1
        self.ready = True

    def input_finished(self) -> None:
        self.finished = True
        self.ready = True


class FakeRecognizer:
    def __init__(self, kwargs: dict[str, object]) -> None:
        self.kwargs = kwargs

    def create_stream(self) -> FakeStream:
        return FakeStream()

    def is_ready(self, stream: FakeStream) -> bool:
        return stream.ready

    def decode_stream(self, stream: FakeStream) -> None:
        stream.ready = False

    def get_result_all(self, stream: FakeStream):
        text = "hello world" if stream.count else ""
        return SimpleNamespace(text=text)

    def is_endpoint(self, stream: FakeStream) -> bool:
        return stream.count >= 1


class FakeOnlineRecognizer:
    last_kwargs: dict[str, object] | None = None

    @classmethod
    def from_transducer(cls, **kwargs):
        cls.last_kwargs = kwargs
        return FakeRecognizer(kwargs)


class FakeTtsConfig:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def validate(self) -> bool:
        return True


class FakeOfflineTts:
    def __init__(self, config) -> None:
        self.config = config

    def generate(self, text: str, generation):
        return SimpleNamespace(samples=[0.25] * 2400, sample_rate=24000)


class FakeGenerationConfig:
    sid = 0
    speed = 1.0
    silence_scale = 0.2


class FakeSherpa:
    __version__ = "1.13.6"
    VadModelConfig = FakeVadModelConfig
    VoiceActivityDetector = FakeVadDetector
    OnlineRecognizer = FakeOnlineRecognizer
    OfflineTtsVitsModelConfig = FakeTtsConfig
    OfflineTtsModelConfig = FakeTtsConfig
    OfflineTtsConfig = FakeTtsConfig
    OfflineTts = FakeOfflineTts
    GenerationConfig = FakeGenerationConfig


def frame(sequence: int, value: int = 2000) -> AudioFrame:
    payload = int(value).to_bytes(2, "little", signed=True) * 512
    return AudioFrame(sequence=sequence, payload=payload, format=AudioFormat())


def test_pcm_conversion_round_trip() -> None:
    payload = floats_to_pcm_s16le([-1.0, -0.5, 0.0, 0.5, 1.0])
    values = pcm_s16le_to_floats(payload)

    assert values[0] <= -0.999
    assert values[2] == 0.0
    assert values[-1] >= 0.999


def test_sherpa_vad_maps_detected_speech(tmp_path: Path) -> None:
    adapter = SherpaVadAdapter(
        SherpaVadConfig(model=tmp_path / "silero.onnx"),
        sherpa_module=FakeSherpa,
    )

    assert adapter.evaluate(frame(1)).state.value == "speech"
    assert adapter.evaluate(frame(2, value=0)).state.value == "silence"


def test_sherpa_streaming_stt_uses_transducer_contract(tmp_path: Path) -> None:
    config = SherpaSttConfig(
        tokens=tmp_path / "tokens.txt",
        encoder=tmp_path / "encoder.onnx",
        decoder=tmp_path / "decoder.onnx",
        joiner=tmp_path / "joiner.onnx",
    )
    adapter = SherpaSttAdapter(config, sherpa_module=FakeSherpa)

    deltas = adapter.push(frame(1))
    assert deltas[0].text == "hello world"
    assert adapter.endpoint_detected is True
    assert adapter.finish().text == "hello world"  # type: ignore[union-attr]
    assert FakeOnlineRecognizer.last_kwargs["enable_endpoint_detection"] is True

    adapter.reset()
    assert adapter.endpoint_detected is False


def test_sherpa_tts_chunks_generated_audio(tmp_path: Path) -> None:
    config = SherpaTtsConfig(
        model=tmp_path / "tts.onnx",
        tokens=tmp_path / "tokens.txt",
        chunk_ms=50,
    )
    adapter = SherpaTtsAdapter(config, sherpa_module=FakeSherpa)

    adapter.start("hello")
    first = adapter.pull()
    second = adapter.pull()

    assert first is not None
    assert second is not None
    assert first.format.sample_rate_hz == 24000
    assert first.duration_ms == pytest.approx(50.0)
    assert adapter.pull() is None
