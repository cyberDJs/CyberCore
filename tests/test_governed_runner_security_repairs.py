from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import subprocess
import sys
import time

import pytest

import cybercore.governed_runner as governed_runner_module
from cybercore.governed_plan import (
    AuthorizationGrant,
    CommandBinding,
    CommandPlan,
    CommandSpec,
    OperationClass,
)
from cybercore.governed_runner import GovernedRunnerError


def _grant(
    *,
    classes: frozenset[OperationClass],
    prefixes: tuple[tuple[str, ...], ...],
    bindings: tuple[CommandBinding, ...] = (),
) -> AuthorizationGrant:
    now = datetime.now(timezone.utc)
    return AuthorizationGrant(
        operation_id="WB-0040",
        canonical_target="cyberDJs/CyberCore",
        allowed_classes=classes,
        allowed_command_prefixes=prefixes,
        issuer="test-authorizer",
        issued_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(minutes=5),
        nonce="security-repair",
        allowed_command_bindings=bindings,
    )


def _plan(command: CommandSpec, grant: AuthorizationGrant) -> CommandPlan:
    return CommandPlan(
        operation_id="WB-0040",
        canonical_target="cyberDJs/CyberCore",
        commands=(command,),
        grant=grant,
    )


def test_rejects_nul_before_plan_execution() -> None:
    with pytest.raises(ValueError, match="NUL"):
        CommandSpec(
            argv=(sys.executable, "bad\0argument"),
            cwd=".",
            classification=OperationClass.READ_ONLY,
        )


def test_strict_mode_requires_command_class_binding_for_multi_class_grant(
    tmp_path: Path,
) -> None:
    grant = _grant(
        classes=frozenset({OperationClass.READ_ONLY, OperationClass.FILE_WRITE}),
        prefixes=((sys.executable,),),
    )
    command = CommandSpec(
        argv=(sys.executable, "--version"),
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )

    with pytest.raises(GovernedRunnerError, match="explicit command/class bindings"):
        governed_runner_module._prepare_plan(_plan(command, grant), root=tmp_path, strict=True)


def test_exact_binding_prevents_operation_class_relabel(tmp_path: Path) -> None:
    argv = (sys.executable, "-c", "print('ok')")
    binding = CommandBinding(OperationClass.FILE_WRITE, argv, exact=True)
    grant = _grant(
        classes=frozenset({OperationClass.READ_ONLY, OperationClass.FILE_WRITE}),
        prefixes=(argv,),
        bindings=(binding,),
    )
    relabeled = CommandSpec(
        argv=argv,
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )

    with pytest.raises(GovernedRunnerError, match="pair"):
        governed_runner_module._prepare_plan(_plan(relabeled, grant), root=tmp_path, strict=True)


def test_python_script_is_bound_to_exact_authorized_digest(tmp_path: Path) -> None:
    script = tmp_path / "approved.py"
    script.write_text("print('approved')\n", encoding="utf-8")
    digest = hashlib.sha256(script.read_bytes()).hexdigest()
    argv = (sys.executable, str(script))
    binding = CommandBinding(OperationClass.COMPUTE, argv, exact=True)
    grant = _grant(
        classes=frozenset({OperationClass.COMPUTE}),
        prefixes=(argv,),
        bindings=(binding,),
    )
    command = CommandSpec(
        argv=argv,
        cwd=".",
        classification=OperationClass.COMPUTE,
        code_sha256=digest,
    )
    plan = _plan(command, grant)
    prepared = governed_runner_module._prepare_plan(plan, root=tmp_path, strict=True)[0]

    script.write_text("print('replaced')\n", encoding="utf-8")

    with pytest.raises(GovernedRunnerError, match="digest|code input"):
        governed_runner_module._revalidate_prepared_command(
            plan, prepared, root=tmp_path, strict=True
        )


def test_service_wrapper_clears_environment_and_seals_memfds() -> None:
    source = governed_runner_module._STABLE_EXEC_WRAPPER
    compile(source, "<stable-wrapper>", "exec")
    assert "os.environ.clear()" in source
    assert "F_ADD_SEALS" in source
    assert "F_GET_SEALS" in source
    assert "F_SEAL_WRITE" in source
    assert "sealed memfd content verification failed" in source


def test_nonce_directory_creation_fsyncs_each_new_parent_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fsynced: list[Path] = []
    monkeypatch.setattr(
        governed_runner_module,
        "_fsync_directory",
        lambda path: fsynced.append(Path(path)),
    )
    state_dir = tmp_path / "a" / "b" / "c"

    governed_runner_module._ensure_nonce_state_dir(state_dir, persist_parent_chain=True)

    assert state_dir.is_dir()
    assert fsynced == [tmp_path, tmp_path / "a", tmp_path / "a" / "b"]


def test_systemd_spawn_hardens_service_and_wrapper_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        governed_runner_module.shutil,
        "which",
        lambda *_args, **_kwargs: "/usr/bin/true",
    )
    captured: dict[str, object] = {}

    class _FakeProcess:
        pid = 111

    def fake_popen(argv: list[str], **kwargs: object) -> _FakeProcess:
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return _FakeProcess()

    monkeypatch.setattr(governed_runner_module.subprocess, "Popen", fake_popen)
    containment = governed_runner_module._SystemdContainment()
    command = CommandSpec(
        argv=(sys.executable, "--version"),
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )
    grant = _grant(
        classes=frozenset({OperationClass.READ_ONLY}),
        prefixes=((sys.executable, "--version"),),
    )
    prepared = governed_runner_module._prepare_plan(_plan(command, grant), root=tmp_path)[0]
    env = governed_runner_module._bounded_environment(include_user_bus=False)

    containment.spawn(
        prepared,
        env=env,
        timeout_seconds=5.0,
        grant_expires_at=grant.expires_at,
    )

    argv = captured["argv"]
    kwargs = captured["kwargs"]
    assert isinstance(argv, list)
    assert isinstance(kwargs, dict)
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert "--setenv=PYTHONPATH=" in argv
    assert "--setenv=PYTHONNOUSERSITE=1" in argv
    assert "--property=ProtectSystem=strict" in argv
    assert "--property=ProtectHome=read-only" in argv
    assert "--property=RestrictAddressFamilies=AF_INET AF_INET6" in argv
    assert "--property=UnsetEnvironment=LD_PRELOAD LD_AUDIT LD_LIBRARY_PATH" in argv
    assert f"--property=ReadOnlyPaths={tmp_path}" in argv


def test_strict_mode_rejects_absolute_python_impostor_outside_trusted_path(
    tmp_path: Path,
) -> None:
    fake_python = tmp_path / "python3.99"
    fake_python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake_python.chmod(0o755)
    argv = (str(fake_python), "--version")
    grant = _grant(
        classes=frozenset({OperationClass.READ_ONLY}),
        prefixes=(argv,),
    )
    command = CommandSpec(
        argv=argv,
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )

    with pytest.raises(GovernedRunnerError, match="trusted runtime identities"):
        governed_runner_module._prepare_plan(_plan(command, grant), root=tmp_path, strict=True)


def test_systemd_termination_never_kills_only_client_when_unit_stop_unconfirmed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        governed_runner_module.shutil,
        "which",
        lambda *_args, **_kwargs: "/usr/bin/true",
    )

    def timeout_control(*_args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired("systemctl", kwargs["timeout"])

    monkeypatch.setattr(governed_runner_module.subprocess, "run", timeout_control)

    class _FakeProcess:
        pid = 222
        returncode = None
        killed_client = False

        def poll(self) -> None:
            return None

        def wait(self, timeout: float | None = None) -> int:
            raise subprocess.TimeoutExpired("systemd-run", timeout or 0)

        def kill(self) -> None:
            self.killed_client = True

    process = _FakeProcess()
    containment = governed_runner_module._SystemdContainment()
    containment._units[process.pid] = "test-unit"
    containment._runtime_deadlines[process.pid] = time.monotonic() + 0.01

    with pytest.raises(GovernedRunnerError, match="stop could not be confirmed"):
        containment.terminate(process, deadline=time.monotonic() + 0.005)

    assert process.killed_client is False
