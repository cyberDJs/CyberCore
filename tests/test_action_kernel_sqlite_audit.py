from datetime import datetime, timezone
from pathlib import Path
import sqlite3

import pytest

from cybercore.action_kernel import AuditEvent, Provenance
from cybercore.action_kernel_sqlite_audit import SQLiteAuditSink


def _event(stage: str = "request") -> AuditEvent:
    now = datetime.now(timezone.utc)
    return AuditEvent(
        stage=stage,
        task_id="local-1",
        correlation_id="corr-1",
        actor="trusted-actor",
        capability="diagnostics.synthetic_status.v1",
        target_id="local-node",
        outcome="OBSERVED",
        reason="REQUEST_RECEIVED",
        occurred_at=now,
        provenance=Provenance("cybercore", "test", "local", now),
    )


def test_chain_survives_restart_and_detects_payload_tamper(tmp_path: Path) -> None:
    path = tmp_path / "audit.sqlite"
    sink = SQLiteAuditSink(path)
    sink(_event("request"))
    SQLiteAuditSink(path)(_event("policy"))
    assert SQLiteAuditSink(path).verify_chain()

    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE audit_events SET payload='forged' WHERE seq=1")
    assert not sink.verify_chain()


def test_chain_detects_missing_middle_record(tmp_path: Path) -> None:
    path = tmp_path / "audit.sqlite"
    sink = SQLiteAuditSink(path)
    for stage in ("request", "policy", "execution"):
        sink(_event(stage))
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM audit_events WHERE seq=2")
    assert not sink.verify_chain()


def test_unavailable_audit_backend_raises(tmp_path: Path) -> None:
    sink = SQLiteAuditSink(tmp_path / "missing" / "audit.sqlite")
    with pytest.raises(sqlite3.OperationalError):
        sink(_event())


def test_relative_path_rejected() -> None:
    with pytest.raises(ValueError):
        SQLiteAuditSink("audit.sqlite")
