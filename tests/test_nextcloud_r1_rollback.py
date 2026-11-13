from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from cybercore.execution.models import ExecutionReceipt, ExecutionStatus, GovernedAction
from cybercore.execution.nextcloud_r1_rollback import rollback_local
from cybercore.execution.policy import NEXTCLOUD_R1_TARGET, evaluate_action
from cybercore.execution.server.operations import resolve_operation
from cybercore.execution.server.protocol import PROTOCOL_VERSION, ServerRequest
from cybercore.mcp.nextcloud_r1_tool import build_nextcloud_r1_handler


def _request() -> ServerRequest:
    return ServerRequest.from_mapping(
        {
            "version": PROTOCOL_VERSION,
            "operation_id": "ISSUE-113-R1-ROLLBACK",
            "operation": "nextcloud.r1.offhost.rollback",
            "target_id": NEXTCLOUD_R1_TARGET.id,
            "plan_id": "GH-113",
            "plan_revision": "1",
            "authorization_reference": "APPROVE-ISSUE-113-ROLLBACK",
            "arguments": {},
        },
        expected_target_id=NEXTCLOUD_R1_TARGET.id,
    )


def test_rollback_operation_is_mutating_and_fixed_to_static_unit() -> None:
    request = _request()
    action = GovernedAction(
        operation_id=request.operation_id,
        operation=request.operation,
        target_id=request.target_id,
        plan_id=request.plan_id,
        plan_revision=request.plan_revision,
        authorization_reference=request.authorization_reference,
        arguments={},
    )
    decision = evaluate_action(action, NEXTCLOUD_R1_TARGET)
    assert decision.allowed is True
    assert decision.mutating is True
    assert resolve_operation(request).argv == (
        "/usr/bin/systemctl",
        "start",
        "cybercore-nextcloud-r1-rollback.service",
    )


def test_mcp_rollback_action_maps_to_only_fixed_operation() -> None:
    observed = {}

    def fake_executor(action, target, *, authorization_verifier=None):
        observed["operation"] = action.operation
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
    handler(
        {
            "action": "rollback",
            "operation_id": "ISSUE-113-R1-ROLLBACK",
            "plan_id": "GH-113",
            "plan_revision": "1",
            "authorization_reference": "APPROVE-ISSUE-113-ROLLBACK",
        }
    )
    assert observed == {
        "operation": "nextcloud.r1.offhost.rollback",
        "target": NEXTCLOUD_R1_TARGET,
    }


def _prepare_private_tree(tmp_path: Path, monkeypatch):
    import cybercore.execution.nextcloud_r1_rollback as rollback

    credentials = tmp_path / "credentials"
    state = tmp_path / "state"
    backups = tmp_path / "backups"
    for directory in (credentials, state, backups):
        directory.mkdir(mode=0o700)

    private_key = credentials / "source_ed25519"
    public_key = credentials / "source_ed25519.pub"
    known_hosts = credentials / "known_hosts"
    source_hash = credentials / "source_archive.sha256"
    partial = backups / "archive.tar.gz.partial"
    final = backups / "archive.tar.gz"
    receipt = state / "rollback-receipt.json"
    transfer_receipt = state / "transfer-receipt.json"

    monkeypatch.setattr(rollback, "CREDENTIAL_ROOT", credentials)
    monkeypatch.setattr(rollback, "STATE_ROOT", state)
    monkeypatch.setattr(rollback, "BACKUP_ROOT", backups)
    monkeypatch.setattr(rollback, "PRIVATE_KEY", private_key)
    monkeypatch.setattr(rollback, "PUBLIC_KEY", public_key)
    monkeypatch.setattr(rollback, "KNOWN_HOSTS", known_hosts)
    monkeypatch.setattr(rollback, "SOURCE_SHA256", source_hash)
    monkeypatch.setattr(rollback, "PARTIAL_ARCHIVE", partial)
    monkeypatch.setattr(rollback, "FINAL_ARCHIVE", final)
    monkeypatch.setattr(rollback, "ROLLBACK_RECEIPT", receipt)
    monkeypatch.setattr(rollback, "TRANSFER_RECEIPT", transfer_receipt)
    return (
        rollback,
        private_key,
        public_key,
        known_hosts,
        source_hash,
        partial,
        final,
        receipt,
        transfer_receipt,
    )


def test_local_rollback_removes_only_local_artifacts_and_preserves_final(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (
        _rollback,
        private_key,
        public_key,
        known_hosts,
        source_hash,
        partial,
        final,
        receipt,
        transfer_receipt,
    ) = _prepare_private_tree(tmp_path, monkeypatch)

    for path in (
        private_key,
        public_key,
        known_hosts,
        source_hash,
        partial,
        final,
        transfer_receipt,
    ):
        path.write_bytes(b"evidence")
        path.chmod(0o600)

    result = rollback_local()

    assert result["status"] == "LOCAL_CONTAINMENT_COMPLETE_REMOTE_REVOKE_REQUIRED"
    assert result["remote_authorized_key_cleanup_required"] is True
    assert result["final_archive_preserved"] is True
    assert final.read_bytes() == b"evidence"
    assert not partial.exists()
    assert not private_key.exists()
    assert not public_key.exists()
    assert not known_hosts.exists()
    assert not source_hash.exists()
    assert receipt.is_file()
    assert transfer_receipt.read_bytes() == b"evidence"
    assert result["transfer_receipt_preserved"] is True
    assert result["secret_values_recorded"] is False


def test_local_rollback_rejects_symlink_before_mutation(tmp_path: Path, monkeypatch) -> None:
    (
        _rollback,
        _private_key,
        _public_key,
        _known_hosts,
        _source_hash,
        partial,
        _final,
        _receipt,
        _transfer_receipt,
    ) = _prepare_private_tree(tmp_path, monkeypatch)

    victim = tmp_path / "victim"
    victim.write_bytes(b"keep")
    partial.symlink_to(victim)

    with pytest.raises(RuntimeError, match="not a regular file"):
        rollback_local()

    assert victim.read_bytes() == b"keep"


def test_rollback_unit_is_network_denied_and_preserves_final_archive_by_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    deploy = root / "deploy/cybercore-exec-nextcloud-r1"
    unit = (deploy / "cybercore-nextcloud-r1-rollback.service").read_text()
    helper = (root / "src/cybercore/execution/nextcloud_r1_rollback.py").read_text()
    policy = (deploy / "cybercore-exec.policy").read_text()

    assert "Conflicts=cybercore-nextcloud-r1-transfer.service" in unit
    assert "IPAddressDeny=any" in unit
    assert "IPAddressAllow=" not in unit
    assert "FINAL_ARCHIVE" in helper
    assert "_unlink_if_present(FINAL_ARCHIVE" not in helper
    assert 'unit === "cybercore-nextcloud-r1-rollback.service"' in policy
