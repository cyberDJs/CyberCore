import pytest

from cybercore.voice import (
    AudioBackpressureError,
    AudioFormat,
    AudioFrame,
    RealtimeEventType,
    RealtimeState,
    RealtimeVoiceRuntime,
    SessionStatus,
    TranscriptDelta,
    TranscriptResult,
    VadResult,
    VadState,
    VoiceSession,
)


class FakeVad:
    def __init__(self, state: VadState = VadState.SPEECH) -> None:
        self.state = state

    def evaluate(self, frame: AudioFrame) -> VadResult:
        return VadResult(self.state, confidence=1.0)


class FakeStt:
    def __init__(self, result: TranscriptResult | None = None) -> None:
        self.frames: list[int] = []
        self.reset_count = 0
        self.result = result or TranscriptResult("inspect staging", confidence=1.0, language="en")

    def push(self, frame: AudioFrame) -> tuple[TranscriptDelta, ...]:
        self.frames.append(frame.sequence)
        return (TranscriptDelta(text=f"delta-{frame.sequence}", sequence=len(self.frames) - 1),)

    def finish(self) -> TranscriptResult | None:
        return self.result

    def reset(self) -> None:
        self.reset_count += 1
        self.frames.clear()


class FakeTts:
    def __init__(self, frames: list[AudioFrame] | None = None) -> None:
        self.frames = list(frames or [])
        self.started: list[str] = []
        self.cancel_count = 0
        self.reset_count = 0

    def start(self, text: str) -> None:
        self.started.append(text)

    def pull(self) -> AudioFrame | None:
        if not self.frames:
            return None
        return self.frames.pop(0)

    def cancel(self) -> None:
        self.cancel_count += 1
        self.frames.clear()

    def reset(self) -> None:
        self.reset_count += 1


class FakeTransport:
    def __init__(self) -> None:
        self.sent: list[int] = []
        self.flush_count = 0

    def send(self, frame: AudioFrame) -> None:
        self.sent.append(frame.sequence)

    def flush_output(self) -> None:
        self.flush_count += 1


def frame(sequence: int) -> AudioFrame:
    return AudioFrame(sequence=sequence, payload=b"\x00\x00" * 160, format=AudioFormat())


def make_runtime(
    *,
    vad_state: VadState = VadState.SPEECH,
    tts_frames: list[AudioFrame] | None = None,
    input_max_frames: int = 128,
    output_max_frames: int = 128,
):
    events = []
    session = VoiceSession("session-1")
    vad = FakeVad(vad_state)
    stt = FakeStt()
    tts = FakeTts(tts_frames)
    transport = FakeTransport()
    runtime = RealtimeVoiceRuntime(
        session=session,
        vad=vad,
        stt=stt,
        tts=tts,
        transport=transport,
        input_max_frames=input_max_frames,
        input_max_bytes=4096,
        output_max_frames=output_max_frames,
        output_max_bytes=4096,
        event_sink=events.append,
    )
    return runtime, session, vad, stt, tts, transport, events


def test_realtime_happy_path_creates_foundation_utterance_and_returns_idle() -> None:
    runtime, session, _, _, tts, transport, events = make_runtime(tts_frames=[frame(10), frame(11)])

    runtime.receive_input(frame(1))
    utterance = runtime.finish_utterance(actor_id="johnny", utterance_id="u-1")

    assert runtime.state is RealtimeState.PROCESSING
    assert utterance is not None
    assert utterance.text == "inspect staging"
    assert utterance.session_id == session.session_id
    assert runtime.input_buffer.snapshot().frame_count == 0
    transcript_events = [
        event
        for event in events
        if event.type in {RealtimeEventType.TRANSCRIPT_DELTA, RealtimeEventType.TRANSCRIPT_FINAL}
    ]
    assert all("text" not in event.detail for event in transcript_events)

    runtime.begin_speaking("done")
    assert runtime.state is RealtimeState.SPEAKING
    assert runtime.pump_synthesis(max_frames=4) == 2
    assert runtime.send_next_output() is True
    assert runtime.send_next_output() is True
    assert runtime.state is RealtimeState.IDLE
    assert transport.sent == [10, 11]
    assert tts.started == ["done"]


def test_idle_silence_is_ignored_until_voice_starts() -> None:
    runtime, _, vad, stt, _, _, events = make_runtime(vad_state=VadState.SILENCE)

    assert runtime.receive_input(frame(1)) == ()
    assert runtime.state is RealtimeState.IDLE
    assert stt.frames == []
    assert any(event.type is RealtimeEventType.INPUT_FRAME_IGNORED for event in events)

    vad.state = VadState.SPEECH
    runtime.receive_input(frame(2))
    assert runtime.state is RealtimeState.LISTENING
    assert stt.frames == [2]


def test_empty_transcript_returns_to_idle_without_utterance() -> None:
    runtime, _, _, stt, _, _, _ = make_runtime()
    stt.result = TranscriptResult("   ")
    runtime.receive_input(frame(1))

    assert runtime.finish_utterance(actor_id="johnny", utterance_id="u-empty") is None
    assert runtime.state is RealtimeState.IDLE
    assert runtime.input_buffer.snapshot().frame_count == 0


def test_speech_during_speaking_causes_barge_in_and_flushes_output() -> None:
    runtime, session, _, stt, tts, transport, events = make_runtime(
        tts_frames=[frame(20), frame(21)]
    )
    runtime.receive_input(frame(1))
    runtime.finish_utterance(actor_id="johnny", utterance_id="u-1")
    runtime.begin_speaking("long answer")
    runtime.pump_synthesis(max_frames=1)
    assert runtime.output_buffer.snapshot().frame_count == 1

    runtime.receive_input(frame(2))

    assert runtime.state is RealtimeState.INTERRUPTED
    assert session.status is SessionStatus.INTERRUPTED
    assert runtime.output_buffer.snapshot().frame_count == 0
    assert transport.flush_count == 1
    assert tts.cancel_count == 1
    assert stt.frames == [2]
    assert any(event.type is RealtimeEventType.BARGE_IN for event in events)

    utterance = runtime.finish_utterance(actor_id="johnny", utterance_id="u-2")
    assert utterance is not None
    assert runtime.state is RealtimeState.PROCESSING
    assert session.status is SessionStatus.ACTIVE


def test_silence_during_speaking_is_ignored_without_barge_in() -> None:
    runtime, session, vad, _, tts, transport, events = make_runtime(tts_frames=[frame(20)])
    runtime.receive_input(frame(1))
    runtime.finish_utterance(actor_id="johnny", utterance_id="u-1")
    runtime.begin_speaking("answer")
    vad.state = VadState.SILENCE

    assert runtime.receive_input(frame(2)) == ()
    assert runtime.state is RealtimeState.SPEAKING
    assert session.status is SessionStatus.ACTIVE
    assert tts.cancel_count == 0
    assert transport.flush_count == 0
    assert any(event.type is RealtimeEventType.INPUT_FRAME_IGNORED for event in events)


def test_input_backpressure_rejects_frame_before_stt() -> None:
    runtime, _, _, stt, _, _, events = make_runtime(input_max_frames=1)
    runtime.receive_input(frame(1))

    with pytest.raises(AudioBackpressureError):
        runtime.receive_input(frame(2))

    assert stt.frames == [1]
    assert any(event.type is RealtimeEventType.INPUT_BACKPRESSURE for event in events)


def test_output_backpressure_fails_closed_by_interrupting_output() -> None:
    runtime, session, _, _, tts, transport, events = make_runtime(
        tts_frames=[frame(20), frame(21)], output_max_frames=1
    )
    runtime.receive_input(frame(1))
    runtime.finish_utterance(actor_id="johnny", utterance_id="u-1")
    runtime.begin_speaking("answer")

    with pytest.raises(AudioBackpressureError):
        runtime.pump_synthesis(max_frames=2)

    assert runtime.state is RealtimeState.INTERRUPTED
    assert session.status is SessionStatus.INTERRUPTED
    assert runtime.output_buffer.snapshot().frame_count == 0
    assert tts.cancel_count == 1
    assert transport.flush_count == 1
    assert any(event.type is RealtimeEventType.OUTPUT_BACKPRESSURE for event in events)


def test_cancel_is_terminal_and_flushes_everything() -> None:
    runtime, session, _, stt, tts, transport, events = make_runtime(tts_frames=[frame(20)])
    runtime.receive_input(frame(1))
    runtime.finish_utterance(actor_id="johnny", utterance_id="u-1")
    runtime.begin_speaking("answer")
    runtime.pump_synthesis(max_frames=1)

    runtime.cancel("operator stop")

    assert runtime.state is RealtimeState.CANCELLED
    assert session.status is SessionStatus.CANCELLED
    assert runtime.input_buffer.snapshot().frame_count == 0
    assert runtime.output_buffer.snapshot().frame_count == 0
    assert stt.reset_count >= 1
    assert tts.cancel_count == 1
    assert transport.flush_count == 1
    assert any(event.type is RealtimeEventType.CANCELLED for event in events)
    with pytest.raises(RuntimeError):
        runtime.receive_input(frame(3))
