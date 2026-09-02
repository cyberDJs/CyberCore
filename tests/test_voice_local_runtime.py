from pathlib import Path
import time
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
    def __init__(self) -> None:
        self.reset_count = 0

    def evaluate(self, audio_frame: AudioFrame) -> VadResult:
        state = VadState.SILENCE if audio_frame.sequence == 99 else VadState.SPEECH
        return VadResult(state)

    def reset(self) -> None:
        self.reset_count += 1


class DelayedSpeechVad(FakeVad):
    def __init__(self, speech_sequence: int) -> None:
        super().__init__()
        self.speech_sequence = speech_sequence

    def evaluate(self, audio_frame: AudioFrame) -> VadResult:
        state = (
            VadState.SPEECH if audio_frame.sequence == self.speech_sequence else VadState.SILENCE
        )
        return VadResult(state)


class FakeStt:
    def __init__(self) -> None:
        self.endpoint_detected = False
        self.frames = 0
        self.sequences: list[int] = []

    def push(self, audio_frame: AudioFrame):
        self.frames += 1
        self.sequences.append(audio_frame.sequence)
        self.endpoint_detected = True
        return ()

    def finish(self) -> TranscriptResult:
        return TranscriptResult("inspect CyberCore", language="en")

    def reset(self) -> None:
        self.endpoint_detected = False
        self.frames = 0
        self.sequences.clear()


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


class LongFakeTts(FakeTts):
    def start(self, text: str) -> None:
        self.frames = [frame(sequence) for sequence in range(20, 26)]


class SlowFakeTts(FakeTts):
    def start(self, text: str) -> None:
        time.sleep(0.08)
        if self.cancelled:
            return
        super().start(text)


class FakeInput:
    def __init__(
        self,
        blocking: list[AudioFrame],
        nonblocking: list[AudioFrame | None] | None = None,
    ) -> None:
        self.blocking = list(blocking)
        self.nonblocking = list(nonblocking or [])
        self.started = False
        self.closed = False
        self.nonblocking_reads = 0

    def start(self) -> None:
        self.started = True

    def read_frame(self) -> AudioFrame:
        return self.blocking.pop(0)

    def read_frame_if_available(self) -> AudioFrame | None:
        self.nonblocking_reads += 1
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


class PlaybackAwareFakeInput(FakeInput):
    def __init__(self, transport: FakeTransport, *, speech_after_sends: int) -> None:
        super().__init__([frame(1)])
        self.transport = transport
        self.speech_after_sends = speech_after_sends
        self.delivered_playback_speech = False

    def read_frame_if_available(self) -> AudioFrame | None:
        self.nonblocking_reads += 1
        if (
            len(self.transport.sent) >= self.speech_after_sends
            and not self.delivered_playback_speech
        ):
            self.delivered_playback_speech = True
            return frame(2)
        return None


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
                "default_samplerate": 48000.0,
            },
            {
                "name": "Speaker",
                "max_input_channels": 0,
                "max_output_channels": 1,
                "default_samplerate": 48000.0,
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


def make_runtime(
    *,
    nonblocking: list[AudioFrame | None] | None = None,
    tts: FakeTts | None = None,
    vad: FakeVad | None = None,
    blocking: list[AudioFrame] | None = None,
    block_ms: int = 80,
) -> tuple:
    session = VoiceSession("session-local")
    stt = FakeStt()
    selected_tts = tts or FakeTts()
    selected_vad = vad or FakeVad()
    provider = SimpleNamespace(vad=selected_vad, stt=stt, tts=selected_tts)
    source = FakeInput(blocking or [frame(1)], nonblocking=nonblocking)
    transport = FakeTransport()
    runtime = LocalSpeechRuntime(
        config=SimpleNamespace(audio=SimpleNamespace(block_ms=block_ms)),
        session=session,
        provider=provider,
        audio_input=source,
        transport=transport,
    )
    return runtime, session, stt, selected_tts, source, transport


def test_capture_utterance_bridges_real_input_into_existing_contract() -> None:
    runtime, session, stt, _, source, _ = make_runtime()

    utterance = runtime.capture_utterance(actor_id="johnny", utterance_id="u-1")

    assert utterance is not None
    assert utterance.text == "inspect CyberCore"
    assert utterance.session_id == session.session_id
    assert source.started is True
    assert stt.sequences == [1]
    assert runtime.realtime.state is RealtimeState.PROCESSING
    assert runtime.provider.vad.reset_count == 2


def test_capture_replays_bounded_preroll_before_speech_onset() -> None:
    runtime, _, stt, _, _, _ = make_runtime(
        vad=DelayedSpeechVad(speech_sequence=8),
        blocking=[frame(sequence) for sequence in range(9)],
        block_ms=100,
    )

    utterance = runtime.capture_utterance(actor_id="johnny", utterance_id="u-1")

    assert utterance is not None
    assert stt.sequences == [3, 4, 5, 6, 7, 8]
    assert runtime.provider.vad.reset_count == 2
    assert runtime.realtime.state is RealtimeState.PROCESSING


def test_speak_sends_audio_and_returns_to_idle() -> None:
    runtime, _, _, _, _, transport = make_runtime()
    runtime.capture_utterance(actor_id="johnny", utterance_id="u-1")

    interrupted = runtime.speak("done")

    assert interrupted is False
    assert transport.sent == [20, 21]
    assert runtime.realtime.state is RealtimeState.IDLE


def test_local_playback_is_safe_half_duplex_and_drains_mic_speech() -> None:
    long_tts = LongFakeTts()
    runtime, session, _, tts, _, transport = make_runtime(tts=long_tts)
    source = PlaybackAwareFakeInput(transport, speech_after_sends=1)
    runtime.audio_input = source
    runtime.capture_utterance(actor_id="johnny", utterance_id="u-1")

    interrupted = runtime.speak("long answer")

    assert interrupted is False
    assert runtime.realtime.state is RealtimeState.IDLE
    assert session.status is SessionStatus.ACTIVE
    assert tts.cancelled == 0
    assert transport.flush_count == 0
    assert transport.sent == [20, 21, 22, 23, 24, 25]
    assert source.delivered_playback_speech is True
    assert source.nonblocking_reads > 0


def test_microphone_is_drained_while_synchronous_tts_is_generating() -> None:
    slow_tts = SlowFakeTts()
    runtime, _, _, _, source, transport = make_runtime(
        nonblocking=[frame(99)],
        tts=slow_tts,
    )
    runtime.capture_utterance(actor_id="johnny", utterance_id="u-1")

    interrupted = runtime.speak("slow answer")

    assert interrupted is False
    assert source.nonblocking_reads > 0
    assert transport.sent == [20, 21]
    assert runtime.realtime.state is RealtimeState.IDLE


def test_speech_captured_during_synchronous_tts_is_drained_not_interpreted() -> None:
    slow_tts = SlowFakeTts()
    runtime, session, _, tts, source, transport = make_runtime(
        nonblocking=[frame(2)],
        tts=slow_tts,
    )
    runtime.capture_utterance(actor_id="johnny", utterance_id="u-1")

    interrupted = runtime.speak("slow answer")

    assert interrupted is False
    assert source.nonblocking_reads > 0
    assert runtime.realtime.state is RealtimeState.IDLE
    assert session.status is SessionStatus.ACTIVE
    assert tts.cancelled == 0
    assert transport.flush_count == 0
    assert transport.sent == [20, 21]


def test_doctor_reports_native_capture_to_model_rate(tmp_path: Path) -> None:
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
    audio_check = next(check for check in checks if check.name == "audio")
    assert "capture 48000 Hz -> model 16000 Hz" in audio_check.detail
