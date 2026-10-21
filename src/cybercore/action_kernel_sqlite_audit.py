"""Single-host SQLite audit sink for synthetic Action Kernel events.

A hash chain detects accidental or unsophisticated alteration, but does not
provide authenticity against an attacker able to rewrite the entire database.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from cybercore.action_kernel import AuditEvent


class SQLiteAuditSink:
    """Durable append-only-by-API event writer for a trusted local application."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        if not self._path.is_absolute() or str(self._path) == ":memory:":
            raise ValueError("Audit database requires an absolute file path")

    def __call__(self, event: AuditEvent) -> None:
        document = {
            "schema_version": event.schema_version,
            "stage": event.stage,
            "task_id": event.task_id,
            "correlation_id": event.correlation_id,
            "actor": event.actor,
            "capability": event.capability,
            "target_id": event.target_id,
            "outcome": event.outcome,
            "reason": event.reason,
            "occurred_at": event.occurred_at.isoformat(),
            "provenance": event.provenance.as_nexus(),
            "evidence_sha256": event.evidence_sha256,
        }
        payload = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if len(payload.encode("utf-8")) > 8192:
            raise ValueError("Audit payload exceeds limit")
        with sqlite3.connect(self._path, timeout=5) as conn:
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS audit_events ("
                "seq INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL, "
                "previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL)"
            )
            previous = conn.execute(
                "SELECT event_hash FROM audit_events ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            previous_hash = "0" * 64 if previous is None else str(previous[0])
            event_hash = hashlib.sha256(
                (previous_hash + "\n" + payload).encode("utf-8")
            ).hexdigest()
            conn.execute(
                "INSERT INTO audit_events (payload, previous_hash, event_hash) VALUES (?,?,?)",
                (payload, previous_hash, event_hash),
            )
            conn.commit()

    def verify_chain(self) -> bool:
        """Validate stored adjacency and payload digests, not external authenticity."""
        with sqlite3.connect(self._path, timeout=5) as conn:
            rows = conn.execute(
                "SELECT seq,payload,previous_hash,event_hash FROM audit_events ORDER BY seq"
            ).fetchall()
        previous_hash = "0" * 64
        previous_seq = 0
        for seq, payload, prior, digest in rows:
            if seq != previous_seq + 1 or prior != previous_hash:
                return False
            actual = hashlib.sha256((prior + "\n" + payload).encode("utf-8")).hexdigest()
            if actual != digest:
                return False
            previous_hash = digest
            previous_seq = seq
        return True
