import sys
from types import ModuleType

from cybercore import voice_entrypoint
from cybercore.voice import local_runtime


class FakeDevice:
    index = 3
    name = "USB Mic"
    can_input = True
    can_output = False
    default_input = True
    default_output = False

    def as_dict(self):
        return {"index": self.index, "name": self.name}


def test_voice_devices_routes_without_loading_foundation_cli(monkeypatch, capsys) -> None:
    monkeypatch.setattr(local_runtime, "list_audio_devices", lambda: (FakeDevice(),))

    assert voice_entrypoint.main(["voice", "devices"]) == 0
    assert "USB Mic" in capsys.readouterr().out


def test_voice_doctor_json_returns_failure_for_failed_check(monkeypatch, capsys) -> None:
    check = local_runtime.VoiceDoctorCheck("dependency:sherpa-onnx", "fail", "missing")
    monkeypatch.setattr(local_runtime, "run_local_voice_doctor", lambda path: (check,))

    assert voice_entrypoint.main(["--json", "voice", "doctor"]) == 1
    assert '"state": "fail"' in capsys.readouterr().out


def test_non_voice_commands_delegate_to_existing_entrypoint(monkeypatch) -> None:
    fake = ModuleType("cybercore.entrypoint")
    calls = []
    fake.main = lambda argv: calls.append(argv) or 7
    monkeypatch.setitem(sys.modules, "cybercore.entrypoint", fake)

    assert voice_entrypoint.main(["status"]) == 7
    assert calls == [["status"]]


def test_interactive_voice_rejects_json(capsys) -> None:
    assert voice_entrypoint.main(["--json", "voice", "local"]) == 2
    assert "not supported" in capsys.readouterr().err
