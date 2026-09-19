import json
import subprocess

import pytest

from cybercore.execution.models import ExecutionStatus, GovernedAction
from cybercore.execution.policy import VIKUNJA_TARGET
from cybercore.execution.server.operations import MAX_SERVER_OPERATION_TIMEOUT_SECONDS
from cybercore.execution.server.protocol import PROTOCOL_VERSION, ServerRequest
from cybercore.execution.ssh_runner import (
    TRANSPORT_TIMEOUT_SECONDS,
    ExecutionBlockedError,
    build_transport_argv,
    execute_action,
)


def _action(operation: str = "vikunja.health.verify") -> GovernedAction:
    return GovernedAction(
        operation_id="A6-OPERATIONS",
        operation=operation,
        target_id="tasks.cyberdjs.org",
        plan_id="A6",
        plan_revision="1",
        authorization_reference="APPROVE-A6-OPERATIONS",
    )


def test_transport_uses_ssh_subsystem_not_remote_shell() -> None:
    argv = build_transport_argv(VIKUNJA_TARGET)
    assert argv[0] == "ssh"
    assert "-s" in argv
    assert argv[-1] == "cybercore-exec"
    assert "bash" not in argv
    assert "sh" not in argv


def test_execute_uses_shell_false_and_server_compatible_structured_stdin() -> None:
    observed: dict[str, object] = {}

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        observed["argv"] = argv
        observed.update(kwargs)
        return subprocess.CompletedProcess(argv, 0, stdout=b"ok", stderr=b"")

    receipt = execute_action(_action(), VIKUNJA_TARGET, run=fake_run)
    assert observed["shell"] is False
    payload = json.loads(observed["input"])  # type: ignore[arg-type]
    parsed = ServerRequest.from_mapping(payload)
    assert parsed.version == PROTOCOL_VERSION
    assert parsed.operation == "vikunja.health.verify"
    assert parsed.target_id == "tasks.cyberdjs.org"
    assert observed["timeout"] == TRANSPORT_TIMEOUT_SECONDS
    assert receipt.exit_code == 0
    assert receipt.mutation_possible is False


def test_transport_timeout_exceeds_connection_plus_server_operation_budget() -> None:
    assert TRANSPORT_TIMEOUT_SECONDS > MAX_SERVER_OPERATION_TIMEOUT_SECONDS + 15


def test_mutating_operation_marks_mutation_possible() -> None:
    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(argv, 0, stdout=b"ok", stderr=b"")

    receipt = execute_action(_action("vikunja.backup.run"), VIKUNJA_TARGET, run=fake_run)
    assert receipt.mutation_possible is True


def test_timeout_returns_failed_receipt_and_preserves_mutation_uncertainty() -> None:
    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(
            cmd=argv,
            timeout=TRANSPORT_TIMEOUT_SECONDS,
            output=b"partial-output",
            stderr=b"partial-error",
        )

    receipt = execute_action(_action("vikunja.backup.run"), VIKUNJA_TARGET, run=fake_run)

    assert receipt.status is ExecutionStatus.FAILED
    assert receipt.exit_code == 124
    assert receipt.mutation_possible is True
    assert receipt.secret_values_recorded is False
    assert len(receipt.stdout_sha256) == 64
    assert len(receipt.stderr_sha256) == 64


def test_timeout_for_read_only_operation_is_not_marked_mutating() -> None:
    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(cmd=argv, timeout=TRANSPORT_TIMEOUT_SECONDS)

    receipt = execute_action(_action("vikunja.health.verify"), VIKUNJA_TARGET, run=fake_run)

    assert receipt.status is ExecutionStatus.FAILED
    assert receipt.exit_code == 124
    assert receipt.mutation_possible is False


def test_policy_blocks_before_ssh() -> None:
    called = False

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        nonlocal called
        called = True
        return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")

    action = GovernedAction(
        operation_id="A6-OPERATIONS",
        operation="shell.run",
        target_id="tasks.cyberdjs.org",
        plan_id="A6",
        plan_revision="1",
        authorization_reference="APPROVE-A6-OPERATIONS",
    )
    with pytest.raises(ExecutionBlockedError):
        execute_action(action, VIKUNJA_TARGET, run=fake_run)
    assert called is False
