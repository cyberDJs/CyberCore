from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cybercore.execution.models import ExecutionReceipt, ExecutionStatus, GovernedAction
from cybercore.execution.policy import NEXTCLOUD_R1_TARGET, VIKUNJA_TARGET, evaluate_action
from cybercore.execution.server.operations import resolve_operation
from cybercore.execution.server.protocol import (
    PROTOCOL_VERSION,
    RequestValidationError,
    ServerRequest,
)
from cybercore.mcp.nextcloud_r1_tool import build_nextcloud_r1_handler
from cybercore.execution.nextcloud_r1_transfer import (
    ARCHIVE_NAME,
    EXPECTED_SIZE_BYTES,
    SOURCE_ARCHIVE,
    SOURCE_HOST,
    _sftp_argv,
    _sftp_batch,
)
import pytest


def _action(operation: str) -> GovernedAction:
    return GovernedAction(
        operation_id="ISSUE-113-R1",
        operation=operation,
        target_id=NEXTCLOUD_R1_TARGET.id,
        plan_id="GH-113",
        plan_revision="1",
        authorization_reference="APPROVE-ISSUE-113",
        arguments={},
    )


def test_policy_binds_nextcloud_operations_to_only_cyberskills_target() -> None:
    decision = evaluate_action(_action("nextcloud.r1.offhost.transfer"), NEXTCLOUD_R1_TARGET)
    assert decision.allowed is True
    assert decision.mutating is True

    assert evaluate_action(_action("nextcloud.r1.offhost.verify"), NEXTCLOUD_R1_TARGET).allowed
    assert not evaluate_action(_action("nextcloud.r1.offhost.transfer"), VIKUNJA_TARGET).allowed
    inventory = _action("system.inventory")
    assert not evaluate_action(inventory, NEXTCLOUD_R1_TARGET).allowed


def test_server_protocol_binds_request_to_configured_backup_target() -> None:
    value = {
        "version": PROTOCOL_VERSION,
        "operation_id": "ISSUE-113-R1",
        "operation": "nextcloud.r1.offhost.status",
        "target_id": "cyberskills-vps",
        "plan_id": "GH-113",
        "plan_revision": "1",
        "authorization_reference": "APPROVE-ISSUE-113",
        "arguments": {},
    }
    request = ServerRequest.from_mapping(value, expected_target_id="cyberskills-vps")
    assert request.target_id == "cyberskills-vps"
    assert resolve_operation(request).argv[-1] == "cybercore-nextcloud-r1-transfer.service"

    with pytest.raises(RequestValidationError):
        ServerRequest.from_mapping(value, expected_target_id="tasks.cyberdjs.org")


def test_server_operation_rejects_nextcloud_action_on_tasks_target() -> None:
    request = ServerRequest.from_mapping(
        {
            "version": PROTOCOL_VERSION,
            "operation_id": "ISSUE-113-R1",
            "operation": "nextcloud.r1.offhost.status",
            "target_id": "tasks.cyberdjs.org",
            "plan_id": "GH-113",
            "plan_revision": "1",
            "authorization_reference": "APPROVE-ISSUE-113",
            "arguments": {},
        }
    )
    with pytest.raises(RequestValidationError, match="not allowed"):
        resolve_operation(request)


def test_mcp_handler_has_no_host_path_or_command_arguments_and_redacts_raw_approval() -> None:
    observed: dict[str, object] = {}

    def fake_executor(action, target, *, authorization_verifier=None):
        observed["action"] = action
        observed["target"] = target
        return ExecutionReceipt(
            operation_id=action.operation_id,
            operation=action.operation,
            target_id=action.target_id,
            plan_id=action.plan_id,
            plan_revision=action.plan_revision,
            authorization_reference_sha256=hashlib.sha256(
                action.authorization_reference.encode()
            ).hexdigest(),
            transport_argv=("ssh", "-s", "cybercore-exec"),
            started_at="2026-11-12T00:00:00Z",
            completed_at="2026-11-12T00:00:01Z",
            exit_code=0,
            stdout_sha256="1" * 64,
            stderr_sha256="2" * 64,
            status=ExecutionStatus.EXECUTED,
            mutation_possible=True,
            result=None,
        )

    handler = build_nextcloud_r1_handler(executor=fake_executor)
    result = handler(
        {
            "action": "transfer",
            "operation_id": "ISSUE-113-R1",
            "plan_id": "GH-113",
            "plan_revision": "1",
            "authorization_reference": "APPROVE-ISSUE-113",
        }
    )

    action = observed["action"]
    assert isinstance(action, GovernedAction)
    assert action.arguments == {}
    assert action.target_id == "cyberskills-vps"
    assert observed["target"] == NEXTCLOUD_R1_TARGET
    assert "APPROVE-ISSUE-113" not in json.dumps(result)


def test_transfer_uses_fixed_sftp_subsystem_and_disables_forwarding() -> None:
    argv = _sftp_argv()
    rendered = " ".join(argv)
    batch = _sftp_batch().decode()

    assert argv[0] == "/usr/bin/sftp"
    assert "-b" in argv
    assert SOURCE_HOST in rendered
    assert SOURCE_ARCHIVE in batch
    assert ARCHIVE_NAME in batch
    assert str(EXPECTED_SIZE_BYTES) not in rendered + batch
    assert "StrictHostKeyChecking=yes" in rendered
    assert "ClearAllForwardings=yes" in rendered
    assert "ForwardAgent=no" in rendered
    assert "PasswordAuthentication=no" in rendered
    assert "bash" not in rendered
    assert "sh -c" not in rendered
    assert "|" not in batch
    assert ";" not in batch


def test_deploy_candidate_is_static_sandboxed_and_secret_free() -> None:
    root = Path(__file__).resolve().parents[1]
    deploy = root / "deploy/cybercore-exec-nextcloud-r1"
    unit = (deploy / "cybercore-nextcloud-r1-transfer.service").read_text()
    policy = (deploy / "cybercore-exec.policy").read_text()
    sshd = (deploy / "cybercore-exec.subsystem.conf").read_text()
    readme = (deploy / "README.md").read_text()

    assert "IPAddressAllow=162.250.126.107" in unit
    assert "NoNewPrivileges=yes" in unit
    assert "ProtectSystem=strict" in unit
    assert 'unit === "cybercore-nextcloud-r1-transfer.service"' in policy
    assert "cyberskills-vps" in sshd
    assert "AllowAgentForwarding no" in sshd
    assert "private key" in readme.lower()
    assert "not contain or create" in readme.lower()
    for text in (unit, policy, sshd):
        assert "bash -c" not in text
        assert "sh -c" not in text
        assert "NOPASSWD" not in text
