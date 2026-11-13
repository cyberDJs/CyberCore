from types import SimpleNamespace

from cybercore.voice.adapters import VadResult, VadState
from cybercore.voice.audio import AudioFormat, AudioFrame
from cybercore.voice.barge_shadow_probe import ShadowLocalSpeechRuntime


class FakeVad:
    def evaluate(self, frame: AudioFrame) -> VadResult:
        return VadResult(VadState.SPEECH)


def test_shadow_runtime_observes_speaking_input_without_interrupt_authority() -> None:
    runtime = object.__new__(ShadowLocalSpeechRuntime)
    runtime.provider = SimpleNamespace(vad=FakeVad())
    from cybercore.voice.barge_shadow import FreshSpeechShadowGate

    runtime._barge_shadow = FreshSpeechShadowGate(
        required_silence_frames=1, required_speech_frames=1
    )
    runtime._barge_shadow._armed = True
    frame = AudioFrame(sequence=7, payload=b"\x00\x00" * 512, format=AudioFormat())

    assert runtime._observe_speaking_barge_in(frame) is False
    assert runtime.barge_in_shadow_snapshot.candidate is True
    assert runtime.barge_in_shadow_snapshot.candidate_frame_sequence == 7
