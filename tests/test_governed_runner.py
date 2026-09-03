from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

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


def test_stops_after_first_failed_command(tmp_path: Path) -> None:
    missing = "definitely-not-a-real-command-wb0040"
    grant = _grant(prefixes=((missing,), (sys.executable, "--version")))
    plan = CommandPlan(
        operation_id="WB-0040",
        canonical_target="cyberDJs/CyberCore",
        commands=(
            CommandSpec(
                argv=(missing,),
                cwd=".",
                classification=OperationClass.READ_ONLY,
            ),
            CommandSpec(
                argv=(sys.executable, "--version"),
                cwd=".",
                classification=OperationClass.READ_ONLY,
            ),
        ),
        grant=grant,
    )

    receipt = GovernedRunner(tmp_path).execute(plan)

    assert receipt.status == "FAILED"
    assert receipt.verified is False
    assert len(receipt.commands) == 1
    assert receipt.commands[0].exit_code is None
    assert len(receipt.commands[0].stderr_sha256) == 64
