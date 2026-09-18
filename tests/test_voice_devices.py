from array import array
import math
from types import SimpleNamespace

import pytest

from cybercore.voice import devices as voice_devices
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


class SequencedInputStream(FakeInputStream):
    def __init__(self, payloads: list[bytes]) -> None:
        super().__init__(b"")
        self.payloads = list(payloads)

    @property
    def read_available(self) -> int:
        return len(self.payloads) * 3840

    @read_available.setter
    def read_available(self, value: int) -> None:
        pass

    def read(self, frames: int):
        self.read_calls.append(frames)
        return self.payloads.pop(0), False


class PartialInputStream(FakeInputStream):
    def __init__(self, frames: int) -> None:
        super().__init__(b"\x00\x00" * frames)
        self.frames = frames
        self.read_available = frames

    def read(self, frames: int):
        self.read_calls.append(frames)
        assert frames == self.frames
        self.read_available = 0
        return self.payload, False


class FakeOutputStream:
    def __init__(self, *, underflows: list[bool] | None = None) -> None:
        self.started = False
        self.closed = False
        self.aborted = False
        self.payloads: list[bytes] = []
        self.underflows = list(underflows or [])

    def start(self) -> None:
        self.started = True

    def write(self, payload: bytes) -> bool:
        self.payloads.append(bytes(payload))
        if self.underflows:
            return self.underflows.pop(0)
        return False

    def abort(self) -> None:
        self.aborted = True

    def close(self) -> None:
        self.closed = True


class FakeSoundDevice:
    __version__ = "0.5.6"

    def __init__(
        self,
        *,
        overflowed: bool = False,
        output_underflows: list[bool] | None = None,
    ) -> None:
        self.default = SimpleNamespace(device=(0, 1))
        self.input_stream = FakeInputStream(b"\x01\x00" * 3840, overflowed=overflowed)
        self.output_stream = FakeOutputStream(underflows=output_underflows)
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


def test_named_input_device_uses_resolved_numeric_index() -> None:
    sd = FakeSoundDevice()
    config = LocalAudioConfig(input_device="Mic", output_device=1)

    validate_audio_settings(config, sounddevice_module=sd)
    source = SoundDeviceInput(config, sounddevice_module=sd)
    source.start()

    assert sd.input_checks[0]["device"] == 0
    assert sd.input_stream_kwargs["device"] == 0


def test_sounddevice_input_captures_native_rate_then_resamples_to_model_rate() -> None:
    sd = FakeSoundDevice()
    source = SoundDeviceInput(LocalAudioConfig(), sounddevice_module=sd)

    frame = source.read_frame()

    assert frame.sequence == 0
    assert frame.format == AudioFormat()
    assert len(frame.payload) == 2560
    assert sd.input_stream_kwargs["samplerate"] == 48000
    assert sd.input_stream_kwargs["blocksize"] == 3840
    assert sd.input_stream.read_calls == [3840, 3840]

    overflow_sd = FakeSoundDevice(overflowed=True)
    overflow_source = SoundDeviceInput(LocalAudioConfig(), sounddevice_module=overflow_sd)
    with pytest.raises(AudioInputOverflowError):
        overflow_source.read_frame()


def test_sounddevice_input_preserves_downsampling_state_across_capture_blocks() -> None:
    source_rate_hz = 48000
    target_rate_hz = 16000
    block_samples = 3840
    amplitude = 12000
    frequency_hz = 6000
    all_samples = array(
        "h",
        (
            round(amplitude * math.sin(2.0 * math.pi * frequency_hz * index / source_rate_hz))
            for index in range(block_samples * 3)
        ),
    )
    block_bytes = block_samples * 2
    payload = all_samples.tobytes()
    blocks = [
        payload[offset : offset + block_bytes] for offset in range(0, len(payload), block_bytes)
    ]
    sd = FakeSoundDevice()
    sd.input_stream = SequencedInputStream(blocks)
    source = SoundDeviceInput(LocalAudioConfig(), sounddevice_module=sd)

    actual = source.read_frame().payload + source.read_frame().payload
    reference = resample_pcm_s16le_mono(payload, source_rate_hz, target_rate_hz)

    assert actual == reference[: len(actual)]


def test_sounddevice_input_discards_partial_capture_block() -> None:
    sd = FakeSoundDevice()
    sd.input_stream = PartialInputStream(100)
    source = SoundDeviceInput(LocalAudioConfig(), sounddevice_module=sd)

    source.discard_pending_audio()

    assert sd.input_stream.read_calls == [100]
    assert sd.input_stream.read_available == 0


def test_pcm_resampler_preserves_block_duration() -> None:
    source = array("h", range(3840)).tobytes()

    output = resample_pcm_s16le_mono(source, 48000, 16000)

    assert len(output) == 1280 * 2
    assert resample_pcm_s16le_mono(output, 16000, 16000) == output


def test_pcm_resampler_low_passes_before_downsampling() -> None:
    source_rate_hz = 48000
    target_rate_hz = 16000
    amplitude = 12000
    sample_count = 3840

    def output_rms(frequency_hz: int) -> float:
        source = array(
            "h",
            (
                round(amplitude * math.sin(2.0 * math.pi * frequency_hz * index / source_rate_hz))
                for index in range(sample_count)
            ),
        ).tobytes()
        output = array("h")
        output.frombytes(resample_pcm_s16le_mono(source, source_rate_hz, target_rate_hz))
        steady_state = output[64:-64]
        return math.sqrt(sum(sample * sample for sample in steady_state) / len(steady_state))

    speech_band_rms = output_rms(1000)
    upper_speech_band_rms = output_rms(6000)
    just_above_nyquist_rms = output_rms(8050)
    transition_stopband_rms = output_rms(8250)

    assert speech_band_rms > amplitude * 0.5
    assert upper_speech_band_rms > speech_band_rms * 0.9
    assert just_above_nyquist_rms < speech_band_rms * 0.05
    assert transition_stopband_rms < speech_band_rms * 0.05


def test_pcm_resampler_reuses_precomputed_downsampling_kernels() -> None:
    source = array("h", range(3840)).tobytes()
    voice_devices._downsample_kernels.cache_clear()

    resample_pcm_s16le_mono(source, 48000, 16000)
    first = voice_devices._downsample_kernels.cache_info()

    assert first.misses == 1
    assert first.hits == 0

    resample_pcm_s16le_mono(source, 48000, 16000)
    second = voice_devices._downsample_kernels.cache_info()

    assert second.misses == 1
    assert second.hits == 1


def test_sounddevice_transport_writes_and_flushes_output() -> None:
    sd = FakeSoundDevice()
    transport = SoundDeviceTransport(output_device=1, sounddevice_module=sd)
    frame = AudioFrame(sequence=0, payload=b"\x00\x00" * 160, format=AudioFormat())

    transport.send(frame)
    assert sd.output_stream.payloads == [frame.payload]

    transport.flush_output()
    assert sd.output_stream.aborted is True
    assert sd.output_stream.closed is True


def test_sounddevice_transport_recovers_from_transient_underflow() -> None:
    sd = FakeSoundDevice(output_underflows=[True, False])
    transport = SoundDeviceTransport(output_device=1, sounddevice_module=sd)
    first = AudioFrame(sequence=0, payload=b"\x01\x00" * 160, format=AudioFormat())
    second = AudioFrame(sequence=1, payload=b"\x02\x00" * 160, format=AudioFormat())

    transport.send(first)
    transport.send(second)

    assert sd.output_stream.payloads == [first.payload, second.payload]
    assert transport.underflow_count == 1
    assert sd.output_stream.aborted is False
    assert sd.output_stream.closed is False


def test_sounddevice_transport_recovers_from_isolated_underflow() -> None:
    sd = FakeSoundDevice()
    sd.output_stream = FakeOutputStream(underflows=[True, False])
    transport = SoundDeviceTransport(output_device=1, sounddevice_module=sd)
    frame = AudioFrame(sequence=0, payload=b"\x00\x00" * 160, format=AudioFormat())

    transport.send(frame)
    transport.send(frame)

    assert transport.underflow_count == 1
    assert sd.output_stream.aborted is False
    assert sd.output_stream.closed is False
    assert sd.output_stream.payloads == [frame.payload, frame.payload]


def test_sounddevice_transport_fails_closed_on_persistent_underflow() -> None:
    sd = FakeSoundDevice()
    sd.output_stream = FakeOutputStream(underflows=[True, True, True])
    transport = SoundDeviceTransport(output_device=1, sounddevice_module=sd)
    frame = AudioFrame(sequence=0, payload=b"\x00\x00" * 160, format=AudioFormat())

    transport.send(frame)
    transport.send(frame)
    with pytest.raises(voice_devices.AudioOutputUnderflowError):
        transport.send(frame)

    assert transport.underflow_count == 3
    assert sd.output_stream.aborted is True
    assert sd.output_stream.closed is True
