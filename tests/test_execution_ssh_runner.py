import hashlib
import json
import subprocess

import pytest

from cybercore.execution.authorization import ExecutionAuthorizationCheck
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


class AllowAuthorizationVerifier:
    def verify(self, **kwargs: str) -> ExecutionAuthorizationCheck:
        return ExecutionAuthorizationCheck(True, "test authorization accepted")


def _action(operation: str = "vikunja.health.verify") -> GovernedAction:
    return GovernedAction(
        operation_id="A6-OPERATIONS",
        operation=operation,
        target_id="tasks.cyberdjs.org",
        plan_id="A6",
        plan_revision="1",
        authorization_reference="APPROVE-A6-OPERATIONS",
    )


def _inventory_result() -> dict[str, object]:
    return {
        "schema_version": 1,
        "host": {
            "hostname": "tasks",
            "cpu_logical": 2,
            "load_1m": 0.1,
            "load_5m": 0.2,
            "load_15m": 0.3,
        },
        "memory": {
            "total_bytes": 4_000_000_000,
            "available_bytes": 2_000_000_000,
            "swap_total_bytes": 2_000_000_000,
            "swap_free_bytes": 2_000_000_000,
        },
        "root_filesystem": {
            "total_bytes": 80_000_000_000,
            "used_bytes": 10_000_000_000,
            "free_bytes": 70_000_000_000,
        },
        "docker": {
            "cli_present": True,
            "access_status": "denied_or_unreachable",
            "server_version": None,
            "containers": [],
            "storage": [],
        },
    }


def _server_inventory_receipt(action: GovernedAction) -> bytes:
    result = _inventory_result()
    payload = {
        "operation_id": action.operation_id,
        "operation": action.operation,
        "target_id": action.target_id,
        "plan_id": action.plan_id,
        "plan_revision": action.plan_revision,
        "authorization_reference_sha256": hashlib.sha256(
            action.authorization_reference.encode("utf-8")
        ).hexdigest(),
        "started_at": "2026-09-19T00:00:00Z",
        "completed_at": "2026-09-19T00:00:01Z",
        "exit_code": 0,
        "stdout_sha256": "1" * 64,
        "stderr_sha256": "2" * 64,
        "status": "EXECUTED",
        "mutation_possible": False,
        "result": result,
        "secret_values_recorded": False,
    }
    return (json.dumps(payload) + "\n").encode()


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


def test_system_inventory_promotes_only_validated_server_result() -> None:
    action = _action("system.inventory")

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=_server_inventory_receipt(action),
            stderr=b"",
        )

    receipt = execute_action(action, VIKUNJA_TARGET, run=fake_run)
    assert receipt.status is ExecutionStatus.EXECUTED
    assert receipt.mutation_possible is False
    assert receipt.result is not None
    assert receipt.result["schema_version"] == 1
    assert receipt.result["host"]["cpu_logical"] == 2  # type: ignore[index]


def test_system_inventory_fails_closed_on_unbound_server_result() -> None:
    action = _action("system.inventory")

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        payload = json.loads(_server_inventory_receipt(action))
        payload["target_id"] = "wrong.example"
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=json.dumps(payload).encode(),
            stderr=b"",
        )

    receipt = execute_action(action, VIKUNJA_TARGET, run=fake_run)
    assert receipt.status is ExecutionStatus.FAILED
    assert receipt.exit_code == 65
    assert receipt.result is None


def test_system_inventory_rejects_mismatched_authorization_hash() -> None:
    action = _action("system.inventory")

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        payload = json.loads(_server_inventory_receipt(action))
        payload["authorization_reference_sha256"] = "0" * 64
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=json.dumps(payload).encode(),
            stderr=b"",
        )

    receipt = execute_action(action, VIKUNJA_TARGET, run=fake_run)
    assert receipt.status is ExecutionStatus.FAILED
    assert receipt.exit_code == 65
    assert receipt.result is None


def test_transport_timeout_exceeds_connection_plus_server_operation_budget() -> None:
    assert TRANSPORT_TIMEOUT_SECONDS > MAX_SERVER_OPERATION_TIMEOUT_SECONDS + 15


def test_mutating_operation_fails_closed_without_authorization_verifier() -> None:
    called = False

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        nonlocal called
        called = True
        return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")

    with pytest.raises(ExecutionBlockedError, match="no execution authorization verifier"):
        execute_action(_action("vikunja.backup.run"), VIKUNJA_TARGET, run=fake_run)
    assert called is False


def test_mutating_operation_marks_mutation_possible_when_authorized() -> None:
    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(argv, 0, stdout=b"ok", stderr=b"")

    receipt = execute_action(
        _action("vikunja.backup.run"),
        VIKUNJA_TARGET,
        authorization_verifier=AllowAuthorizationVerifier(),
        run=fake_run,
    )
    assert receipt.mutation_possible is True


def test_timeout_returns_failed_receipt_and_preserves_mutation_uncertainty() -> None:
    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(
            cmd=argv,
            timeout=TRANSPORT_TIMEOUT_SECONDS,
            output=b"partial-output",
            stderr=b"partial-error",
        )

    receipt = execute_action(
        _action("vikunja.backup.run"),
        VIKUNJA_TARGET,
        authorization_verifier=AllowAuthorizationVerifier(),
        run=fake_run,
    )

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
