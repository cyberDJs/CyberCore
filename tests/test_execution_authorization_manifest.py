from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

import pytest

from cybercore.execution.authorization import FileBoundExecutionAuthorizationVerifier


FIXED_NOW = datetime(2026, 11, 12, 15, 0, 0, tzinfo=timezone.utc)
AUTHORIZATION_REFERENCE = "APPROVE-EXACT-R1-TRANSFER"


def _manifest() -> dict[str, object]:
    return {
        "schema_version": 1,
        "approval_id": "issue-113-r1-transfer",
        "operation_id": "ISSUE-113-R1",
        "operation": "nextcloud.r1.offhost.transfer",
        "target_id": "cyberskills-vps",
        "plan_id": "GH-113",
        "plan_revision": "1",
        "authorization_reference_sha256": hashlib.sha256(
            AUTHORIZATION_REFERENCE.encode("utf-8")
        ).hexdigest(),
        "issued_at": "2026-11-12T14:55:00Z",
        "expires_at": "2026-11-12T15:25:00Z",
    }


def _write_manifest(root: Path, payload: dict[str, object] | None = None) -> Path:
    root.mkdir(mode=0o700)
    path = root / "nextcloud-r1.json"
    path.write_text(
        json.dumps(payload or _manifest(), sort_keys=True),
        encoding="utf-8",
    )
    path.chmod(0o600)
    return path


def _verifier(path: Path) -> FileBoundExecutionAuthorizationVerifier:
    return FileBoundExecutionAuthorizationVerifier(
        path,
        required_owner_uid=os.geteuid(),
        now=lambda: FIXED_NOW,
    )


def _verify(
    verifier: FileBoundExecutionAuthorizationVerifier,
    *,
    authorization_reference: str = AUTHORIZATION_REFERENCE,
):
    return verifier.verify(
        operation_id="ISSUE-113-R1",
        operation="nextcloud.r1.offhost.transfer",
        target_id="cyberskills-vps",
        plan_id="GH-113",
        plan_revision="1",
        authorization_reference=authorization_reference,
    )


def test_file_bound_authorization_accepts_only_exact_live_binding(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path / "approvals")
    decision = _verify(_verifier(path))
    assert decision.authorized is True
    assert "issue-113-r1-transfer" in decision.reason
    assert AUTHORIZATION_REFERENCE not in path.read_text(encoding="utf-8")


def test_file_bound_authorization_rejects_wrong_reference(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path / "approvals")
    decision = _verify(_verifier(path), authorization_reference="WRONG")
    assert decision.authorized is False
    assert "does not match" in decision.reason


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("operation_id", "OTHER"),
        ("operation", "nextcloud.r1.offhost.verify"),
        ("target_id", "tasks.cyberdjs.org"),
        ("plan_id", "OTHER"),
        ("plan_revision", "2"),
    ],
)
def test_file_bound_authorization_rejects_tuple_mismatch(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    payload = _manifest()
    payload[field] = value
    path = _write_manifest(tmp_path / "approvals", payload)
    decision = _verify(_verifier(path))
    assert decision.authorized is False
    assert "exact governed action" in decision.reason


def test_file_bound_authorization_rejects_expired_or_overlong_window(tmp_path: Path) -> None:
    expired = _manifest()
    expired["issued_at"] = "2026-11-12T14:00:00Z"
    expired["expires_at"] = "2026-11-12T14:30:00Z"
    path = _write_manifest(tmp_path / "expired", expired)
    assert _verify(_verifier(path)).authorized is False

    overlong = _manifest()
    overlong["issued_at"] = "2026-11-12T14:30:00Z"
    overlong["expires_at"] = "2026-11-12T16:00:01Z"
    path = _write_manifest(tmp_path / "overlong", overlong)
    assert _verify(_verifier(path)).authorized is False


def test_file_bound_authorization_rejects_unsafe_file_or_parent_permissions(
    tmp_path: Path,
) -> None:
    path = _write_manifest(tmp_path / "unsafe-file")
    path.chmod(0o622)
    assert _verify(_verifier(path)).authorized is False

    path = _write_manifest(tmp_path / "unsafe-parent")
    path.parent.chmod(0o722)
    assert _verify(_verifier(path)).authorized is False


def test_file_bound_authorization_rejects_extra_fields_and_symlink(tmp_path: Path) -> None:
    payload = _manifest()
    payload["raw_authorization"] = AUTHORIZATION_REFERENCE
    path = _write_manifest(tmp_path / "extra", payload)
    assert _verify(_verifier(path)).authorized is False

    target = _write_manifest(tmp_path / "target")
    link_parent = tmp_path / "link-parent"
    link_parent.mkdir(mode=0o700)
    link = link_parent / "nextcloud-r1.json"
    link.symlink_to(target)
    assert _verify(_verifier(link)).authorized is False
