from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
import importlib
import json
from pathlib import Path
import threading
import time
from typing import Any

from cybercore.voice.adapters import VadState
from cybercore.voice.devices import (
    AudioDeviceError,
    LocalVoiceDependencyError,
    SoundDeviceInput,
    SoundDeviceTransport,
    list_audio_devices,
    native_input_sample_rate_hz,
    validate_audio_settings,
)
from cybercore.voice.local_config import (
    LocalVoiceConfig,
    LocalVoiceConfigError,
    load_local_voice_config,
)
from cybercore.voice.models import ResponseStatus, Utterance, VoiceContext
from cybercore.voice.providers.sherpa import SherpaSpeechProvider
from cybercore.voice.realtime import RealtimeState, RealtimeVoiceRuntime
from cybercore.voice.session import SessionStatus, VoiceSession


@dataclass(frozen=True)
class VoiceDoctorCheck:
    name: str
    state: str
    detail: str

    @property
    def successful(self) -> bool:
        return self.state in {"pass", "warn"}

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "state": self.state, "detail": self.detail}


def _import_dependency(name: str, supplied: Any | None) -> Any:
    if supplied is not None:
        return supplied
    try:
        return importlib.import_module(name)
    except (ImportError, OSError) as exc:
        raise LocalVoiceDependencyError(
            f"{name} is unavailable; install CyberCore with the 'voice-local' extra"
        ) from exc


def _dependency_version(module: Any) -> str:
    return str(getattr(module, "__version__", "unknown"))


def _validate_sherpa_api(module: Any) -> None:
    required = (
        "GenerationConfig",
        "OfflineTts",
        "OfflineTtsConfig",
        "OfflineTtsModelConfig",
        "OfflineTtsVitsModelConfig",
        "OnlineRecognizer",
        "VadModelConfig",
        "VoiceActivityDetector",
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise LocalVoiceDependencyError(
            "sherpa-onnx API is missing required symbol(s): " + ", ".join(missing)
        )


def _path_check(config: LocalVoiceConfig) -> tuple[VoiceDoctorCheck, ...]:
    checks: list[VoiceDoctorCheck] = []
    for name, path, kind in config.required_paths():
        if kind == "file":
            exists = path.is_file()
        else:
            exists = path.is_dir()
        checks.append(
            VoiceDoctorCheck(
                name=f"model:{name}",
                state="pass" if exists else "fail",
                detail=str(path) if exists else f"missing {kind}: {path}",
            )
        )
    return tuple(checks)


def run_local_voice_doctor(
    config_path: Path | str | None = None,
    *,
    config: LocalVoiceConfig | None = None,
    sounddevice_module: Any | None = None,
    sherpa_module: Any | None = None,
) -> tuple[VoiceDoctorCheck, ...]:
    checks: list[VoiceDoctorCheck] = []

    sd: Any | None = None
    try:
        sd = _import_dependency("sounddevice", sounddevice_module)
        checks.append(
            VoiceDoctorCheck(
                "dependency:sounddevice",
                "pass",
                f"available version={_dependency_version(sd)}",
            )
        )
    except LocalVoiceDependencyError as exc:
        checks.append(VoiceDoctorCheck("dependency:sounddevice", "fail", str(exc)))

    sherpa: Any | None = None
    try:
        sherpa = _import_dependency("sherpa_onnx", sherpa_module)
        _validate_sherpa_api(sherpa)
        checks.append(
            VoiceDoctorCheck(
                "dependency:sherpa-onnx",
                "pass",
                f"available version={_dependency_version(sherpa)}",
            )
        )
    except LocalVoiceDependencyError as exc:
        checks.append(VoiceDoctorCheck("dependency:sherpa-onnx", "fail", str(exc)))

    resolved_config = config
    if resolved_config is None:
        try:
            resolved_config = load_local_voice_config(config_path)
            checks.append(VoiceDoctorCheck("config", "pass", "local voice config loaded"))
        except LocalVoiceConfigError as exc:
            checks.append(VoiceDoctorCheck("config", "fail", str(exc)))
            return tuple(checks)
    else:
        checks.append(VoiceDoctorCheck("config", "pass", "local voice config supplied"))

    path_checks = _path_check(resolved_config)
    checks.extend(path_checks)

    if sd is not None:
        try:
            validate_audio_settings(resolved_config.audio, sounddevice_module=sd)
            input_rate = native_input_sample_rate_hz(resolved_config.audio, sounddevice_module=sd)
            devices = list_audio_devices(sounddevice_module=sd)
            checks.append(
                VoiceDoctorCheck(
                    "audio",
                    "pass",
                    "input/output settings accepted; "
                    f"capture {input_rate} Hz -> model {resolved_config.audio.sample_rate_hz} Hz; "
                    f"discovered {len(devices)} device(s)",
                )
            )
        except (AudioDeviceError, LocalVoiceDependencyError, OSError, RuntimeError) as exc:
            checks.append(VoiceDoctorCheck("audio", "fail", str(exc)))

    if sherpa is not None and all(check.successful for check in path_checks):
        checks.append(
            VoiceDoctorCheck(
                "provider:sherpa-onnx",
                "pass",
                "required API surface and configured model paths are available",
            )
        )

    return tuple(checks)


class LocalSpeechRuntime:
    def __init__(
        self,
        *,
        config: LocalVoiceConfig,
        session: VoiceSession,
        provider: Any,
        audio_input: Any,
        transport: Any,
    ) -> None:
        self.config = config
        self.session = session
        self.provider = provider
        self.audio_input = audio_input
        self.transport = transport
        self.realtime = RealtimeVoiceRuntime(
            session=session,
            vad=provider.vad,
            stt=provider.stt,
            tts=provider.tts,
            transport=transport,
        )
        self._opened = False

    @classmethod
    def from_config(
        cls,
        config: LocalVoiceConfig,
        *,
        session: VoiceSession | None = None,
        sounddevice_module: Any | None = None,
        sherpa_module: Any | None = None,
    ) -> LocalSpeechRuntime:
        validate_audio_settings(config.audio, sounddevice_module=sounddevice_module)
        provider = SherpaSpeechProvider.from_config(config, sherpa_module=sherpa_module)
        audio_input = SoundDeviceInput(
            config.audio,
            sounddevice_module=sounddevice_module,
        )
        transport = SoundDeviceTransport(
            output_device=config.audio.output_device,
            sounddevice_module=sounddevice_module,
        )
        return cls(
            config=config,
            session=session or VoiceSession("local-voice"),
            provider=provider,
            audio_input=audio_input,
            transport=transport,
        )

    def open(self) -> None:
        if self._opened:
            return
        self.audio_input.start()
        self._opened = True

    def close(self) -> None:
        try:
            self.audio_input.close()
        finally:
            self.transport.close()
            self._opened = False

    def _reset_vad(self, reason: str) -> None:
        reset = getattr(self.provider.vad, "reset", None)
        if not callable(reset):
            if self.realtime.state is not RealtimeState.CANCELLED:
                self.realtime.cancel(f"VAD reset unavailable: {reason}")
            raise RuntimeError("local voice VAD does not support reset")
        try:
            reset()
        except Exception:
            if self.realtime.state is not RealtimeState.CANCELLED:
                self.realtime.cancel(f"VAD reset failed: {reason}")
            raise

    def _input_preroll_frame_limit(self) -> int:
        block_ms = int(getattr(getattr(self.config, "audio", None), "block_ms", 80))
        return max(1, round(500 / block_ms))

    def _begin_listening_with_preroll(self, preroll: deque[Any], speech_frame: Any) -> None:
        self.realtime.start_listening()
        self._reset_vad("input pre-roll replay started")
        for buffered in (*preroll, speech_frame):
            self.realtime.receive_input(buffered)
        preroll.clear()

    def capture_utterance(
        self,
        *,
        actor_id: str,
        utterance_id: str,
        max_frames: int | None = None,
    ) -> Utterance | None:
        if self.realtime.state is RealtimeState.CANCELLED:
            raise RuntimeError("local speech runtime is cancelled")
        self.open()
        frames = 0
        preroll: deque[Any] = deque(maxlen=self._input_preroll_frame_limit())
        while max_frames is None or frames < max_frames:
            frame = self.audio_input.read_frame()
            frames += 1

            if self.realtime.state is RealtimeState.IDLE:
                vad = self.provider.vad.evaluate(frame)
                if vad.state is not VadState.SPEECH:
                    preroll.append(frame)
                    continue
                self._begin_listening_with_preroll(preroll, frame)
            else:
                self.realtime.receive_input(frame)

            if bool(getattr(self.provider.stt, "endpoint_detected", False)):
                if self.realtime.state in {RealtimeState.LISTENING, RealtimeState.INTERRUPTED}:
                    utterance = self.realtime.finish_utterance(
                        actor_id=actor_id,
                        utterance_id=utterance_id,
                    )
                    self._reset_vad("input turn finalized")
                    return utterance
        return None

    def _begin_speaking_with_live_input(self, text: str) -> None:
        stop = threading.Event()
        errors: list[Exception] = []
        block_ms = int(getattr(getattr(self.config, "audio", None), "block_ms", 80))
        idle_sleep = max(0.005, min(0.05, block_ms / 4000))

        def pump_input() -> None:
            while not stop.is_set():
                try:
                    incoming = self.audio_input.read_frame_if_available()
                    if incoming is None:
                        time.sleep(idle_sleep)
                except Exception as exc:
                    errors.append(exc)
                    stop.set()

        thread = threading.Thread(
            target=pump_input,
            name="cybercore-voice-input-pump",
            daemon=True,
        )
        thread.start()
        try:
            self.realtime.begin_speaking(text)
        finally:
            stop.set()
            thread.join(timeout=max(1.0, block_ms / 1000 * 4))

        if thread.is_alive():
            self.realtime.cancel("microphone pump did not stop after TTS synthesis")
            raise RuntimeError("microphone input pump did not stop")
        if errors:
            if self.realtime.state is not RealtimeState.CANCELLED:
                self.realtime.cancel("microphone input failed during TTS synthesis")
            raise errors[0]

    def _drain_microphone_input(self, reason: str) -> None:
        try:
            while self.audio_input.read_frame_if_available() is not None:
                pass
        except Exception:
            if self.realtime.state is not RealtimeState.CANCELLED:
                self.realtime.cancel(f"microphone input failed while {reason}")
            raise

    def speak(self, text: str) -> bool:
        self.open()
        self._begin_speaking_with_live_input(text)
        self._drain_microphone_input("preparing local half-duplex playback")

        while self.realtime.state is RealtimeState.SPEAKING:
            self._drain_microphone_input("draining local half-duplex playback input")
            if self.realtime.output_buffer.snapshot().frame_count == 0:
                self.realtime.pump_synthesis(max_frames=1)
            if self.realtime.state is RealtimeState.SPEAKING:
                self.realtime.send_next_output()
            self._drain_microphone_input("draining local half-duplex playback input")
        return self.realtime.state is RealtimeState.INTERRUPTED

    def cancel(self, reason: str = "operator cancellation") -> None:
        self.realtime.cancel(reason)


def run_local_voice_session(
    config: LocalVoiceConfig,
    *,
    actor_id: str = "local-operator",
    once: bool = False,
) -> int:
    from cybercore.voice.router import VoiceRouter

    local = LocalSpeechRuntime.from_config(config)
    router = VoiceRouter()
    context = VoiceContext()
    turn = 0
    try:
        local.open()
        while local.session.status is not SessionStatus.CANCELLED:
            turn += 1
            print("CYBER VOICE: LISTENING")
            utterance = local.capture_utterance(
                actor_id=actor_id,
                utterance_id=f"local:{local.session.session_id}:{turn}",
            )
            if utterance is None:
                continue
            print(f"YOU: {utterance.text}")
            response = router.handle(
                utterance,
                context,
                session=local.session,
            )
            print(f"CYBER VOICE [{response.status.value}]: {response.message}")

            if response.status is ResponseStatus.CANCELLED:
                local.cancel("voice cancellation intent")
                return 0

            interrupted = False
            if local.realtime.state is RealtimeState.PROCESSING and response.message.strip():
                print("CYBER VOICE: SPEAKING")
                interrupted = local.speak(response.message)
                if interrupted:
                    print("CYBER VOICE: INTERRUPTED")
            if once and not interrupted:
                return 0
        return 0
    except KeyboardInterrupt:
        if local.realtime.state is not RealtimeState.CANCELLED:
            local.cancel("keyboard interrupt")
        return 130
    finally:
        local.close()


def _voice_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cybercore",
        description="CyberCore Foundation Runtime",
    )
    parser.add_argument("--repo", help="CyberCore repository path")
    parser.add_argument("--json", action="store_true", dest="as_json")
    sub = parser.add_subparsers(dest="command", required=True)
    voice = sub.add_parser("voice", help="Use the local Cyber Voice speech runtime")
    voice_sub = voice.add_subparsers(dest="voice_command", required=True)
    voice_sub.add_parser("devices", help="List local audio devices")
    doctor = voice_sub.add_parser("doctor", help="Verify local Voice dependencies and config")
    doctor.add_argument("--config", type=Path)
    local = voice_sub.add_parser("local", help="Run the local microphone/speaker Voice loop")
    local.add_argument("--config", type=Path)
    local.add_argument("--actor", default="local-operator")
    local.add_argument("--once", action="store_true")
    return parser


def _render_devices(devices: tuple[Any, ...]) -> str:
    lines = []
    for device in devices:
        modes = []
        if device.can_input:
            modes.append("IN")
        if device.can_output:
            modes.append("OUT")
        defaults = []
        if device.default_input:
            defaults.append("default-in")
        if device.default_output:
            defaults.append("default-out")
        suffix = f" ({', '.join(defaults)})" if defaults else ""
        lines.append(f"{device.index:>3} {'/'.join(modes) or '-':<7} {device.name}{suffix}")
    return "\n".join(lines)


def run_voice_cli(arguments: list[str]) -> int:
    args = _voice_parser().parse_args(arguments)
    if args.voice_command == "devices":
        devices = list_audio_devices()
        if args.as_json:
            print(json.dumps([device.as_dict() for device in devices], indent=2))
        else:
            print(_render_devices(devices))
        return 0

    if args.voice_command == "doctor":
        checks = run_local_voice_doctor(args.config)
        if args.as_json:
            print(json.dumps([check.as_dict() for check in checks], indent=2))
        else:
            for check in checks:
                print(f"{check.state.upper():5} {check.name}: {check.detail}")
        return 0 if all(check.successful for check in checks) else 1

    if args.as_json:
        raise ValueError("--json is not supported for the interactive local voice session")
    config = load_local_voice_config(args.config)
    return run_local_voice_session(
        config,
        actor_id=args.actor,
        once=args.once,
    )
