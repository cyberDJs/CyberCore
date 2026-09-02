import pytest

from cybercore.voice import (
    AudioBackpressureError,
    AudioFormat,
    AudioFrame,
    BoundedAudioBuffer,
)


def frame(sequence: int, samples: int = 160) -> AudioFrame:
    return AudioFrame(sequence=sequence, payload=b"\x00\x00" * samples, format=AudioFormat())


def test_pcm_frame_duration_is_deterministic() -> None:
    value = frame(0, samples=160)
    assert value.duration_ms == pytest.approx(10.0)


def test_pcm_frame_rejects_misaligned_payload() -> None:
    with pytest.raises(ValueError):
        AudioFrame(sequence=0, payload=b"\x00", format=AudioFormat())


def test_bounded_buffer_rejects_without_overwriting() -> None:
    buffer = BoundedAudioBuffer(max_frames=1, max_bytes=1024)
    first = frame(1)
    second = frame(2)
    buffer.push(first)

    with pytest.raises(AudioBackpressureError):
        buffer.push(second)

    assert buffer.snapshot().frame_count == 1
    assert buffer.pop() == first
    assert buffer.pop() is None
