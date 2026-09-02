from array import array
from types import SimpleNamespace

import pytest

from cybercore.voice.audio import AudioFormat, AudioFrame
from cybercore.voice.devices import (
    AudioInputOverflowError,
    SoundDeviceInput,
    SoundDeviceTransport,
    list_audio_devices,
    resample_pcm_s16le_mono,
    validate_audio_settings,
)
from cybercore.voice.local_config import LocalAudioConfig


class FakeInputStream:
    def __init__(self, payload: bytes, *, overflowed: bool = False) -> None:
        self.payload = payload
        self.overflowed = overflowed
        self.started = False
        self.closed = False
        self.read_available = 8192
        self.read_calls: list[int] = []

    def start(self) -> None:
        self.started = True

    def read(self, frames: int):
        self.read_calls.append(frames)
        return self.payload, self.overflowed

    def stop(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


class FakeOutputStream:
    def __init__(self) -> None:
        self.started = False
        self.closed = False
        self.aborted = False
        self.payloads: list[bytes] = []

    def start(self) -> None:
        self.started = True

    def write(self, payload: bytes) -> bool:
        self.payloads.append(bytes(payload))
        return False

    def abort(self) -> None:
        self.aborted = True

    def close(self) -> None:
        self.closed = True


class FakeSoundDevice:
    __version__ = "0.5.6"

    def __init__(self, *, overflowed: bool = False) -> None:
        self.default = SimpleNamespace(device=(0, 1))
        self.input_stream = FakeInputStream(b"\x01\x00" * 3840, overflowed=overflowed)
        self.output_stream = FakeOutputStream()
        self.input_checks: list[dict[str, object]] = []
        self.output_checks: list[dict[str, object]] = []
        self.input_stream_kwargs: dict[str, object] = {}

    def query_devices(self):
        return [
            {
                "name": "Mic",
                "hostapi": 0,
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 48000.0,
            },
            {
                "name": "Speaker",
                "hostapi": 0,
                "max_input_channels": 0,
                "max_output_channels": 2,
                "default_samplerate": 48000.0,
            },
        ]

    def check_input_settings(self, **kwargs) -> None:
        self.input_checks.append(kwargs)

    def check_output_settings(self, **kwargs) -> None:
        self.output_checks.append(kwargs)

    def RawInputStream(self, **kwargs):
        self.input_stream_kwargs = kwargs
        return self.input_stream

    def RawOutputStream(self, **kwargs):
        return self.output_stream


def test_device_listing_marks_defaults_and_capabilities() -> None:
    devices = list_audio_devices(sounddevice_module=FakeSoundDevice())

    assert devices[0].name == "Mic"
    assert devices[0].can_input is True
    assert devices[0].default_input is True
    assert devices[1].can_output is True
    assert devices[1].default_output is True


def test_validate_audio_settings_checks_native_capture_and_model_output_rate() -> None:
    sd = FakeSoundDevice()
    config = LocalAudioConfig(input_device=0, output_device=1)

    validate_audio_settings(config, sounddevice_module=sd)

    assert sd.input_checks[0]["samplerate"] == 48000
    assert sd.output_checks[0]["samplerate"] == 16000
    assert sd.output_checks[0]["dtype"] == "int16"


def test_sounddevice_input_captures_native_rate_then_resamples_to_model_rate() -> None:
    sd = FakeSoundDevice()
    source = SoundDeviceInput(LocalAudioConfig(), sounddevice_module=sd)

    frame = source.read_frame()

    assert frame.sequence == 0
    assert frame.format == AudioFormat()
    assert len(frame.payload) == 2560
    assert sd.input_stream_kwargs["samplerate"] == 48000
    assert sd.input_stream_kwargs["blocksize"] == 3840
    assert sd.input_stream.read_calls == [3840]

    overflow_sd = FakeSoundDevice(overflowed=True)
    overflow_source = SoundDeviceInput(LocalAudioConfig(), sounddevice_module=overflow_sd)
    with pytest.raises(AudioInputOverflowError):
        overflow_source.read_frame()


def test_pcm_resampler_preserves_block_duration() -> None:
    source = array("h", range(3840)).tobytes()

    output = resample_pcm_s16le_mono(source, 48000, 16000)

    assert len(output) == 1280 * 2
    assert resample_pcm_s16le_mono(output, 16000, 16000) == output


def test_sounddevice_transport_writes_and_flushes_output() -> None:
    sd = FakeSoundDevice()
    transport = SoundDeviceTransport(output_device=1, sounddevice_module=sd)
    frame = AudioFrame(sequence=0, payload=b"\x00\x00" * 160, format=AudioFormat())

    transport.send(frame)
    assert sd.output_stream.payloads == [frame.payload]

    transport.flush_output()
    assert sd.output_stream.aborted is True
    assert sd.output_stream.closed is True
