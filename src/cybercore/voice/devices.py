from __future__ import annotations

from dataclasses import dataclass
import importlib
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


def validate_audio_settings(
    config: LocalAudioConfig,
    *,
    sounddevice_module: Any | None = None,
) -> None:
    sd = _load_sounddevice(sounddevice_module)
    try:
        sd.check_input_settings(
            device=config.input_device,
            channels=config.channels,
            dtype="int16",
            samplerate=config.sample_rate_hz,
        )
        sd.check_output_settings(
            device=config.output_device,
            channels=config.channels,
            dtype="int16",
            samplerate=config.sample_rate_hz,
        )
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

    @property
    def audio_format(self) -> AudioFormat:
        return AudioFormat(
            sample_rate_hz=self.config.sample_rate_hz,
            channels=self.config.channels,
            sample_width_bytes=2,
            encoding=AudioEncoding.PCM_S16LE,
        )

    def start(self) -> None:
        if self._stream is not None:
            return
        stream = self._sd.RawInputStream(
            samplerate=self.config.sample_rate_hz,
            blocksize=self.config.frames_per_block,
            device=self.config.input_device,
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

    def read_frame(self) -> AudioFrame:
        stream = self._ensure_stream()
        data, overflowed = stream.read(self.config.frames_per_block)
        if overflowed:
            raise AudioInputOverflowError(
                "microphone input overflowed; audio frame rejected instead of hiding loss"
            )
        frame = AudioFrame(
            sequence=self._sequence,
            payload=bytes(data),
            format=self.audio_format,
        )
        self._sequence += 1
        return frame

    def read_frame_if_available(self) -> AudioFrame | None:
        stream = self._ensure_stream()
        available = int(getattr(stream, "read_available", 0))
        if available < self.config.frames_per_block:
            return None
        return self.read_frame()

    def close(self) -> None:
        stream, self._stream = self._stream, None
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
            self.flush_output()
            raise AudioOutputUnderflowError(
                "speaker output underflowed; output was flushed to avoid stale speech"
            )

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
