from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from cybercore.voice.adapters import VadState
from cybercore.voice.audio import AudioFrame


class LocalPlaybackPhase(StrEnum):
    IDLE = "idle"
    GENERATING = "generating"
    PLAYING = "playing"
    SETTLING = "settling"


class LocalInterruptionDecision(StrEnum):
    DISCARD = "discard"
    OBSERVE = "observe"
    CONFIRMED_INTERRUPT = "confirmed_interrupt"


@dataclass(frozen=True)
class LocalPlaybackContext:
    phase: LocalPlaybackPhase = LocalPlaybackPhase.IDLE
    output_frame_sequence: int | None = None
    playback_started_monotonic: float | None = None
    frame_received_monotonic: float | None = None
    mic_rms: float | None = None
    output_rms: float | None = None
    echo_correlation: float | None = None

    @property
    def playback_active(self) -> bool:
        return self.phase in {
            LocalPlaybackPhase.GENERATING,
            LocalPlaybackPhase.PLAYING,
            LocalPlaybackPhase.SETTLING,
        }


@dataclass(frozen=True)
class LocalInterruptionEvidence:
    frame_sequence: int
    vad_state: str
    playback_phase: str
    speech_run_frames: int
    decision: LocalInterruptionDecision
    reason: str
    output_frame_sequence: int | None = None
    mic_rms: float | None = None
    output_rms: float | None = None
    echo_correlation: float | None = None


class LocalInterruptionProbe:
    """Classify local playback-time microphone frames without changing runtime flow.

    The default probe is evidence-only and fail-closed: it may observe candidate
    speech during playback, but it never confirms an interruption unless explicitly
    constructed with ``allow_confirmed_interrupt=True``.
    """

    def __init__(
        self,
        *,
        min_confirming_speech_frames: int = 3,
        max_echo_correlation: float = 0.70,
        allow_confirmed_interrupt: bool = False,
    ) -> None:
        if min_confirming_speech_frames <= 0:
            raise ValueError("min_confirming_speech_frames must be positive")
        if not 0.0 <= max_echo_correlation <= 1.0:
            raise ValueError("max_echo_correlation must be between 0 and 1")
        self.min_confirming_speech_frames = min_confirming_speech_frames
        self.max_echo_correlation = max_echo_correlation
        self.allow_confirmed_interrupt = allow_confirmed_interrupt
        self._speech_run_frames = 0
        self._last_frame_sequence: int | None = None
        self._last_playback_started_monotonic: float | None = None

    def reset(self) -> None:
        self._speech_run_frames = 0
        self._last_frame_sequence = None
        self._last_playback_started_monotonic = None

    def observe(
        self,
        frame: AudioFrame,
        *,
        vad_state: VadState,
        playback: LocalPlaybackContext,
    ) -> LocalInterruptionEvidence:
        if not playback.playback_active:
            self.reset()
            return self._evidence(
                frame,
                vad_state=vad_state,
                playback=playback,
                decision=LocalInterruptionDecision.DISCARD,
                reason="microphone frame was outside local playback",
            )

        if vad_state is not VadState.SPEECH:
            self.reset()
            return self._evidence(
                frame,
                vad_state=vad_state,
                playback=playback,
                decision=LocalInterruptionDecision.DISCARD,
                reason="playback-time microphone frame was not speech",
            )

        if self._echo_correlation_invalid(playback.echo_correlation):
            self.reset()
            return self._evidence(
                frame,
                vad_state=vad_state,
                playback=playback,
                decision=LocalInterruptionDecision.DISCARD,
                reason="echo correlation was invalid or uncertain during playback",
            )

        if (
            playback.echo_correlation is not None
            and playback.echo_correlation >= self.max_echo_correlation
        ):
            self.reset()
            return self._evidence(
                frame,
                vad_state=vad_state,
                playback=playback,
                decision=LocalInterruptionDecision.DISCARD,
                reason="speech-like frame matched local playback echo profile",
            )

        if self._speech_run_discontinuous(frame, playback):
            self.reset()

        self._speech_run_frames += 1
        self._last_frame_sequence = frame.sequence
        self._last_playback_started_monotonic = playback.playback_started_monotonic

        if (
            self.allow_confirmed_interrupt
            and self._speech_run_frames >= self.min_confirming_speech_frames
        ):
            return self._evidence(
                frame,
                vad_state=vad_state,
                playback=playback,
                decision=LocalInterruptionDecision.CONFIRMED_INTERRUPT,
                reason="fresh playback-time speech satisfied the confirmation boundary",
            )

        if self.allow_confirmed_interrupt:
            reason = "candidate playback-time speech observed while confirmation is pending"
        else:
            reason = "candidate playback-time speech observed while interruption is disabled"

        return self._evidence(
            frame,
            vad_state=vad_state,
            playback=playback,
            decision=LocalInterruptionDecision.OBSERVE,
            reason=reason,
        )

    def _echo_correlation_invalid(self, echo_correlation: float | None) -> bool:
        if echo_correlation is None:
            return False
        return not math.isfinite(echo_correlation) or not 0.0 <= echo_correlation <= 1.0

    def _speech_run_discontinuous(
        self,
        frame: AudioFrame,
        playback: LocalPlaybackContext,
    ) -> bool:
        if (
            self._last_frame_sequence is not None
            and frame.sequence != self._last_frame_sequence + 1
        ):
            return True
        if (
            self._last_playback_started_monotonic != playback.playback_started_monotonic
            and self._last_playback_started_monotonic is not None
        ):
            return True
        return False

    def _evidence(
        self,
        frame: AudioFrame,
        *,
        vad_state: VadState,
        playback: LocalPlaybackContext,
        decision: LocalInterruptionDecision,
        reason: str,
    ) -> LocalInterruptionEvidence:
        return LocalInterruptionEvidence(
            frame_sequence=frame.sequence,
            vad_state=vad_state.value,
            playback_phase=playback.phase.value,
            speech_run_frames=self._speech_run_frames,
            decision=decision,
            reason=reason,
            output_frame_sequence=playback.output_frame_sequence,
            mic_rms=playback.mic_rms,
            output_rms=playback.output_rms,
            echo_correlation=playback.echo_correlation,
        )
