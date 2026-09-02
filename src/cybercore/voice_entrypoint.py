from __future__ import annotations

import sys


def _has_voice_command(arguments: list[str]) -> bool:
    index = 0
    while index < len(arguments):
        token = arguments[index]
        if token == "--repo":
            index += 2
            continue
        if token == "--json":
            index += 1
            continue
        return token == "voice"
    return False


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not _has_voice_command(arguments):
        from cybercore.entrypoint import main as foundation_main

        return foundation_main(arguments)

    from cybercore.voice.local_runtime import run_voice_cli

    try:
        return run_voice_cli(arguments)
    except Exception as exc:
        from cybercore.voice.devices import AudioDeviceError, LocalVoiceDependencyError
        from cybercore.voice.local_config import LocalVoiceConfigError

        handled = (
            AudioDeviceError,
            FileNotFoundError,
            LocalVoiceConfigError,
            LocalVoiceDependencyError,
            OSError,
            RuntimeError,
            ValueError,
        )
        if not isinstance(exc, handled):
            raise
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
