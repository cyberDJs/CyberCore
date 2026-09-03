from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import time

import pytest

from cybercore.governed_plan import (
    AuthorizationGrant,
    CommandPlan,
    CommandSpec,
    OperationClass,
)
from cybercore.governed_runner import GovernedRunner, GovernedRunnerError


def _grant(
    *,
    operation_id: str = "WB-0040",
    target: str = "cyberDJs/CyberCore",
    allowed_classes: frozenset[OperationClass] | None = None,
    prefixes: tuple[tuple[str, ...], ...] | None = None,
) -> AuthorizationGrant:
    now = datetime.now(timezone.utc)
    return AuthorizationGrant(
        operation_id=operation_id,
        canonical_target=target,
        allowed_classes=allowed_classes or frozenset({OperationClass.READ_ONLY}),
        allowed_command_prefixes=prefixes or ((sys.executable, "--version"),),
        issuer="test-authorizer",
        issued_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(minutes=5),
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

    receipt = GovernedRunner(tmp_path).execute(_plan(tmp_path, command))

    assert receipt.status == "IMPLEMENTED"
    assert receipt.verified is False
    assert len(receipt.commands) == 1
    result = receipt.commands[0]
    assert result.exit_code == 0
    assert result.classification is OperationClass.READ_ONLY
    assert Path(result.argv[0]).is_absolute()
    assert len(result.stdout_sha256) == 64
    assert len(result.stderr_sha256) == 64


def test_rejects_shell_wrapper_even_when_prefix_is_allowlisted(tmp_path: Path) -> None:
    command = CommandSpec(
        argv=("bash", "script.sh"),
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )
    grant = _grant(prefixes=(("bash",),))

    with pytest.raises(GovernedRunnerError, match="denied by policy"):
        GovernedRunner(tmp_path).execute(_plan(tmp_path, command, grant=grant))


def test_rejects_shell_metacharacters(tmp_path: Path) -> None:
    command = CommandSpec(
        argv=(sys.executable, "--version", ";"),
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )
    grant = _grant(prefixes=((sys.executable, "--version"),))

    with pytest.raises(GovernedRunnerError, match="metacharacters"):
        GovernedRunner(tmp_path).execute(_plan(tmp_path, command, grant=grant))


def test_rejects_command_outside_authorized_prefixes(tmp_path: Path) -> None:
    command = CommandSpec(
        argv=(sys.executable, "-V"),
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )

    with pytest.raises(GovernedRunnerError, match="outside authorized prefixes"):
        GovernedRunner(tmp_path).execute(_plan(tmp_path, command))


def test_rejects_operation_class_not_present_in_grant(tmp_path: Path) -> None:
    command = CommandSpec(
        argv=(sys.executable, "--version"),
        cwd=".",
        classification=OperationClass.FILE_WRITE,
    )

    with pytest.raises(GovernedRunnerError, match="operation class is not authorized"):
        GovernedRunner(tmp_path).execute(_plan(tmp_path, command))


def test_rejects_cwd_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent
    command = CommandSpec(
        argv=(sys.executable, "--version"),
        cwd=str(outside),
        classification=OperationClass.READ_ONLY,
    )

    with pytest.raises(GovernedRunnerError, match="escapes allowed root"):
        GovernedRunner(tmp_path).execute(_plan(tmp_path, command))


def test_rejects_grant_binding_mismatch(tmp_path: Path) -> None:
    command = CommandSpec(
        argv=(sys.executable, "--version"),
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )
    grant = _grant(operation_id="OTHER")

    with pytest.raises(GovernedRunnerError, match="operation_id"):
        GovernedRunner(tmp_path).execute(_plan(tmp_path, command, grant=grant))


def test_prevalidates_entire_plan_before_first_command_runs(tmp_path: Path) -> None:
    marker = tmp_path / "should-not-exist"
    writer = tmp_path / "writer.py"
    writer.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('ran', encoding='utf-8')\n",
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
        GovernedRunner(tmp_path).execute(plan)

    assert not marker.exists()


def test_bare_executable_ignores_ambient_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    receipt = GovernedRunner(tmp_path).execute(_plan(tmp_path, command, grant=grant))

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

    receipt = GovernedRunner(tmp_path).execute(_plan(tmp_path, command, grant=grant))
    time.sleep(0.7)

    assert receipt.status == "FAILED"
    assert receipt.commands[0].timed_out is True
    assert not marker.exists()


def test_output_limit_stops_noisy_process(tmp_path: Path) -> None:
    marker = tmp_path / "noisy-process-finished"
    noisy = tmp_path / "noisy.py"
    noisy.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "import time\n"
        "chunk = 'x' * 4096\n"
        "for _ in range(400):\n"
        "    sys.stdout.write(chunk)\n"
        "    sys.stdout.flush()\n"
        "    time.sleep(0.003)\n"
        f"Path({str(marker)!r}).write_text('finished', encoding='utf-8')\n",
        encoding="utf-8",
    )
    command = CommandSpec(
        argv=(sys.executable, str(noisy)),
        cwd=".",
        classification=OperationClass.COMPUTE,
        timeout_seconds=5,
    )
    grant = _grant(
        allowed_classes=frozenset({OperationClass.COMPUTE}),
        prefixes=((sys.executable,),),
    )

    receipt = GovernedRunner(tmp_path).execute(_plan(tmp_path, command, grant=grant))

    assert receipt.status == "FAILED"
    assert receipt.commands[0].timed_out is False
    assert not marker.exists()


def test_rejects_missing_executable_during_prevalidation(tmp_path: Path) -> None:
    missing = "definitely-not-a-real-command-wb0040"
    command = CommandSpec(
        argv=(missing,),
        cwd=".",
        classification=OperationClass.READ_ONLY,
    )
    grant = _grant(prefixes=((missing,),))

    with pytest.raises(GovernedRunnerError, match="trusted path"):
        GovernedRunner(tmp_path).execute(_plan(tmp_path, command, grant=grant))
