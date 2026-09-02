from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Mapping


class RealtimeEventType(StrEnum):
    STATE_CHANGED = "state_changed"
    INPUT_FRAME_ACCEPTED = "input_frame_accepted"
    INPUT_FRAME_IGNORED = "input_frame_ignored"
    INPUT_BACKPRESSURE = "input_backpressure"
    OUTPUT_BACKPRESSURE = "output_backpressure"
    VAD_EVALUATED = "vad_evaluated"
    TRANSCRIPT_DELTA = "transcript_delta"
    TRANSCRIPT_FINAL = "transcript_final"
    TTS_STARTED = "tts_started"
    OUTPUT_FRAME_QUEUED = "output_frame_queued"
    OUTPUT_FRAME_SENT = "output_frame_sent"
    BARGE_IN = "barge_in"
    AUDIO_FLUSHED = "audio_flushed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class RealtimeVoiceEvent:
    type: RealtimeEventType
    session_id: str
    state: str
    detail: Mapping[str, str] = field(default_factory=dict)
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
