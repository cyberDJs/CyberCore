from __future__ import annotations

from array import array
from collections import deque
from dataclasses import dataclass
import importlib
import sys
from typing import Any, Iterable

from cybercore.voice.adapters import TranscriptDelta, TranscriptResult, VadResult, VadState
from cybercore.voice.audio import AudioEncoding, AudioFormat, AudioFrame
from cybercore.voice.devices import LocalVoiceDependencyError
from cybercore.voice.local_config import (
    LocalVoiceConfig,
    SherpaSttConfig,
    SherpaTtsConfig,
    SherpaVadConfig,
)


def _load_sherpa(module: Any | None = None) -> Any:
    if module is not None:
        return module
    try:
        return importlib.import_module("sherpa_onnx")
    except (ImportError, OSError) as exc:
        raise LocalVoiceDependencyError(
            "sherpa-onnx is unavailable; install CyberCore with the 'voice-local' extra"
        ) from exc


def _require_pcm_mono(frame: AudioFrame, sample_rate_hz: int | None = None) -> None:
    if frame.format.encoding is not AudioEncoding.PCM_S16LE:
        raise ValueError("sherpa adapters require PCM_S16LE audio")
    if frame.format.channels != 1:
        raise ValueError("sherpa adapters currently require mono audio")
    if sample_rate_hz is not None and frame.format.sample_rate_hz != sample_rate_hz:
        raise ValueError(
            "audio sample rate "
            f"{frame.format.sample_rate_hz} does not match model rate {sample_rate_hz}"
        )


def pcm_s16le_to_floats(payload: bytes) -> list[float]:
    samples = array("h")
    samples.frombytes(payload)
    if sys.byteorder == "big":
        samples.byteswap()
    return [sample / 32768.0 for sample in samples]


def floats_to_pcm_s16le(samples: Iterable[float]) -> bytes:
    pcm = array(
        "h",
        (max(-32768, min(32767, int(round(float(sample) * 32767.0)))) for sample in samples),
    )
    if sys.byteorder == "big":
        pcm.byteswap()
    return pcm.tobytes()


class SherpaVadAdapter:
    def __init__(
        self,
        config: SherpaVadConfig,
        *,
        sample_rate_hz: int = 16000,
        sherpa_module: Any | None = None,
    ) -> None:
        self.config = config
        self.sample_rate_hz = sample_rate_hz
        self._sherpa = _load_sherpa(sherpa_module)
        self._pending: list[float] = []
        self._detector = self._create_detector()

    def _create_detector(self) -> Any:
        model_config = self._sherpa.VadModelConfig()
        model_config.silero_vad.model = str(self.config.model)
        model_config.silero_vad.threshold = self.config.threshold
        model_config.silero_vad.min_silence_duration = self.config.min_silence_duration
        model_config.silero_vad.min_speech_duration = self.config.min_speech_duration
        model_config.silero_vad.max_speech_duration = self.config.max_speech_duration
        model_config.silero_vad.window_size = self.config.window_size
        model_config.sample_rate = self.sample_rate_hz
        model_config.num_threads = self.config.num_threads
        model_config.provider = self.config.provider
        validate = getattr(model_config, "validate", None)
        if callable(validate) and not validate():
            raise ValueError("invalid sherpa VAD configuration")
        return self._sherpa.VoiceActivityDetector(
            model_config,
            buffer_size_in_seconds=self.config.buffer_seconds,
        )

    def evaluate(self, frame: AudioFrame) -> VadResult:
        _require_pcm_mono(frame, self.sample_rate_hz)
        self._pending.extend(pcm_s16le_to_floats(frame.payload))
        while len(self._pending) >= self.config.window_size:
            window = self._pending[: self.config.window_size]
            del self._pending[: self.config.window_size]
            self._detector.accept_waveform(window)
        detected = bool(self._detector.is_speech_detected())
        empty = getattr(self._detector, "empty", None)
        pop = getattr(self._detector, "pop", None)
        if callable(empty) and callable(pop):
            while not empty():
                pop()
        return VadResult(
            state=VadState.SPEECH if detected else VadState.SILENCE,
            reason="sherpa silero-vad",
        )

    def reset(self) -> None:
        self._pending.clear()
        self._detector = self._create_detector()


class SherpaSttAdapter:
    def __init__(
        self,
        config: SherpaSttConfig,
        *,
        sherpa_module: Any | None = None,
    ) -> None:
        self.config = config
        self._sherpa = _load_sherpa(sherpa_module)
        self._recognizer = self._sherpa.OnlineRecognizer.from_transducer(
            tokens=str(config.tokens),
            encoder=str(config.encoder),
            decoder=str(config.decoder),
            joiner=str(config.joiner),
            num_threads=config.num_threads,
            sample_rate=config.sample_rate_hz,
            decoding_method=config.decoding_method,
            enable_endpoint_detection=True,
            rule2_min_trailing_silence=config.trailing_silence_s,
            rule3_min_utterance_length=config.max_utterance_s,
            provider=config.provider,
        )
        self._stream: Any = self._recognizer.create_stream()
        self._last_text = ""
        self._sequence = 0
        self._endpoint_detected = False

    @property
    def endpoint_detected(self) -> bool:
        return self._endpoint_detected

    def push(self, frame: AudioFrame) -> tuple[TranscriptDelta, ...]:
        _require_pcm_mono(frame, self.config.sample_rate_hz)
        samples = pcm_s16le_to_floats(frame.payload)
        self._stream.accept_waveform(self.config.sample_rate_hz, samples)
        while self._recognizer.is_ready(self._stream):
            self._recognizer.decode_stream(self._stream)
        result = self._recognizer.get_result_all(self._stream)
        text = str(getattr(result, "text", "")).strip()
        self._endpoint_detected = bool(self._recognizer.is_endpoint(self._stream))
        if not text or text == self._last_text:
            return ()
        self._last_text = text
        delta = TranscriptDelta(text=text, sequence=self._sequence)
        self._sequence += 1
        return (delta,)

    def finish(self) -> TranscriptResult | None:
        input_finished = getattr(self._stream, "input_finished", None)
        if callable(input_finished):
            input_finished()
        while self._recognizer.is_ready(self._stream):
            self._recognizer.decode_stream(self._stream)
        result = self._recognizer.get_result_all(self._stream)
        text = str(getattr(result, "text", "")).strip()
        if not text:
            return None
        return TranscriptResult(text=text)

    def reset(self) -> None:
        self._stream = self._recognizer.create_stream()
        self._last_text = ""
        self._sequence = 0
        self._endpoint_detected = False


class SherpaTtsAdapter:
    def __init__(
        self,
        config: SherpaTtsConfig,
        *,
        sherpa_module: Any | None = None,
    ) -> None:
        self.config = config
        self._sherpa = _load_sherpa(sherpa_module)
        vits = self._sherpa.OfflineTtsVitsModelConfig(
            model=str(config.model),
            lexicon=str(config.lexicon) if config.lexicon is not None else "",
            data_dir=str(config.data_dir) if config.data_dir is not None else "",
            tokens=str(config.tokens),
        )
        model = self._sherpa.OfflineTtsModelConfig(
            vits=vits,
            provider=config.provider,
            num_threads=config.num_threads,
            debug=False,
        )
        tts_config = self._sherpa.OfflineTtsConfig(model=model, max_num_sentences=1)
        validate = getattr(tts_config, "validate", None)
        if callable(validate) and not validate():
            raise ValueError("invalid sherpa TTS configuration")
        self._tts = self._sherpa.OfflineTts(tts_config)
        self._frames: deque[AudioFrame] = deque()
        self._sequence = 0
        self._cancelled = False

    def start(self, text: str) -> None:
        if not text.strip():
            raise ValueError("TTS text must not be empty")
        self.reset()
        generation = self._sherpa.GenerationConfig()
        generation.sid = self.config.speaker_id
        generation.speed = self.config.speed
        generation.silence_scale = self.config.silence_scale
        audio = self._tts.generate(text, generation)
        if self._cancelled:
            return
        sample_rate = int(getattr(audio, "sample_rate", 0))
        if sample_rate <= 0:
            raise RuntimeError("sherpa TTS returned an invalid sample rate")
        samples = list(getattr(audio, "samples", ()))
        chunk_samples = max(1, round(sample_rate * self.config.chunk_ms / 1000))
        audio_format = AudioFormat(sample_rate_hz=sample_rate, channels=1)
        for start in range(0, len(samples), chunk_samples):
            payload = floats_to_pcm_s16le(samples[start : start + chunk_samples])
            if not payload:
                continue
            self._frames.append(
                AudioFrame(
                    sequence=self._sequence,
                    payload=payload,
                    format=audio_format,
                )
            )
            self._sequence += 1

    def pull(self) -> AudioFrame | None:
        if not self._frames:
            return None
        return self._frames.popleft()

    def cancel(self) -> None:
        self._cancelled = True
        self._frames.clear()

    def reset(self) -> None:
        self._cancelled = False
        self._frames.clear()
        self._sequence = 0


@dataclass
class SherpaSpeechProvider:
    vad: SherpaVadAdapter
    stt: SherpaSttAdapter
    tts: SherpaTtsAdapter

    @classmethod
    def from_config(
        cls,
        config: LocalVoiceConfig,
        *,
        sherpa_module: Any | None = None,
    ) -> SherpaSpeechProvider:
        module = _load_sherpa(sherpa_module)
        return cls(
            vad=SherpaVadAdapter(
                config.vad,
                sample_rate_hz=config.audio.sample_rate_hz,
                sherpa_module=module,
            ),
            stt=SherpaSttAdapter(config.stt, sherpa_module=module),
            tts=SherpaTtsAdapter(config.tts, sherpa_module=module),
        )
