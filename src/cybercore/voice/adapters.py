from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from cybercore.voice.audio import AudioFrame


class VadState(StrEnum):
    SPEECH = "speech"
    SILENCE = "silence"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class VadResult:
    state: VadState
    confidence: float | None = None
    reason: str = ""

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("VAD confidence must be between 0 and 1")


@dataclass(frozen=True)
class TranscriptDelta:
    text: str
    sequence: int

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise ValueError("transcript sequence must be non-negative")


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    confidence: float | None = None
    language: str | None = None

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("transcript confidence must be between 0 and 1")


class VoiceActivityDetector(Protocol):
    def evaluate(self, frame: AudioFrame) -> VadResult: ...


class StreamingSpeechToText(Protocol):
    def push(self, frame: AudioFrame) -> tuple[TranscriptDelta, ...]: ...

    def finish(self) -> TranscriptResult | None: ...

    def reset(self) -> None: ...


class StreamingTextToSpeech(Protocol):
    def start(self, text: str) -> None: ...

    def pull(self) -> AudioFrame | None: ...

    def cancel(self) -> None: ...

    def reset(self) -> None: ...


class RealtimeAudioTransport(Protocol):
    def send(self, frame: AudioFrame) -> None: ...

    def flush_output(self) -> None: ...


class RealtimeSpeechProvider(Protocol):
    vad: VoiceActivityDetector
    stt: StreamingSpeechToText
    tts: StreamingTextToSpeech
