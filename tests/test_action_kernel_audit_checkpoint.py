"""Audit checkpoint tests using an out-of-band retained checkpoint object."""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from cybercore.action_kernel import AuditEvent, Provenance
from cybercore.action_kernel_audit_checkpoint import (
    audit_checkpoint,
    verify_anchored_checkpoint,
)
from cybercore.action_kernel_sqlite_audit import SQLiteAuditSink


def _event(index: int) -> AuditEvent:
    now = datetime.now(timezone.utc)
    return AuditEvent(
        stage="request",
        task_id=f"checkpoint-{index}",
        correlation_id=f"corr-{index}",
        actor="local-test",
        capability="diagnostics.synthetic_status.v1",
        target_id="local-node",
        outcome="OBSERVED",
        reason="REQUEST_RECEIVED",
        occurred_at=now,
        provenance=Provenance("cybercore", "test", "local", now),
    )


def test_checkpoint_detects_tail_truncation_and_allows_extension(tmp_path: Path) -> None:
    path = tmp_path / "audit.sqlite"
    sink = SQLiteAuditSink(path)
    for i in range(3):
        sink(_event(i))
    trusted = audit_checkpoint(path, database_identity="local-instance-A")
    assert trusted.sequence == 3
    sink(_event(3))
    assert verify_anchored_checkpoint(
        path, trusted_checkpoint=trusted, expected_database_identity="local-instance-A"
    )
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM audit_events WHERE seq>=3")
    assert sink.verify_chain()  # local hash chain alone misses a clean tail truncation
    assert not verify_anchored_checkpoint(
        path, trusted_checkpoint=trusted, expected_database_identity="local-instance-A"
    )


def test_wrong_database_identity_denied(tmp_path: Path) -> None:
    path = tmp_path / "audit.sqlite"
    SQLiteAuditSink(path)(_event(0))
    trusted = audit_checkpoint(path, database_identity="instance-A")
    assert not verify_anchored_checkpoint(
        path, trusted_checkpoint=trusted, expected_database_identity="instance-B"
    )
