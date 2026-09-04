from array import array
from types import SimpleNamespace

from cybercore.voice.devices import SoundDeviceInput
from cybercore.voice.local_config import LocalAudioConfig
from cybercore.voice.local_runtime import LocalSpeechRuntime
from cybercore.voice.realtime import RealtimeState


class ScriptedInputStream:
    def __init__(self, reads: list[tuple[int, bytes]]) -> None:
        self.reads = list(reads)
        self.read_available = 0
        self.read_calls: list[int] = []
        self.started = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    def read(self, frames: int):
        self.read_calls.append(frames)
        expected_frames, payload = self.reads.pop(0)
        assert frames == expected_frames
        return payload, False

    def stop(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


class ScriptedSoundDevice:
    __version__ = "0.5.6"

    def __init__(self, stream: ScriptedInputStream) -> None:
        self.default = SimpleNamespace(device=(0, 1))
        self.stream = stream

    def query_devices(self):
        return [
            {
                "name": "Mic",
                "hostapi": 0,
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 48000.0,
            },
            {
                "name": "Speaker",
                "hostapi": 0,
                "max_input_channels": 0,
                "max_output_channels": 2,
                "default_samplerate": 48000.0,
            },
        ]

    def RawInputStream(self, **kwargs):
        return self.stream


def pcm(samples: list[int]) -> bytes:
    return array("h", samples).tobytes()


def samples(payload: bytes) -> array:
    result = array("h")
    result.frombytes(payload)
    return result


def test_sounddevice_input_preserves_fir_state_across_capture_blocks() -> None:
    block_frames = 3840
    first = [0] * block_frames
    first[-1] = 20000
    second = [0] * block_frames
    stream = ScriptedInputStream(
        [
            (block_frames, pcm(first)),
            (block_frames, pcm(second)),
        ]
    )
    source = SoundDeviceInput(
        LocalAudioConfig(),
        sounddevice_module=ScriptedSoundDevice(stream),
    )

    first_frame = source.read_frame()
    second_frame = source.read_frame()
    second_samples = samples(second_frame.payload)

    assert len(first_frame.payload) == 1280 * 2
    assert len(second_frame.payload) == 1280 * 2
    assert sum(abs(value) for value in second_samples[:20]) > 1000


def test_discard_pending_input_consumes_partial_block_and_resets_fir_history() -> None:
    block_frames = 3840
    first = [0] * block_frames
    first[-1] = 20000
    second = [0] * block_frames
    stream = ScriptedInputStream(
        [
            (block_frames, pcm(first)),
            (120, pcm([0] * 120)),
            (block_frames, pcm(second)),
        ]
    )
    source = SoundDeviceInput(
        LocalAudioConfig(),
        sounddevice_module=ScriptedSoundDevice(stream),
    )

    source.read_frame()
    stream.read_available = 120
    source.discard_pending_input()
    stream.read_available = 0
    after_discard = source.read_frame()

    assert stream.read_calls == [block_frames, 120, block_frames]
    assert not any(samples(after_discard.payload)[:20])


class DiscardAwareInput:
    def __init__(self) -> None:
        self.discard_count = 0
        self.started = False

    def start(self) -> None:
        self.started = True

    def read_frame_if_available(self):
        return None

    def discard_pending_input(self) -> None:
        self.discard_count += 1


def test_speak_discards_partial_capture_residue_before_returning_to_listening() -> None:
    source = DiscardAwareInput()
    runtime = object.__new__(LocalSpeechRuntime)
    runtime.audio_input = source
    runtime.realtime = SimpleNamespace(state=RealtimeState.IDLE)
    runtime._opened = True
    runtime._begin_speaking_with_live_input = lambda text: None

    interrupted = runtime.speak("done")

    assert interrupted is False
    assert source.discard_count == 1
