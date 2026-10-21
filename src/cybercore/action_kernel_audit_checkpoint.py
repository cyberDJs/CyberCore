"""Read-only audit checkpoint snapshots for independently retained trust anchors.

Checkpoints are plain data, NOT signed or trusted merely because they exist.
The verifier must receive a checkpoint from outside the audited database's
trust boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from pathlib import Path

GENESIS = "0" * 64


@dataclass(frozen=True)
class AuditCheckpoint:
    sequence: int
    event_hash: str
    database_identity: str

    def __post_init__(self) -> None:
        if self.sequence < 0 or len(self.event_hash) != 64:
            raise ValueError("Invalid checkpoint")
        if not self.database_identity.strip():
            raise ValueError("Missing database identity")
        try:
            int(self.event_hash, 16)
        except ValueError as exc:
            raise ValueError("Invalid checkpoint digest") from exc


def audit_checkpoint(path: str | Path, *, database_identity: str) -> AuditCheckpoint:
    """Export a checkpoint after validating the entire local hash chain."""
    from cybercore.action_kernel_sqlite_audit import SQLiteAuditSink

    db = Path(path)
    if not db.is_absolute():
        raise ValueError("Absolute database path required")
    if not SQLiteAuditSink(db).verify_chain():
        raise ValueError("Audit chain verification failed")
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
        row = conn.execute(
            "SELECT seq,event_hash FROM audit_events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return AuditCheckpoint(0, GENESIS, database_identity)
    return AuditCheckpoint(int(row[0]), str(row[1]), database_identity)


def verify_anchored_checkpoint(
    path: str | Path,
    *,
    trusted_checkpoint: AuditCheckpoint,
    expected_database_identity: str,
) -> bool:
    """Verify a retained, independently trusted checkpoint exists in intact history.

    Later events are allowed, but truncating/replacing the anchored prefix
    fails. This does not prove integrity beyond the checkpoint.
    """
    if trusted_checkpoint.database_identity != expected_database_identity:
        return False
    from cybercore.action_kernel_sqlite_audit import SQLiteAuditSink

    db = Path(path)
    if not db.is_absolute() or not SQLiteAuditSink(db).verify_chain():
        return False
    if trusted_checkpoint.sequence == 0:
        return trusted_checkpoint.event_hash == GENESIS
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
        row = conn.execute(
            "SELECT event_hash FROM audit_events WHERE seq = ?",
            (trusted_checkpoint.sequence,),
        ).fetchone()
    return row is not None and str(row[0]) == trusted_checkpoint.event_hash
