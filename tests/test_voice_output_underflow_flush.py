from cybercore.voice.audio import AudioFormat, AudioFrame
from cybercore.voice.devices import SoundDeviceTransport


class FirstWriteUnderflowStream:
    def __init__(self) -> None:
        self.started = False
        self.aborted = False
        self.closed = False
        self.writes = 0

    def start(self) -> None:
        self.started = True

    def write(self, payload: bytes) -> bool:
        self.writes += 1
        return self.writes == 1

    def abort(self) -> None:
        self.aborted = True

    def close(self) -> None:
        self.closed = True


class FreshStreamSoundDevice:
    def __init__(self) -> None:
        self.streams: list[FirstWriteUnderflowStream] = []

    def RawOutputStream(self, **kwargs):
        stream = FirstWriteUnderflowStream()
        self.streams.append(stream)
        return stream


def test_flush_resets_consecutive_underflow_streak_but_keeps_lifetime_count() -> None:
    sd = FreshStreamSoundDevice()
    transport = SoundDeviceTransport(sounddevice_module=sd)
    frame = AudioFrame(sequence=0, payload=b"\x00\x00", format=AudioFormat())

    for expected_count in (1, 2, 3):
        transport.send(frame)
        assert transport.underflow_count == expected_count
        transport.flush_output()

    assert transport.underflow_count == 3
    assert len(sd.streams) == 3
    assert all(stream.started for stream in sd.streams)
    assert all(stream.aborted for stream in sd.streams)
    assert all(stream.closed for stream in sd.streams)
