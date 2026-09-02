from __future__ import annotations

import argparse
from dataclasses import dataclass
import importlib
import json
from pathlib import Path
from typing import Any

from cybercore.voice.devices import (
    AudioDeviceError,
    LocalVoiceDependencyError,
    SoundDeviceInput,
    SoundDeviceTransport,
    list_audio_devices,
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
            devices = list_audio_devices(sounddevice_module=sd)
            checks.append(
                VoiceDoctorCheck(
                    "audio",
                    "pass",
                    f"input/output settings accepted; discovered {len(devices)} device(s)",
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
        while max_frames is None or frames < max_frames:
            frame = self.audio_input.read_frame()
            self.realtime.receive_input(frame)
            frames += 1
            if bool(getattr(self.provider.stt, "endpoint_detected", False)):
                if self.realtime.state in {RealtimeState.LISTENING, RealtimeState.INTERRUPTED}:
                    return self.realtime.finish_utterance(
                        actor_id=actor_id,
                        utterance_id=utterance_id,
                    )
        return None

    def speak(self, text: str) -> bool:
        self.open()
        self.realtime.begin_speaking(text)
        while self.realtime.state is RealtimeState.SPEAKING:
            incoming = self.audio_input.read_frame_if_available()
            if incoming is not None:
                self.realtime.receive_input(incoming)
                if self.realtime.state is RealtimeState.INTERRUPTED:
                    return True

            if self.realtime.output_buffer.snapshot().frame_count == 0:
                self.realtime.pump_synthesis(max_frames=1)
            if self.realtime.state is RealtimeState.SPEAKING:
                self.realtime.send_next_output()
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
                interrupted = local.speak(response.message)
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
