from cybercore.voice.adapters import VadState
from cybercore.voice.audio import AudioFormat, AudioFrame
from cybercore.voice.local_interruption import (
    LocalInterruptionDecision,
    LocalInterruptionProbe,
    LocalPlaybackContext,
    LocalPlaybackPhase,
)


def frame(sequence: int) -> AudioFrame:
    return AudioFrame(sequence=sequence, payload=b"\x01\x00" * 160, format=AudioFormat())


def test_probe_discards_non_playback_microphone_frames() -> None:
    probe = LocalInterruptionProbe()

    evidence = probe.observe(
        frame(1),
        vad_state=VadState.SPEECH,
        playback=LocalPlaybackContext(),
    )

    assert evidence.decision is LocalInterruptionDecision.DISCARD
    assert evidence.reason == "microphone frame was outside local playback"
    assert evidence.speech_run_frames == 0


def test_probe_observes_but_does_not_confirm_by_default() -> None:
    probe = LocalInterruptionProbe(min_confirming_speech_frames=2)
    playback = LocalPlaybackContext(
        phase=LocalPlaybackPhase.PLAYING,
        output_frame_sequence=20,
        mic_rms=1200.0,
        output_rms=900.0,
        echo_correlation=0.10,
    )

    first = probe.observe(frame(1), vad_state=VadState.SPEECH, playback=playback)
    second = probe.observe(frame(2), vad_state=VadState.SPEECH, playback=playback)

    assert first.decision is LocalInterruptionDecision.OBSERVE
    assert second.decision is LocalInterruptionDecision.OBSERVE
    assert second.speech_run_frames == 2
    assert second.output_frame_sequence == 20
    assert second.reason == "candidate playback-time speech observed while interruption is disabled"


def test_probe_discards_echo_like_speech_and_resets_run() -> None:
    probe = LocalInterruptionProbe(min_confirming_speech_frames=2, max_echo_correlation=0.70)
    clean_playback = LocalPlaybackContext(
        phase=LocalPlaybackPhase.PLAYING,
        echo_correlation=0.20,
    )
    echo_playback = LocalPlaybackContext(
        phase=LocalPlaybackPhase.PLAYING,
        echo_correlation=0.95,
    )

    observed = probe.observe(frame(1), vad_state=VadState.SPEECH, playback=clean_playback)
    discarded = probe.observe(frame(2), vad_state=VadState.SPEECH, playback=echo_playback)

    assert observed.decision is LocalInterruptionDecision.OBSERVE
    assert observed.speech_run_frames == 1
    assert discarded.decision is LocalInterruptionDecision.DISCARD
    assert discarded.speech_run_frames == 0
    assert discarded.reason == "speech-like frame matched local playback echo profile"


def test_probe_discards_invalid_echo_correlation_and_resets_run() -> None:
    probe = LocalInterruptionProbe(
        min_confirming_speech_frames=2,
        allow_confirmed_interrupt=True,
    )
    invalid_playback = LocalPlaybackContext(
        phase=LocalPlaybackPhase.PLAYING,
        echo_correlation=float("nan"),
    )
    clean_playback = LocalPlaybackContext(
        phase=LocalPlaybackPhase.PLAYING,
        echo_correlation=0.05,
    )

    discarded = probe.observe(frame(1), vad_state=VadState.SPEECH, playback=invalid_playback)
    observed = probe.observe(frame(2), vad_state=VadState.SPEECH, playback=clean_playback)

    assert discarded.decision is LocalInterruptionDecision.DISCARD
    assert discarded.speech_run_frames == 0
    assert discarded.reason == "echo correlation was invalid or uncertain during playback"
    assert observed.decision is LocalInterruptionDecision.OBSERVE
    assert observed.speech_run_frames == 1


def test_probe_can_confirm_only_when_explicitly_enabled() -> None:
    probe = LocalInterruptionProbe(
        min_confirming_speech_frames=2,
        allow_confirmed_interrupt=True,
    )
    playback = LocalPlaybackContext(
        phase=LocalPlaybackPhase.PLAYING,
        echo_correlation=0.05,
    )

    first = probe.observe(frame(1), vad_state=VadState.SPEECH, playback=playback)
    second = probe.observe(frame(2), vad_state=VadState.SPEECH, playback=playback)

    assert first.decision is LocalInterruptionDecision.OBSERVE
    assert first.reason == "candidate playback-time speech observed while confirmation is pending"
    assert second.decision is LocalInterruptionDecision.CONFIRMED_INTERRUPT
    assert second.reason == "fresh playback-time speech satisfied the confirmation boundary"


def test_probe_resets_confirmation_across_frame_sequence_discontinuity() -> None:
    probe = LocalInterruptionProbe(
        min_confirming_speech_frames=2,
        allow_confirmed_interrupt=True,
    )
    playback = LocalPlaybackContext(
        phase=LocalPlaybackPhase.PLAYING,
        playback_started_monotonic=10.0,
        echo_correlation=0.05,
    )

    first = probe.observe(frame(10), vad_state=VadState.SPEECH, playback=playback)
    discontinuous = probe.observe(frame(12), vad_state=VadState.SPEECH, playback=playback)
    confirmed = probe.observe(frame(13), vad_state=VadState.SPEECH, playback=playback)

    assert first.speech_run_frames == 1
    assert discontinuous.decision is LocalInterruptionDecision.OBSERVE
    assert discontinuous.speech_run_frames == 1
    assert confirmed.decision is LocalInterruptionDecision.CONFIRMED_INTERRUPT
    assert confirmed.speech_run_frames == 2


def test_probe_resets_confirmation_across_playback_instances() -> None:
    probe = LocalInterruptionProbe(
        min_confirming_speech_frames=2,
        allow_confirmed_interrupt=True,
    )
    first_playback = LocalPlaybackContext(
        phase=LocalPlaybackPhase.PLAYING,
        playback_started_monotonic=10.0,
        echo_correlation=0.05,
    )
    second_playback = LocalPlaybackContext(
        phase=LocalPlaybackPhase.PLAYING,
        playback_started_monotonic=20.0,
        echo_correlation=0.05,
    )

    first = probe.observe(frame(1), vad_state=VadState.SPEECH, playback=first_playback)
    reset = probe.observe(frame(2), vad_state=VadState.SPEECH, playback=second_playback)

    assert first.speech_run_frames == 1
    assert reset.decision is LocalInterruptionDecision.OBSERVE
    assert reset.speech_run_frames == 1


def test_probe_resets_on_silence_during_playback() -> None:
    probe = LocalInterruptionProbe(min_confirming_speech_frames=2)
    playback = LocalPlaybackContext(phase=LocalPlaybackPhase.PLAYING)

    observed = probe.observe(frame(1), vad_state=VadState.SPEECH, playback=playback)
    silent = probe.observe(frame(2), vad_state=VadState.SILENCE, playback=playback)

    assert observed.speech_run_frames == 1
    assert silent.decision is LocalInterruptionDecision.DISCARD
    assert silent.speech_run_frames == 0
    assert silent.reason == "playback-time microphone frame was not speech"


def test_probe_rejects_invalid_confirmation_settings() -> None:
    try:
        LocalInterruptionProbe(min_confirming_speech_frames=0)
    except ValueError as exc:
        assert str(exc) == "min_confirming_speech_frames must be positive"
    else:
        raise AssertionError("expected invalid min_confirming_speech_frames to fail")

    try:
        LocalInterruptionProbe(max_echo_correlation=1.5)
    except ValueError as exc:
        assert str(exc) == "max_echo_correlation must be between 0 and 1"
    else:
        raise AssertionError("expected invalid max_echo_correlation to fail")
