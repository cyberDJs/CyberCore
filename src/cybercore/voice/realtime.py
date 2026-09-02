from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum

from cybercore.voice.adapters import (
    RealtimeAudioTransport,
    StreamingSpeechToText,
    StreamingTextToSpeech,
    TranscriptDelta,
    TranscriptResult,
    VadState,
    VoiceActivityDetector,
)
from cybercore.voice.audio import AudioBackpressureError, AudioFrame, BoundedAudioBuffer
from cybercore.voice.models import Utterance
from cybercore.voice.realtime_events import RealtimeEventType, RealtimeVoiceEvent
from cybercore.voice.session import SessionStatus, VoiceSession


class RealtimeState(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"


RealtimeEventSink = Callable[[RealtimeVoiceEvent], None]


class RealtimeVoiceRuntime:
    def __init__(
        self,
        *,
        session: VoiceSession,
        vad: VoiceActivityDetector,
        stt: StreamingSpeechToText,
        tts: StreamingTextToSpeech,
        transport: RealtimeAudioTransport | None = None,
        input_max_frames: int = 128,
        input_max_bytes: int = 1_048_576,
        output_max_frames: int = 128,
        output_max_bytes: int = 1_048_576,
        event_sink: RealtimeEventSink | None = None,
    ) -> None:
        if session.status is SessionStatus.CANCELLED:
            raise ValueError("cannot create realtime runtime for a cancelled voice session")
        self.session = session
        self.vad = vad
        self.stt = stt
        self.tts = tts
        self.transport = transport
        self.input_buffer = BoundedAudioBuffer(
            max_frames=input_max_frames, max_bytes=input_max_bytes
        )
        self.output_buffer = BoundedAudioBuffer(
            max_frames=output_max_frames, max_bytes=output_max_bytes
        )
        self.event_sink = event_sink
        self.state = RealtimeState.IDLE
        self._synthesis_exhausted = False

    def _emit(self, event_type: RealtimeEventType, **detail: str) -> None:
        if self.event_sink is not None:
            self.event_sink(
                RealtimeVoiceEvent(
                    type=event_type,
                    session_id=self.session.session_id,
                    state=self.state.value,
                    detail=detail,
                )
            )

    def _transition(self, target: RealtimeState, reason: str) -> None:
        if self.state is RealtimeState.CANCELLED and target is not RealtimeState.CANCELLED:
            raise RuntimeError("cancelled realtime runtime is terminal")
        previous = self.state
        self.state = target
        self._emit(
            RealtimeEventType.STATE_CHANGED,
            previous=previous.value,
            current=target.value,
            reason=reason,
        )

    def start_listening(self) -> None:
        if self.state not in {RealtimeState.IDLE, RealtimeState.INTERRUPTED}:
            raise RuntimeError(f"cannot start listening from {self.state.value}")
        if (
            self.state is RealtimeState.INTERRUPTED
            and self.session.status is SessionStatus.INTERRUPTED
        ):
            self.session.resume()
        self.stt.reset()
        self.input_buffer.flush()
        self._transition(RealtimeState.LISTENING, "input turn started")

    def _interrupt_active_turn(self, reason: str) -> None:
        if self.state is RealtimeState.CANCELLED:
            return
        self.tts.cancel()
        self.stt.reset()
        flushed_input = len(self.input_buffer.flush())
        flushed_output = len(self.output_buffer.flush())
        if self.transport is not None:
            self.transport.flush_output()
        self._synthesis_exhausted = False
        self.session.interrupt(reason)
        self._transition(RealtimeState.INTERRUPTED, reason)
        self._emit(
            RealtimeEventType.AUDIO_FLUSHED,
            input_frames=str(flushed_input),
            output_frames=str(flushed_output),
        )

    def receive_input(self, frame: AudioFrame) -> tuple[TranscriptDelta, ...]:
        if self.state is RealtimeState.CANCELLED:
            raise RuntimeError("cannot receive audio after cancellation")

        vad = self.vad.evaluate(frame)
        self._emit(
            RealtimeEventType.VAD_EVALUATED,
            frame_sequence=str(frame.sequence),
            vad_state=vad.state.value,
        )

        if self.state in {RealtimeState.SPEAKING, RealtimeState.PROCESSING}:
            if vad.state is not VadState.SPEECH:
                self._emit(
                    RealtimeEventType.INPUT_FRAME_IGNORED,
                    frame_sequence=str(frame.sequence),
                    reason=f"{self.state.value} input was not classified as speech",
                )
                return ()
            reason = f"speech detected during {self.state.value}"
            self._interrupt_active_turn(reason)
            self._emit(
                RealtimeEventType.BARGE_IN, frame_sequence=str(frame.sequence), reason=reason
            )

        if self.state is RealtimeState.IDLE:
            if vad.state is not VadState.SPEECH:
                self._emit(
                    RealtimeEventType.INPUT_FRAME_IGNORED,
                    frame_sequence=str(frame.sequence),
                    reason="idle input was not classified as speech",
                )
                return ()
            self.start_listening()

        if self.state not in {RealtimeState.LISTENING, RealtimeState.INTERRUPTED}:
            raise RuntimeError(f"cannot accept input while {self.state.value}")

        try:
            self.input_buffer.push(frame)
        except AudioBackpressureError:
            self._emit(RealtimeEventType.INPUT_BACKPRESSURE, frame_sequence=str(frame.sequence))
            raise

        deltas = self.stt.push(frame)
        self._emit(RealtimeEventType.INPUT_FRAME_ACCEPTED, frame_sequence=str(frame.sequence))
        for delta in deltas:
            self._emit(
                RealtimeEventType.TRANSCRIPT_DELTA,
                transcript_sequence=str(delta.sequence),
                characters=str(len(delta.text)),
            )
        return deltas

    def finish_utterance(self, *, actor_id: str, utterance_id: str) -> Utterance | None:
        if self.state not in {RealtimeState.LISTENING, RealtimeState.INTERRUPTED}:
            raise RuntimeError(f"cannot finish input while {self.state.value}")
        result: TranscriptResult | None = self.stt.finish()
        self.input_buffer.flush()
        if self.session.status is SessionStatus.INTERRUPTED:
            self.session.resume()
        if result is None or not result.text.strip():
            self._transition(RealtimeState.IDLE, "input turn produced no utterance")
            return None
        self._transition(RealtimeState.PROCESSING, "input turn finalized")
        self._emit(
            RealtimeEventType.TRANSCRIPT_FINAL,
            characters=str(len(result.text)),
            language=result.language or "",
        )
        return Utterance(
            id=utterance_id,
            session_id=self.session.session_id,
            actor_id=actor_id,
            text=result.text,
        )

    def begin_speaking(self, text: str) -> None:
        if self.state is not RealtimeState.PROCESSING:
            raise RuntimeError(f"cannot begin speaking from {self.state.value}")
        if not text.strip():
            raise ValueError("TTS text must not be empty")
        self.output_buffer.flush()
        self.tts.reset()
        self.tts.start(text)
        self._synthesis_exhausted = False
        self._transition(RealtimeState.SPEAKING, "output turn started")
        self._emit(RealtimeEventType.TTS_STARTED)

    def pump_synthesis(self, *, max_frames: int = 8) -> int:
        if self.state is not RealtimeState.SPEAKING:
            raise RuntimeError(f"cannot synthesize output while {self.state.value}")
        if max_frames <= 0:
            raise ValueError("max_frames must be positive")
        queued = 0
        for _ in range(max_frames):
            frame = self.tts.pull()
            if frame is None:
                self._synthesis_exhausted = True
                break
            try:
                self.output_buffer.push(frame)
            except AudioBackpressureError:
                self._emit(
                    RealtimeEventType.OUTPUT_BACKPRESSURE, frame_sequence=str(frame.sequence)
                )
                self._interrupt_active_turn("output backpressure")
                raise
            queued += 1
            self._emit(RealtimeEventType.OUTPUT_FRAME_QUEUED, frame_sequence=str(frame.sequence))
        self._settle_output_if_complete()
        return queued

    def next_output_frame(self) -> AudioFrame | None:
        frame = self.output_buffer.pop()
        self._settle_output_if_complete()
        return frame

    def send_next_output(self) -> bool:
        if self.transport is None:
            raise RuntimeError("no realtime audio transport is configured")
        frame = self.output_buffer.pop()
        if frame is None:
            self._settle_output_if_complete()
            return False
        self.transport.send(frame)
        self._emit(RealtimeEventType.OUTPUT_FRAME_SENT, frame_sequence=str(frame.sequence))
        self._settle_output_if_complete()
        return True

    def _settle_output_if_complete(self) -> None:
        if (
            self.state is RealtimeState.SPEAKING
            and self._synthesis_exhausted
            and len(self.output_buffer) == 0
        ):
            self.tts.reset()
            self._synthesis_exhausted = False
            self._transition(RealtimeState.IDLE, "output turn completed")

    def barge_in(self, reason: str = "operator barge-in") -> None:
        if self.state not in {RealtimeState.PROCESSING, RealtimeState.SPEAKING}:
            raise RuntimeError(f"cannot barge in while {self.state.value}")
        self._interrupt_active_turn(reason)
        self._emit(RealtimeEventType.BARGE_IN, reason=reason)

    def cancel(self, reason: str = "operator cancellation") -> None:
        if self.state is RealtimeState.CANCELLED:
            return
        self.tts.cancel()
        self.stt.reset()
        flushed_input = len(self.input_buffer.flush())
        flushed_output = len(self.output_buffer.flush())
        if self.transport is not None:
            self.transport.flush_output()
        self._synthesis_exhausted = False
        self.session.cancel()
        self._transition(RealtimeState.CANCELLED, reason)
        self._emit(
            RealtimeEventType.AUDIO_FLUSHED,
            input_frames=str(flushed_input),
            output_frames=str(flushed_output),
        )
        self._emit(RealtimeEventType.CANCELLED, reason=reason)
