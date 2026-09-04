from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

import pytest

import cybercore.governed_runner as governed_runner_module
from cybercore.governed_plan import (
    AuthorizationGrant,
    CommandPlan,
    CommandSpec,
    OperationClass,
)
from cybercore.governed_runner import GovernedRunner, GovernedRunnerError


class _DirectTestContainment:
    """Test-only containment double; production uses the fail-closed cgroup backend."""

    def spawn(
        self,
        argv: tuple[str, ...],
        *,
        cwd: Path,
        env: dict[str, str],
        timeout_seconds: float,
    ) -> subprocess.Popen[bytes]:
        del timeout_seconds
        return subprocess.Popen(
            list(argv),
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            shell=False,
        )

    def terminate(self, process: subprocess.Popen[bytes], *, deadline: float) -> None:
        del deadline
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        elif process.poll() is None:
            process.kill()
        if process.poll() is None:
            process.wait()


def _runner(root: Path) -> GovernedRunner:
    return GovernedRunner(
        root,
        containment=_DirectTestContainment(),
        nonce_state_dir=root / ".nonce-state",
    )


def _grant(
    *,
    operation_id: str = "WB-0040",
    target: str = "cyberDJs/CyberCore",
    allowed_classes: frozenset[OperationClass] | None = None,
    prefixes: tuple[tuple[str, ...], ...] | None = None,
    expires_in: float = 300.0,
) -> AuthorizationGrant:
    now = datetime.now(timezone.utc)
    return AuthorizationGrant(
        operation_id=operation_id,
        canonical_target=target,
        allowed_classes=allowed_classes or frozenset({OperationClass.READ_ONLY}),
        allowed_command_prefixes=prefixes or ((sys.executable, "--version"),),
        issuer="test-authorizer",
        issued_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(seconds=expires_in),
        nonce="test-nonce",
    )


def _plan(
    root: Path,
    command: CommandSpec,
    *,
    grant: AuthorizationGrant | None = None,
    operation_id: str = "WB-0040",
    target: str = "cyberDJs/CyberCore",
) -> CommandPlan:
    del root
    return CommandPlan(
        operation_id=operation_id,
        canonical_target=target,
        commands=(command,),
        grant=grant or _grant(),
    )


def test_executes_allowlisted_command_and_emits_unverified_receipt(tmp_path: Path) -> None:
    command = CommandSpec(
        argv=(sys.executable, "--version"),
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )

    receipt = _runner(tmp_path).execute(_plan(tmp_path, command))

    assert receipt.status == "IMPLEMENTED"
    assert receipt.verified is False
    assert len(receipt.commands) == 1
    result = receipt.commands[0]
    assert result.exit_code == 0
    assert result.classification is OperationClass.READ_ONLY
    assert Path(result.argv[0]).is_absolute()
    assert len(result.stdout_sha256) == 64
    assert len(result.stderr_sha256) == 64


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_timeout(timeout: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        CommandSpec(
            argv=(sys.executable, "--version"),
            cwd=".",
            classification=OperationClass.READ_ONLY,
            timeout_seconds=timeout,
        )


def test_rejects_shell_wrapper_even_when_prefix_is_allowlisted(tmp_path: Path) -> None:
    command = CommandSpec(
        argv=("bash", "script.sh"),
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )
    grant = _grant(prefixes=(("bash",),))

    with pytest.raises(GovernedRunnerError, match="denied by policy"):
        GovernedRunner(tmp_path).execute(_plan(tmp_path, command, grant=grant))


def test_positive_policy_rejects_non_runtime_executable(tmp_path: Path) -> None:
    echo = str(Path("/bin/echo").resolve())
    command = CommandSpec(
        argv=(echo, "hello"),
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )
    grant = _grant(prefixes=((echo,),))

    with pytest.raises(GovernedRunnerError, match="positive policy"):
        _runner(tmp_path).execute(_plan(tmp_path, command, grant=grant))


def test_rejects_shell_metacharacters(tmp_path: Path) -> None:
    command = CommandSpec(
        argv=(sys.executable, "--version", ";"),
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )
    grant = _grant(prefixes=((sys.executable, "--version"),))

    with pytest.raises(GovernedRunnerError, match="metacharacters"):
        _runner(tmp_path).execute(_plan(tmp_path, command, grant=grant))


def test_rejects_command_outside_authorized_prefixes(tmp_path: Path) -> None:
    command = CommandSpec(
        argv=(sys.executable, "-V"),
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )

    with pytest.raises(GovernedRunnerError, match="outside authorized prefixes"):
        _runner(tmp_path).execute(_plan(tmp_path, command))


def test_rejects_operation_class_not_present_in_grant(tmp_path: Path) -> None:
    command = CommandSpec(
        argv=(sys.executable, "--version"),
        cwd=".",
        classification=OperationClass.FILE_WRITE,
    )

    with pytest.raises(GovernedRunnerError, match="operation class is not authorized"):
        _runner(tmp_path).execute(_plan(tmp_path, command))


def test_rejects_cwd_escape(tmp_path: Path) -> None:
    command = CommandSpec(
        argv=(sys.executable, "--version"),
        cwd=str(tmp_path.parent),
        classification=OperationClass.READ_ONLY,
    )

    with pytest.raises(GovernedRunnerError, match="escapes allowed root"):
        _runner(tmp_path).execute(_plan(tmp_path, command))


def test_rejects_grant_binding_mismatch(tmp_path: Path) -> None:
    command = CommandSpec(
        argv=(sys.executable, "--version"),
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )
    grant = _grant(operation_id="OTHER")

    with pytest.raises(GovernedRunnerError, match="operation_id"):
        _runner(tmp_path).execute(_plan(tmp_path, command, grant=grant))


def test_prevalidates_entire_plan_before_first_command_runs(tmp_path: Path) -> None:
    marker = tmp_path / "should-not-exist"
    writer = tmp_path / "writer.py"
    writer.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran', encoding='utf-8')\n",
        encoding="utf-8",
    )
    grant = _grant(
        allowed_classes=frozenset({OperationClass.FILE_WRITE, OperationClass.READ_ONLY}),
        prefixes=((sys.executable,),),
    )
    plan = CommandPlan(
        operation_id="WB-0040",
        canonical_target="cyberDJs/CyberCore",
        commands=(
            CommandSpec(
                argv=(sys.executable, str(writer)),
                cwd=".",
                classification=OperationClass.FILE_WRITE,
            ),
            CommandSpec(
                argv=(sys.executable, "--version", ";"),
                cwd=".",
                classification=OperationClass.READ_ONLY,
            ),
        ),
        grant=grant,
    )

    with pytest.raises(GovernedRunnerError, match="metacharacters"):
        _runner(tmp_path).execute(plan)

    assert not marker.exists()


def test_revalidates_grant_before_each_spawn(tmp_path: Path) -> None:
    sleeper = tmp_path / "sleep.py"
    sleeper.write_text("import time\ntime.sleep(0.2)\n", encoding="utf-8")
    grant = _grant(
        allowed_classes=frozenset({OperationClass.COMPUTE, OperationClass.READ_ONLY}),
        prefixes=((sys.executable,),),
        expires_in=0.1,
    )
    plan = CommandPlan(
        operation_id="WB-0040",
        canonical_target="cyberDJs/CyberCore",
        commands=(
            CommandSpec(
                argv=(sys.executable, str(sleeper)),
                cwd=".",
                classification=OperationClass.COMPUTE,
            ),
            CommandSpec(
                argv=(sys.executable, "--version"),
                cwd=".",
                classification=OperationClass.READ_ONLY,
            ),
        ),
        grant=grant,
    )

    receipt = _runner(tmp_path).execute(plan)

    assert receipt.status == "FAILED"
    assert len(receipt.commands) == 2
    assert receipt.commands[0].exit_code == 0
    assert receipt.commands[1].exit_code is None


def test_revalidates_cwd_before_each_spawn(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    mutator = tmp_path / "mutate-cwd.py"
    mutator.write_text(
        "import os\n"
        "from pathlib import Path\n"
        "import shutil\n"
        f"target = Path({str(target)!r})\n"
        "shutil.rmtree(target)\n"
        f"os.symlink({str(tmp_path.parent)!r}, target)\n",
        encoding="utf-8",
    )
    grant = _grant(
        allowed_classes=frozenset({OperationClass.FILE_WRITE, OperationClass.READ_ONLY}),
        prefixes=((sys.executable,),),
    )
    plan = CommandPlan(
        operation_id="WB-0040",
        canonical_target="cyberDJs/CyberCore",
        commands=(
            CommandSpec(
                argv=(sys.executable, str(mutator)),
                cwd=".",
                classification=OperationClass.FILE_WRITE,
            ),
            CommandSpec(
                argv=(sys.executable, "--version"),
                cwd="target",
                classification=OperationClass.READ_ONLY,
            ),
        ),
        grant=grant,
    )

    receipt = _runner(tmp_path).execute(plan)

    assert receipt.status == "FAILED"
    assert len(receipt.commands) == 2
    assert receipt.commands[0].exit_code == 0
    assert receipt.commands[1].exit_code is None


def test_detects_in_place_executable_replacement(tmp_path: Path) -> None:
    executable = tmp_path / "python3.99"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)
    mutator = tmp_path / "mutate-executable.py"
    mutator.write_text(
        "from pathlib import Path\n"
        f"path = Path({str(executable)!r})\n"
        "path.write_text('#!/bin/sh\\nexit 99\\n', encoding='utf-8')\n"
        "path.chmod(0o755)\n",
        encoding="utf-8",
    )
    grant = _grant(
        allowed_classes=frozenset({OperationClass.FILE_WRITE, OperationClass.READ_ONLY}),
        prefixes=((sys.executable,), (str(executable),)),
    )
    plan = CommandPlan(
        operation_id="WB-0040",
        canonical_target="cyberDJs/CyberCore",
        commands=(
            CommandSpec(
                argv=(sys.executable, str(mutator)),
                cwd=".",
                classification=OperationClass.FILE_WRITE,
            ),
            CommandSpec(
                argv=(str(executable),),
                cwd=".",
                classification=OperationClass.READ_ONLY,
            ),
        ),
        grant=grant,
    )

    receipt = _runner(tmp_path).execute(plan)

    assert receipt.status == "FAILED"
    assert len(receipt.commands) == 2
    assert receipt.commands[0].exit_code == 0
    assert receipt.commands[1].exit_code is None


def test_consumes_mutating_authorization_nonce_atomically_across_runners(
    tmp_path: Path,
) -> None:
    sleeper = tmp_path / "nonce-sleeper.py"
    sleeper.write_text("import time\ntime.sleep(0.1)\n", encoding="utf-8")
    grant = _grant(
        allowed_classes=frozenset({OperationClass.FILE_WRITE}),
        prefixes=((sys.executable,),),
    )
    command = CommandSpec(
        argv=(sys.executable, str(sleeper)),
        cwd=".",
        classification=OperationClass.FILE_WRITE,
    )
    plan = _plan(tmp_path, command, grant=grant)
    nonce_state_dir = tmp_path / "shared-nonce-state"
    runners = (
        GovernedRunner(
            tmp_path,
            containment=_DirectTestContainment(),
            nonce_state_dir=nonce_state_dir,
        ),
        GovernedRunner(
            tmp_path,
            containment=_DirectTestContainment(),
            nonce_state_dir=nonce_state_dir,
        ),
    )
    barrier = threading.Barrier(2)
    outcomes: list[tuple[str, str]] = []
    outcomes_lock = threading.Lock()

    def execute(runner: GovernedRunner) -> None:
        barrier.wait()
        try:
            result = ("receipt", runner.execute(plan).status)
        except GovernedRunnerError as exc:
            result = ("error", str(exc))
        with outcomes_lock:
            outcomes.append(result)

    threads = [threading.Thread(target=execute, args=(runner,)) for runner in runners]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2.0)

    assert not any(thread.is_alive() for thread in threads)
    assert sorted(kind for kind, _detail in outcomes) == ["error", "receipt"]
    assert next(detail for kind, detail in outcomes if kind == "receipt") == "IMPLEMENTED"
    assert "nonce" in next(detail for kind, detail in outcomes if kind == "error")


def test_bare_executable_ignores_ambient_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_git = tmp_path / "git"
    fake_git.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
    fake_git.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    command = CommandSpec(
        argv=("git", "--version"),
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )
    grant = _grant(prefixes=(("git", "--version"),))

    receipt = _runner(tmp_path).execute(_plan(tmp_path, command, grant=grant))

    assert receipt.status == "IMPLEMENTED"
    assert receipt.commands[0].exit_code == 0
    assert Path(receipt.commands[0].argv[0]).resolve() != fake_git.resolve()


def test_timeout_terminates_descendant_processes(tmp_path: Path) -> None:
    marker = tmp_path / "descendant-survived"
    grandchild = tmp_path / "grandchild.py"
    grandchild.write_text(
        "from pathlib import Path\n"
        "import time\n"
        "time.sleep(0.5)\n"
        f"Path({str(marker)!r}).write_text('survived', encoding='utf-8')\n",
        encoding="utf-8",
    )
    parent = tmp_path / "parent.py"
    parent.write_text(
        "import subprocess\n"
        "import sys\n"
        "import time\n"
        f"subprocess.Popen([sys.executable, {str(grandchild)!r}])\n"
        "time.sleep(5)\n",
        encoding="utf-8",
    )
    command = CommandSpec(
        argv=(sys.executable, str(parent)),
        cwd=".",
        classification=OperationClass.COMPUTE,
        timeout_seconds=0.1,
    )
    grant = _grant(
        allowed_classes=frozenset({OperationClass.COMPUTE}),
        prefixes=((sys.executable,),),
    )

    receipt = _runner(tmp_path).execute(_plan(tmp_path, command, grant=grant))
    time.sleep(0.7)

    assert receipt.status == "FAILED"
    assert receipt.commands[0].timed_out is True
    assert not marker.exists()


def test_timeout_reserves_separate_containment_cleanup_budget(tmp_path: Path) -> None:
    sleeper = tmp_path / "cleanup-budget.py"
    sleeper.write_text("import time\ntime.sleep(5)\n", encoding="utf-8")

    class _RecordingContainment(_DirectTestContainment):
        def __init__(self) -> None:
            self.remaining_budgets: list[float] = []

        def terminate(self, process: subprocess.Popen[bytes], *, deadline: float) -> None:
            self.remaining_budgets.append(deadline - time.monotonic())
            super().terminate(process, deadline=deadline)

    containment = _RecordingContainment()
    command = CommandSpec(
        argv=(sys.executable, str(sleeper)),
        cwd=".",
        classification=OperationClass.COMPUTE,
        timeout_seconds=0.05,
    )
    grant = _grant(
        allowed_classes=frozenset({OperationClass.COMPUTE}),
        prefixes=((sys.executable,),),
    )

    receipt = GovernedRunner(
        tmp_path,
        containment=containment,
        nonce_state_dir=tmp_path / ".nonce-state",
    ).execute(_plan(tmp_path, command, grant=grant))

    assert receipt.status == "FAILED"
    assert containment.remaining_budgets
    assert max(containment.remaining_budgets) > 0.5


def test_timeout_remains_active_while_inherited_pipes_are_open(tmp_path: Path) -> None:
    grandchild = tmp_path / "pipe-holder.py"
    grandchild.write_text("import time\ntime.sleep(5)\n", encoding="utf-8")
    parent = tmp_path / "pipe-parent.py"
    parent.write_text(
        f"import subprocess\nimport sys\nsubprocess.Popen([sys.executable, {str(grandchild)!r}])\n",
        encoding="utf-8",
    )
    command = CommandSpec(
        argv=(sys.executable, str(parent)),
        cwd=".",
        classification=OperationClass.COMPUTE,
        timeout_seconds=0.2,
    )
    grant = _grant(
        allowed_classes=frozenset({OperationClass.COMPUTE}),
        prefixes=((sys.executable,),),
    )

    started = time.monotonic()
    receipt = _runner(tmp_path).execute(_plan(tmp_path, command, grant=grant))
    elapsed = time.monotonic() - started

    assert elapsed < 1.0
    assert receipt.status == "FAILED"
    assert receipt.commands[0].timed_out is True


def test_systemd_client_env_preserves_only_required_bus_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/run/user/1000/bus")
    monkeypatch.setenv("SECRET_SHOULD_NOT_LEAK", "nope")

    env = governed_runner_module._bounded_environment(include_user_bus=True)

    assert env["XDG_RUNTIME_DIR"] == "/run/user/1000"
    assert env["DBUS_SESSION_BUS_ADDRESS"] == "unix:path=/run/user/1000/bus"
    assert "SECRET_SHOULD_NOT_LEAK" not in env


def test_systemd_spawn_binds_validated_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        governed_runner_module.shutil, "which", lambda *_args, **_kwargs: "/usr/bin/true"
    )
    captured: dict[str, object] = {}

    class _FakeProcess:
        pid = 123

    def fake_popen(argv: list[str], **kwargs: object) -> _FakeProcess:
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return _FakeProcess()

    monkeypatch.setattr(governed_runner_module.subprocess, "Popen", fake_popen)
    containment = governed_runner_module._SystemdContainment()
    env = governed_runner_module._bounded_environment(include_user_bus=False)

    containment.spawn(
        (sys.executable, "--version"),
        cwd=tmp_path,
        env=env,
        timeout_seconds=5.0,
    )

    argv = captured["argv"]
    assert isinstance(argv, list)
    assert f"--working-directory={tmp_path}" in argv
    assert "--property=RuntimeMaxSec=5.0s" in argv


def test_systemctl_control_call_is_bounded_by_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        governed_runner_module.shutil, "which", lambda *_args, **_kwargs: "/usr/bin/true"
    )
    seen_timeouts: list[float] = []

    def fake_run(*_args: object, timeout: float, **_kwargs: object) -> None:
        seen_timeouts.append(timeout)
        raise subprocess.TimeoutExpired(cmd="systemctl", timeout=timeout)

    monkeypatch.setattr(governed_runner_module.subprocess, "run", fake_run)

    class _FakeProcess:
        pid = 321
        returncode: int | None = None

        def poll(self) -> int | None:
            return self.returncode

        def kill(self) -> None:
            self.returncode = -9

        def wait(self, timeout: float | None = None) -> int:
            del timeout
            self.returncode = -9
            return self.returncode

    process = _FakeProcess()
    containment = governed_runner_module._SystemdContainment()
    containment._units[process.pid] = "test-unit"
    deadline = time.monotonic() + 0.05

    containment.terminate(process, deadline=deadline)

    assert seen_timeouts
    assert all(0 < value <= 0.05 for value in seen_timeouts)


def test_rejects_missing_executable_during_prevalidation(tmp_path: Path) -> None:
    missing = "definitely-not-a-real-command-wb0040"
    command = CommandSpec(
        argv=(missing,),
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )
    grant = _grant(prefixes=((missing,),))

    with pytest.raises(GovernedRunnerError, match="positive policy"):
        _runner(tmp_path).execute(_plan(tmp_path, command, grant=grant))
