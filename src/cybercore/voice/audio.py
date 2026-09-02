from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum


class AudioEncoding(StrEnum):
    PCM_S16LE = "pcm_s16le"


@dataclass(frozen=True)
class AudioFormat:
    sample_rate_hz: int = 16000
    channels: int = 1
    sample_width_bytes: int = 2
    encoding: AudioEncoding = AudioEncoding.PCM_S16LE

    def __post_init__(self) -> None:
        if self.sample_rate_hz <= 0:
            raise ValueError("sample rate must be positive")
        if self.channels <= 0:
            raise ValueError("channel count must be positive")
        if self.sample_width_bytes <= 0:
            raise ValueError("sample width must be positive")
        if self.encoding is AudioEncoding.PCM_S16LE and self.sample_width_bytes != 2:
            raise ValueError("PCM_S16LE requires a two-byte sample width")

    @property
    def bytes_per_second(self) -> int:
        return self.sample_rate_hz * self.channels * self.sample_width_bytes

    @property
    def bytes_per_sample_frame(self) -> int:
        return self.channels * self.sample_width_bytes


@dataclass(frozen=True)
class AudioFrame:
    sequence: int
    payload: bytes
    format: AudioFormat = AudioFormat()
    captured_at_ms: int | None = None

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise ValueError("audio frame sequence must be non-negative")
        if not self.payload:
            raise ValueError("audio frame payload must not be empty")
        if len(self.payload) % self.format.bytes_per_sample_frame:
            raise ValueError("audio frame payload is not aligned to complete sample frames")
        if self.captured_at_ms is not None and self.captured_at_ms < 0:
            raise ValueError("captured_at_ms must be non-negative")

    @property
    def duration_ms(self) -> float:
        return (len(self.payload) / self.format.bytes_per_second) * 1000.0


class AudioBackpressureError(RuntimeError):
    pass


@dataclass(frozen=True)
class AudioBufferSnapshot:
    frame_count: int
    byte_count: int
    max_frames: int
    max_bytes: int


class BoundedAudioBuffer:
    def __init__(self, *, max_frames: int, max_bytes: int) -> None:
        if max_frames <= 0 or max_bytes <= 0:
            raise ValueError("audio buffer limits must be positive")
        self.max_frames = max_frames
        self.max_bytes = max_bytes
        self._frames: deque[AudioFrame] = deque()
        self._byte_count = 0

    def __len__(self) -> int:
        return len(self._frames)

    @property
    def byte_count(self) -> int:
        return self._byte_count

    def snapshot(self) -> AudioBufferSnapshot:
        return AudioBufferSnapshot(
            frame_count=len(self._frames),
            byte_count=self._byte_count,
            max_frames=self.max_frames,
            max_bytes=self.max_bytes,
        )

    def push(self, frame: AudioFrame) -> None:
        next_frames = len(self._frames) + 1
        next_bytes = self._byte_count + len(frame.payload)
        if next_frames > self.max_frames or next_bytes > self.max_bytes:
            raise AudioBackpressureError(
                "audio buffer capacity exceeded; frame rejected without overwriting queued audio"
            )
        self._frames.append(frame)
        self._byte_count = next_bytes

    def pop(self) -> AudioFrame | None:
        if not self._frames:
            return None
        frame = self._frames.popleft()
        self._byte_count -= len(frame.payload)
        return frame

    def flush(self) -> tuple[AudioFrame, ...]:
        frames = tuple(self._frames)
        self._frames.clear()
        self._byte_count = 0
        return frames
