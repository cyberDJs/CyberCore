from __future__ import annotations

from dataclasses import dataclass

from cybercore.voice.adapters import VadState


@dataclass(frozen=True)
class BargeInShadowSnapshot:
    candidate: bool
    armed: bool
    silence_frames: int
    speech_frames: int
    candidate_frame_sequence: int | None


class FreshSpeechShadowGate:
    """Observe playback-time VAD without granting interruption authority.

    The gate deliberately refuses to treat speech that is already present when
    observation begins as fresh user speech. It first requires a bounded run of
    silence and only then confirms a candidate after a bounded run of speech.
    This is a shadow-only evidence boundary: callers must not use it to cancel
    playback or change execution authority.
    """

    def __init__(
        self, *, required_silence_frames: int = 2, required_speech_frames: int = 3
    ) -> None:
        if required_silence_frames <= 0:
            raise ValueError("required_silence_frames must be positive")
        if required_speech_frames <= 0:
            raise ValueError("required_speech_frames must be positive")
        self.required_silence_frames = required_silence_frames
        self.required_speech_frames = required_speech_frames
        self.reset()

    def reset(self) -> None:
        self._armed = False
        self._silence_frames = 0
        self._speech_frames = 0
        self._candidate_frame_sequence: int | None = None

    @property
    def snapshot(self) -> BargeInShadowSnapshot:
        return BargeInShadowSnapshot(
            candidate=self._candidate_frame_sequence is not None,
            armed=self._armed,
            silence_frames=self._silence_frames,
            speech_frames=self._speech_frames,
            candidate_frame_sequence=self._candidate_frame_sequence,
        )

    def observe(self, vad_state: VadState, *, frame_sequence: int) -> bool:
        if self._candidate_frame_sequence is not None:
            return True

        if vad_state is VadState.UNKNOWN:
            self._armed = False
            self._silence_frames = 0
            self._speech_frames = 0
            return False

        if not self._armed:
            self._speech_frames = 0
            if vad_state is VadState.SILENCE:
                self._silence_frames += 1
                if self._silence_frames >= self.required_silence_frames:
                    self._armed = True
            else:
                self._silence_frames = 0
            return False

        if vad_state is VadState.SPEECH:
            self._speech_frames += 1
            if self._speech_frames >= self.required_speech_frames:
                self._candidate_frame_sequence = frame_sequence
                return True
        else:
            self._speech_frames = 0
        return False
