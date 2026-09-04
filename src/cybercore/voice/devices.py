from __future__ import annotations

from array import array
from collections import deque
from dataclasses import dataclass
from functools import lru_cache
import importlib
import math
import sys
from typing import Any

from cybercore.voice.audio import AudioEncoding, AudioFormat, AudioFrame
from cybercore.voice.local_config import LocalAudioConfig


class LocalVoiceDependencyError(RuntimeError):
    pass


class AudioDeviceError(RuntimeError):
    pass


class AudioInputOverflowError(AudioDeviceError):
    pass


class AudioOutputUnderflowError(AudioDeviceError):
    pass


def _load_sounddevice(module: Any | None = None) -> Any:
    if module is not None:
        return module
    try:
        return importlib.import_module("sounddevice")
    except (ImportError, OSError) as exc:
        raise LocalVoiceDependencyError(
            "sounddevice is unavailable; install CyberCore with the 'voice-local' extra"
        ) from exc


@dataclass(frozen=True)
class AudioDeviceInfo:
    index: int
    name: str
    hostapi: int | None
    max_input_channels: int
    max_output_channels: int
    default_sample_rate: float
    default_input: bool = False
    default_output: bool = False

    @property
    def can_input(self) -> bool:
        return self.max_input_channels > 0

    @property
    def can_output(self) -> bool:
        return self.max_output_channels > 0

    def as_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "name": self.name,
            "hostapi": self.hostapi,
            "max_input_channels": self.max_input_channels,
            "max_output_channels": self.max_output_channels,
            "default_sample_rate": self.default_sample_rate,
            "default_input": self.default_input,
            "default_output": self.default_output,
        }


def list_audio_devices(*, sounddevice_module: Any | None = None) -> tuple[AudioDeviceInfo, ...]:
    sd = _load_sounddevice(sounddevice_module)
    devices = sd.query_devices()
    default_pair = getattr(getattr(sd, "default", object()), "device", (None, None))
    try:
        default_input = default_pair[0]
        default_output = default_pair[1]
    except (TypeError, IndexError):
        default_input = None
        default_output = None

    result: list[AudioDeviceInfo] = []
    for index, item in enumerate(devices):
        result.append(
            AudioDeviceInfo(
                index=index,
                name=str(item.get("name", f"device-{index}")),
                hostapi=int(item["hostapi"]) if item.get("hostapi") is not None else None,
                max_input_channels=int(item.get("max_input_channels", 0)),
                max_output_channels=int(item.get("max_output_channels", 0)),
                default_sample_rate=float(item.get("default_samplerate", 0.0)),
                default_input=index == default_input,
                default_output=index == default_output,
            )
        )
    return tuple(result)


def _resolve_input_device(sd: Any, device: int | str | None) -> tuple[int, Any]:
    devices = sd.query_devices()
    if device is None:
        default_pair = getattr(getattr(sd, "default", object()), "device", (None, None))
        try:
            default_input = default_pair[0]
        except (TypeError, IndexError) as exc:
            raise AudioDeviceError("no default input device is available") from exc
        if default_input is None:
            raise AudioDeviceError("no default input device is available")
        try:
            index = int(default_input)
        except (TypeError, ValueError) as exc:
            raise AudioDeviceError("no default input device is available") from exc
    elif isinstance(device, int):
        index = device
    else:
        matches = [
            (index, item)
            for index, item in enumerate(devices)
            if str(item.get("name", "")) == device and int(item.get("max_input_channels", 0)) > 0
        ]
        if len(matches) != 1:
            raise AudioDeviceError(f"input device name must resolve exactly once: {device}")
        return matches[0]

    if index < 0 or index >= len(devices):
        raise AudioDeviceError(f"input device index is out of range: {index}")
    item = devices[index]
    if int(item.get("max_input_channels", 0)) <= 0:
        raise AudioDeviceError(f"device {index} has no input channels")
    return index, item


def _resolved_input_device_and_sample_rate(
    config: LocalAudioConfig,
    *,
    sounddevice_module: Any | None = None,
) -> tuple[int, int]:
    sd = _load_sounddevice(sounddevice_module)
    index, item = _resolve_input_device(sd, config.input_device)
    sample_rate = round(float(item.get("default_samplerate", 0.0)))
    if sample_rate <= 0:
        raise AudioDeviceError("input device reported an invalid native sample rate")
    return index, sample_rate


def native_input_sample_rate_hz(
    config: LocalAudioConfig,
    *,
    sounddevice_module: Any | None = None,
) -> int:
    _, sample_rate = _resolved_input_device_and_sample_rate(
        config, sounddevice_module=sounddevice_module
    )
    return sample_rate


def _normalized_sinc(value: float) -> float:
    if abs(value) < 1e-12:
        return 1.0
    scaled = math.pi * value
    return math.sin(scaled) / scaled


@lru_cache(maxsize=32)
def _downsample_kernels(
    source_rate_hz: int,
    target_rate_hz: int,
    half_width: int = 36,
) -> tuple[int, int, tuple[tuple[float, ...], ...], tuple[float, ...]]:
    common_rate = math.gcd(source_rate_hz, target_rate_hz)
    phase_count = target_rate_hz // common_rate
    cutoff = 0.45 * target_rate_hz / source_rate_hz
    first_offset = -half_width + 1
    kernels: list[tuple[float, ...]] = []
    totals: list[float] = []

    for phase in range(phase_count):
        fraction = phase / phase_count
        weights: list[float] = []
        for offset in range(first_offset, half_width + 1):
            distance = offset - fraction
            window = 0.54 + 0.46 * math.cos(math.pi * distance / half_width)
            weight = 2.0 * cutoff * _normalized_sinc(2.0 * cutoff * distance) * window
            weights.append(weight)
        kernel = tuple(weights)
        kernels.append(kernel)
        totals.append(sum(kernel))

    return common_rate, first_offset, tuple(kernels), tuple(totals)


def _downsample_pcm_s16le(
    source: list[int],
    source_rate_hz: int,
    target_rate_hz: int,
    output_count: int,
) -> list[int]:
    common_rate, first_offset, kernels, kernel_totals = _downsample_kernels(
        source_rate_hz, target_rate_hz
    )
    last_offset = first_offset + len(kernels[0]) - 1
    output: list[int] = []

    for index in range(output_count):
        numerator = index * source_rate_hz
        center = numerator // target_rate_hz
        residue = numerator % target_rate_hz
        phase = residue // common_rate
        kernel = kernels[phase]

        low_offset = max(first_offset, -center)
        high_offset = min(last_offset, len(source) - 1 - center)
        kernel_start = low_offset - first_offset
        kernel_stop = high_offset - first_offset + 1

        weighted = 0.0
        sample_index = center + low_offset
        for kernel_index in range(kernel_start, kernel_stop):
            weighted += source[sample_index] * kernel[kernel_index]
            sample_index += 1

        if low_offset == first_offset and high_offset == last_offset:
            total_weight = kernel_totals[phase]
        else:
            total_weight = sum(kernel[kernel_start:kernel_stop])

        if abs(total_weight) < 1e-12:
            fallback = min(max(round(numerator / target_rate_hz), 0), len(source) - 1)
            value = source[fallback]
        else:
            value = round(weighted / total_weight)
        output.append(max(-32768, min(32767, value)))

    return output


class _StreamingDownsampler:
    def __init__(self, source_rate_hz: int, target_rate_hz: int) -> None:
        if target_rate_hz >= source_rate_hz:
            raise ValueError("streaming downsampler requires target rate below source rate")
        self.source_rate_hz = source_rate_hz
        self.target_rate_hz = target_rate_hz
        self._common_rate, self._first_offset, self._kernels, self._kernel_totals = (
            _downsample_kernels(source_rate_hz, target_rate_hz)
        )
        self._last_offset = self._first_offset + len(self._kernels[0]) - 1
        self.reset()

    def reset(self) -> None:
        self._source: list[int] = []
        self._source_start = 0
        self._source_count = 0
        self._next_output_index = 0
        self._output: deque[int] = deque()

    @property
    def available_samples(self) -> int:
        return len(self._output)

    def feed(self, payload: bytes) -> None:
        if len(payload) % 2:
            raise ValueError("PCM_S16LE payload must contain complete samples")
        samples = array("h")
        samples.frombytes(payload)
        if sys.byteorder == "big":
            samples.byteswap()
        self._source.extend(samples)
        self._source_count += len(samples)
        self._produce_available_output()
        self._trim_consumed_source()

    def pop_payload(self, sample_count: int) -> bytes:
        if sample_count < 0 or sample_count > len(self._output):
            raise ValueError("requested streaming output is not available")
        pcm = array("h", (self._output.popleft() for _ in range(sample_count)))
        if sys.byteorder == "big":
            pcm.byteswap()
        return pcm.tobytes()

    def _produce_available_output(self) -> None:
        last_available = self._source_count - 1
        while True:
            numerator = self._next_output_index * self.source_rate_hz
            center = numerator // self.target_rate_hz
            residue = numerator % self.target_rate_hz
            phase = residue // self._common_rate
            high_source = center + self._last_offset
            if high_source > last_available:
                return

            kernel = self._kernels[phase]
            low_offset = max(self._first_offset, -center)
            kernel_start = low_offset - self._first_offset
            weighted = 0.0
            sample_global = center + low_offset
            sample_index = sample_global - self._source_start
            for kernel_index in range(kernel_start, len(kernel)):
                weighted += self._source[sample_index] * kernel[kernel_index]
                sample_index += 1

            if low_offset == self._first_offset:
                total_weight = self._kernel_totals[phase]
            else:
                total_weight = sum(kernel[kernel_start:])
            if abs(total_weight) < 1e-12:
                fallback_global = min(
                    max(round(numerator / self.target_rate_hz), 0), last_available
                )
                value = self._source[fallback_global - self._source_start]
            else:
                value = round(weighted / total_weight)
            self._output.append(max(-32768, min(32767, value)))
            self._next_output_index += 1

    def _trim_consumed_source(self) -> None:
        numerator = self._next_output_index * self.source_rate_hz
        center = numerator // self.target_rate_hz
        minimum_needed = max(0, center + self._first_offset)
        trim_count = minimum_needed - self._source_start
        if trim_count <= 0:
            return
        del self._source[:trim_count]
        self._source_start += trim_count


def resample_pcm_s16le_mono(payload: bytes, source_rate_hz: int, target_rate_hz: int) -> bytes:
    if source_rate_hz <= 0 or target_rate_hz <= 0:
        raise ValueError("sample rates must be positive")
    if len(payload) % 2:
        raise ValueError("PCM_S16LE payload must contain complete samples")
    if source_rate_hz == target_rate_hz or not payload:
        return payload

    samples = array("h")
    samples.frombytes(payload)
    if sys.byteorder == "big":
        samples.byteswap()
    source = list(samples)
    output_count = max(1, round(len(source) * target_rate_hz / source_rate_hz))

    output: list[int]
    if len(source) == 1:
        output = [source[0]] * output_count
    elif target_rate_hz < source_rate_hz:
        output = _downsample_pcm_s16le(source, source_rate_hz, target_rate_hz, output_count)
    else:
        ratio = source_rate_hz / target_rate_hz
        output = []
        for index in range(output_count):
            position = min(index * ratio, len(source) - 1)
            left = int(position)
            right = min(left + 1, len(source) - 1)
            fraction = position - left
            value = round(source[left] + (source[right] - source[left]) * fraction)
            output.append(max(-32768, min(32767, value)))

    pcm = array("h", output)
    if sys.byteorder == "big":
        pcm.byteswap()
    return pcm.tobytes()


def validate_audio_settings(
    config: LocalAudioConfig,
    *,
    sounddevice_module: Any | None = None,
) -> None:
    sd = _load_sounddevice(sounddevice_module)
    try:
        input_device_index, input_sample_rate = _resolved_input_device_and_sample_rate(
            config, sounddevice_module=sd
        )
        sd.check_input_settings(
            device=input_device_index,
            channels=config.channels,
            dtype="int16",
            samplerate=input_sample_rate,
        )
        sd.check_output_settings(
            device=config.output_device,
            channels=config.channels,
            dtype="int16",
            samplerate=config.sample_rate_hz,
        )
    except AudioDeviceError:
        raise
    except Exception as exc:
        raise AudioDeviceError(f"audio device settings are not supported: {exc}") from exc


class SoundDeviceInput:
    def __init__(
        self,
        config: LocalAudioConfig,
        *,
        sounddevice_module: Any | None = None,
    ) -> None:
        self.config = config
        self._sd = _load_sounddevice(sounddevice_module)
        self._stream: Any | None = None
        self._sequence = 0
        self._device_index, self._device_sample_rate_hz = _resolved_input_device_and_sample_rate(
            config, sounddevice_module=self._sd
        )
        self._device_frames_per_block = max(
            1, round(self._device_sample_rate_hz * config.block_ms / 1000)
        )
        self._model_frames_per_block = max(1, round(config.sample_rate_hz * config.block_ms / 1000))
        self._downsampler = (
            _StreamingDownsampler(self._device_sample_rate_hz, config.sample_rate_hz)
            if config.sample_rate_hz < self._device_sample_rate_hz
            else None
        )

    @property
    def audio_format(self) -> AudioFormat:
        return AudioFormat(
            sample_rate_hz=self.config.sample_rate_hz,
            channels=self.config.channels,
            sample_width_bytes=2,
            encoding=AudioEncoding.PCM_S16LE,
        )

    @property
    def device_sample_rate_hz(self) -> int:
        return self._device_sample_rate_hz

    def start(self) -> None:
        if self._stream is not None:
            return
        stream = self._sd.RawInputStream(
            samplerate=self._device_sample_rate_hz,
            blocksize=self._device_frames_per_block,
            device=self._device_index,
            channels=self.config.channels,
            dtype="int16",
        )
        stream.start()
        self._stream = stream

    def _ensure_stream(self) -> Any:
        if self._stream is None:
            self.start()
        assert self._stream is not None
        return self._stream

    def _read_device_payload(self, frames: int) -> bytes:
        stream = self._ensure_stream()
        data, overflowed = stream.read(frames)
        if overflowed:
            if self._downsampler is not None:
                self._downsampler.reset()
            raise AudioInputOverflowError(
                "microphone input overflowed; audio frame rejected instead of hiding loss"
            )
        return bytes(data)

    def _build_frame(self, payload: bytes) -> AudioFrame:
        frame = AudioFrame(
            sequence=self._sequence,
            payload=payload,
            format=self.audio_format,
        )
        self._sequence += 1
        return frame

    def _feed_downsampler_block(self) -> None:
        assert self._downsampler is not None
        self._downsampler.feed(self._read_device_payload(self._device_frames_per_block))

    def read_frame(self) -> AudioFrame:
        if self._downsampler is None:
            payload = resample_pcm_s16le_mono(
                self._read_device_payload(self._device_frames_per_block),
                self._device_sample_rate_hz,
                self.config.sample_rate_hz,
            )
            return self._build_frame(payload)

        while self._downsampler.available_samples < self._model_frames_per_block:
            self._feed_downsampler_block()
        return self._build_frame(self._downsampler.pop_payload(self._model_frames_per_block))

    def read_frame_if_available(self) -> AudioFrame | None:
        stream = self._ensure_stream()
        if self._downsampler is None:
            available = int(getattr(stream, "read_available", 0))
            if available < self._device_frames_per_block:
                return None
            return self.read_frame()

        if self._downsampler.available_samples >= self._model_frames_per_block:
            return self._build_frame(self._downsampler.pop_payload(self._model_frames_per_block))
        available = int(getattr(stream, "read_available", 0))
        if available < self._device_frames_per_block:
            return None
        self._feed_downsampler_block()
        if self._downsampler.available_samples < self._model_frames_per_block:
            return None
        return self._build_frame(self._downsampler.pop_payload(self._model_frames_per_block))

    def discard_pending_audio(self) -> None:
        stream = self._ensure_stream()
        available = int(getattr(stream, "read_available", 0))
        if available > 0:
            self._read_device_payload(available)
        if self._downsampler is not None:
            self._downsampler.reset()

    def close(self) -> None:
        stream, self._stream = self._stream, None
        if self._downsampler is not None:
            self._downsampler.reset()
        if stream is None:
            return
        try:
            stream.stop()
        finally:
            stream.close()


class SoundDeviceTransport:
    def __init__(
        self,
        *,
        output_device: int | str | None = None,
        sounddevice_module: Any | None = None,
    ) -> None:
        self.output_device = output_device
        self._sd = _load_sounddevice(sounddevice_module)
        self._stream: Any | None = None
        self._format: AudioFormat | None = None
        self._underflow_count = 0

    @property
    def underflow_count(self) -> int:
        return self._underflow_count

    def _open(self, audio_format: AudioFormat) -> Any:
        if audio_format.encoding is not AudioEncoding.PCM_S16LE:
            raise AudioDeviceError("sounddevice transport only accepts PCM_S16LE frames")
        if self._stream is not None and self._format == audio_format:
            return self._stream
        self.flush_output()
        stream = self._sd.RawOutputStream(
            samplerate=audio_format.sample_rate_hz,
            blocksize=0,
            device=self.output_device,
            channels=audio_format.channels,
            dtype="int16",
        )
        stream.start()
        self._stream = stream
        self._format = audio_format
        return stream

    def send(self, frame: AudioFrame) -> None:
        stream = self._open(frame.format)
        underflowed = stream.write(frame.payload)
        if underflowed:
            self._underflow_count += 1

    def flush_output(self) -> None:
        stream, self._stream = self._stream, None
        self._format = None
        if stream is None:
            return
        abort = getattr(stream, "abort", None)
        try:
            if callable(abort):
                abort()
            else:
                stop = getattr(stream, "stop", None)
                if callable(stop):
                    stop()
        finally:
            close = getattr(stream, "close", None)
            if callable(close):
                close()

    def close(self) -> None:
        self.flush_output()
