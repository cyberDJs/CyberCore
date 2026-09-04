from cybercore.voice.adapters import VadState
from cybercore.voice.barge_shadow import FreshSpeechShadowGate


def test_shadow_gate_rejects_speech_already_present_when_playback_observation_starts() -> None:
    gate = FreshSpeechShadowGate(required_silence_frames=2, required_speech_frames=3)

    results = [
        gate.observe(VadState.SPEECH, frame_sequence=sequence) for sequence in range(6)
    ]

    assert results == [False] * 6
    assert gate.snapshot.candidate is False
    assert gate.snapshot.armed is False


def test_shadow_gate_confirms_only_speech_after_a_fresh_silence_boundary() -> None:
    gate = FreshSpeechShadowGate(required_silence_frames=2, required_speech_frames=3)

    assert gate.observe(VadState.SILENCE, frame_sequence=0) is False
    assert gate.observe(VadState.SILENCE, frame_sequence=1) is False
    assert gate.snapshot.armed is True
    assert gate.observe(VadState.SPEECH, frame_sequence=2) is False
    assert gate.observe(VadState.SPEECH, frame_sequence=3) is False
    assert gate.observe(VadState.SPEECH, frame_sequence=4) is True

    snapshot = gate.snapshot
    assert snapshot.candidate is True
    assert snapshot.candidate_frame_sequence == 4
    assert snapshot.speech_frames == 3


def test_shadow_gate_requires_consecutive_speech_after_arming() -> None:
    gate = FreshSpeechShadowGate(required_silence_frames=1, required_speech_frames=2)

    gate.observe(VadState.SILENCE, frame_sequence=0)
    gate.observe(VadState.SPEECH, frame_sequence=1)
    gate.observe(VadState.SILENCE, frame_sequence=2)

    assert gate.observe(VadState.SPEECH, frame_sequence=3) is False
    assert gate.observe(VadState.SPEECH, frame_sequence=4) is True
    assert gate.snapshot.candidate_frame_sequence == 4


def test_shadow_gate_unknown_state_fails_closed_and_requires_rearming() -> None:
    gate = FreshSpeechShadowGate(required_silence_frames=1, required_speech_frames=1)

    gate.observe(VadState.SILENCE, frame_sequence=0)
    assert gate.snapshot.armed is True

    assert gate.observe(VadState.UNKNOWN, frame_sequence=1) is False
    assert gate.snapshot.armed is False
    assert gate.observe(VadState.SPEECH, frame_sequence=2) is False
    assert gate.snapshot.candidate is False

    gate.observe(VadState.SILENCE, frame_sequence=3)
    assert gate.observe(VadState.SPEECH, frame_sequence=4) is True
