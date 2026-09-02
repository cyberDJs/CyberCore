from pathlib import Path
from types import SimpleNamespace

from cybercore.voice.adapters import TranscriptResult, VadResult, VadState
from cybercore.voice.audio import AudioFormat, AudioFrame
from cybercore.voice.local_config import (
    LocalAudioConfig,
    LocalVoiceConfig,
    SherpaSttConfig,
    SherpaTtsConfig,
    SherpaVadConfig,
)
from cybercore.voice.local_runtime import (
    LocalSpeechRuntime,
    run_local_voice_doctor,
)
from cybercore.voice.realtime import RealtimeState
from cybercore.voice.session import SessionStatus, VoiceSession


class FakeVad:
    def evaluate(self, frame: AudioFrame) -> VadResult:
        return VadResult(VadState.SPEECH)


class FakeStt:
    def __init__(self) -> None:
        self.endpoint_detected = False
        self.frames = 0

    def push(self, frame: AudioFrame):
        self.frames += 1
        self.endpoint_detected = True
        return ()

    def finish(self) -> TranscriptResult:
        return TranscriptResult("inspect CyberCore", language="en")

    def reset(self) -> None:
        self.endpoint_detected = False
        self.frames = 0


class FakeTts:
    def __init__(self) -> None:
        self.frames: list[AudioFrame] = []
        self.cancelled = 0

    def start(self, text: str) -> None:
        self.frames = [frame(20), frame(21)]

    def pull(self) -> AudioFrame | None:
        if not self.frames:
            return None
        return self.frames.pop(0)

    def cancel(self) -> None:
        self.cancelled += 1
        self.frames.clear()

    def reset(self) -> None:
        self.frames.clear()


class FakeInput:
    def __init__(
        self,
        blocking: list[AudioFrame],
        nonblocking: list[AudioFrame] | None = None,
    ) -> None:
        self.blocking = list(blocking)
        self.nonblocking = list(nonblocking or [])
        self.started = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    def read_frame(self) -> AudioFrame:
        return self.blocking.pop(0)

    def read_frame_if_available(self) -> AudioFrame | None:
        if not self.nonblocking:
            return None
        return self.nonblocking.pop(0)

    def close(self) -> None:
        self.closed = True


class FakeTransport:
    def __init__(self) -> None:
        self.sent: list[int] = []
        self.flush_count = 0
        self.closed = False

    def send(self, audio_frame: AudioFrame) -> None:
        self.sent.append(audio_frame.sequence)

    def flush_output(self) -> None:
        self.flush_count += 1

    def close(self) -> None:
        self.closed = True


class FakeSoundDevice:
    __version__ = "0.5.6"

    def __init__(self) -> None:
        self.default = SimpleNamespace(device=(0, 1))

    def check_input_settings(self, **kwargs) -> None:
        pass

    def check_output_settings(self, **kwargs) -> None:
        pass

    def query_devices(self):
        return [
            {
                "name": "Mic",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 16000.0,
            },
            {
                "name": "Speaker",
                "max_input_channels": 0,
                "max_output_channels": 1,
                "default_samplerate": 16000.0,
            },
        ]


class FakeSherpaApi:
    __version__ = "1.13.6"
    GenerationConfig = object
    OfflineTts = object
    OfflineTtsConfig = object
    OfflineTtsModelConfig = object
    OfflineTtsVitsModelConfig = object
    OnlineRecognizer = object
    VadModelConfig = object
    VoiceActivityDetector = object


def frame(sequence: int) -> AudioFrame:
    return AudioFrame(sequence=sequence, payload=b"\x01\x00" * 512, format=AudioFormat())


def config(tmp_path: Path) -> LocalVoiceConfig:
    files = [
        "silero.onnx",
        "tokens.txt",
        "encoder.onnx",
        "decoder.onnx",
        "joiner.onnx",
        "tts.onnx",
        "tts-tokens.txt",
    ]
    for name in files:
        (tmp_path / name).write_bytes(b"test")
    data_dir = tmp_path / "espeak-ng-data"
    data_dir.mkdir()
    return LocalVoiceConfig(
        audio=LocalAudioConfig(input_device=0, output_device=1),
        vad=SherpaVadConfig(model=tmp_path / "silero.onnx"),
        stt=SherpaSttConfig(
            tokens=tmp_path / "tokens.txt",
            encoder=tmp_path / "encoder.onnx",
            decoder=tmp_path / "decoder.onnx",
            joiner=tmp_path / "joiner.onnx",
        ),
        tts=SherpaTtsConfig(
            model=tmp_path / "tts.onnx",
            tokens=tmp_path / "tts-tokens.txt",
            data_dir=data_dir,
        ),
    )


def make_runtime(*, nonblocking: list[AudioFrame] | None = None) -> tuple:
    session = VoiceSession("session-local")
    stt = FakeStt()
    tts = FakeTts()
    provider = SimpleNamespace(vad=FakeVad(), stt=stt, tts=tts)
    source = FakeInput([frame(1)], nonblocking=nonblocking)
    transport = FakeTransport()
    runtime = LocalSpeechRuntime(
        config=SimpleNamespace(),
        session=session,
        provider=provider,
        audio_input=source,
        transport=transport,
    )
    return runtime, session, stt, tts, source, transport


def test_capture_utterance_bridges_real_input_into_existing_contract() -> None:
    runtime, session, _, _, source, _ = make_runtime()

    utterance = runtime.capture_utterance(actor_id="johnny", utterance_id="u-1")

    assert utterance is not None
    assert utterance.text == "inspect CyberCore"
    assert utterance.session_id == session.session_id
    assert source.started is True
    assert runtime.realtime.state is RealtimeState.PROCESSING


def test_speak_sends_audio_and_returns_to_idle() -> None:
    runtime, _, _, _, _, transport = make_runtime()
    runtime.capture_utterance(actor_id="johnny", utterance_id="u-1")

    interrupted = runtime.speak("done")

    assert interrupted is False
    assert transport.sent == [20, 21]
    assert runtime.realtime.state is RealtimeState.IDLE


def test_speech_during_playback_uses_existing_barge_in_semantics() -> None:
    runtime, session, _, tts, _, transport = make_runtime(nonblocking=[frame(2)])
    runtime.capture_utterance(actor_id="johnny", utterance_id="u-1")

    interrupted = runtime.speak("long answer")

    assert interrupted is True
    assert runtime.realtime.state is RealtimeState.INTERRUPTED
    assert session.status is SessionStatus.INTERRUPTED
    assert tts.cancelled == 1
    assert transport.flush_count == 1
    assert transport.sent == []


def test_doctor_checks_dependencies_models_and_audio_without_loading_models(tmp_path: Path) -> None:
    checks = run_local_voice_doctor(
        config=config(tmp_path),
        sounddevice_module=FakeSoundDevice(),
        sherpa_module=FakeSherpaApi,
    )

    assert checks
    assert all(check.successful for check in checks)
    assert {check.name for check in checks} >= {
        "dependency:sounddevice",
        "dependency:sherpa-onnx",
        "config",
        "audio",
        "provider:sherpa-onnx",
    }
