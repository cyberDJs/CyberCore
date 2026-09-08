from __future__ import annotations

from datetime import datetime, timedelta, timezone
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


@pytest.mark.parametrize("python_args", [("-c", "print('ok')"), ("approved.py",)])
def test_strict_mode_rejects_python_launchers_until_descendants_are_constrained(
    tmp_path: Path, python_args: tuple[str, ...]
) -> None:
    script = tmp_path / "approved.py"
    script.write_text("print('approved')\n", encoding="utf-8")
    argv = (sys.executable, *python_args)
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
    )

    with pytest.raises(GovernedRunnerError, match="descendant executable graph"):
        governed_runner_module._prepare_plan(_plan(command, grant), root=tmp_path, strict=True)


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
    separator = argv.index("--")
    assert argv[separator + 1 : separator + 5] == ["/usr/bin/true", "-I", "-S", "-c"]


def test_symlink_loop_cwd_is_a_governed_failure(tmp_path: Path) -> None:
    loop = tmp_path / "loop"
    loop.symlink_to(loop)
    command = CommandSpec(
        argv=(sys.executable, "--version"),
        cwd="loop",
        classification=OperationClass.READ_ONLY,
    )
    grant = _grant(
        classes=frozenset({OperationClass.READ_ONLY}),
        prefixes=((sys.executable, "--version"),),
    )

    with pytest.raises(GovernedRunnerError, match="command cwd cannot be resolved"):
        governed_runner_module._prepare_plan(_plan(command, grant), root=tmp_path)


def test_symlink_loop_executable_is_a_governed_failure(tmp_path: Path) -> None:
    loop = tmp_path / "loop-exec"
    loop.symlink_to(loop)
    argv = (str(loop),)
    command = CommandSpec(
        argv=argv,
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )
    grant = _grant(classes=frozenset({OperationClass.READ_ONLY}), prefixes=(argv,))

    with pytest.raises(GovernedRunnerError, match="authorized executable cannot be resolved"):
        governed_runner_module._prepare_plan(_plan(command, grant), root=tmp_path)


def test_current_python_symlink_loop_is_a_governed_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loop = tmp_path / "current-python-loop"
    loop.symlink_to(loop)
    trusted_python = Path(sys.executable).resolve()
    monkeypatch.setattr(governed_runner_module.sys, "executable", str(loop))

    with pytest.raises(GovernedRunnerError, match="current Python executable cannot be resolved"):
        governed_runner_module._require_trusted_absolute_executable(str(trusted_python))


def test_trusted_path_symlink_loop_is_a_governed_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "approved-tool"
    candidate.write_text("#!/bin/sh\nexit 0\n")
    candidate.chmod(0o755)
    loop = tmp_path / "trusted-loop"
    loop.symlink_to(loop)

    def fake_which(name: str, mode: int = 0, path: str | None = None) -> str | None:
        del mode, path
        if name == "approved-tool":
            return str(loop)
        return None

    monkeypatch.setattr(governed_runner_module.shutil, "which", fake_which)

    with pytest.raises(GovernedRunnerError, match="trusted executable cannot be resolved"):
        governed_runner_module._require_trusted_absolute_executable(str(candidate))


def test_symlink_loop_code_input_is_a_governed_failure(tmp_path: Path) -> None:
    loop = tmp_path / "loop.py"
    loop.symlink_to(loop)

    with pytest.raises(GovernedRunnerError, match="authorized code input cannot be resolved"):
        governed_runner_module._resolve_input_path(tmp_path, tmp_path, "loop.py")


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


def test_strict_mode_rejects_python_through_non_python_symlink_alias(tmp_path: Path) -> None:
    alias = tmp_path / "approved-tool"
    alias.symlink_to(Path(sys.executable).resolve())
    argv = (
        str(alias),
        "-c",
        "__import__('subprocess').run(['/bin/echo', 'bypass'])",
    )
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
    )

    with pytest.raises(GovernedRunnerError, match="descendant executable graph"):
        governed_runner_module._prepare_plan(_plan(command, grant), root=tmp_path, strict=True)


def test_strict_mode_rejects_git_until_code_graph_is_content_bound(tmp_path: Path) -> None:
    argv = ("git", "status")
    grant = _grant(
        classes=frozenset({OperationClass.READ_ONLY}),
        prefixes=(argv,),
    )
    command = CommandSpec(
        argv=argv,
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )

    with pytest.raises(GovernedRunnerError, match="git is not approved for production"):
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
