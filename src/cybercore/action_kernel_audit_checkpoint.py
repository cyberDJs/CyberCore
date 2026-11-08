"""Read-only audit checkpoint snapshots for independently retained trust anchors.

Checkpoints are plain data, NOT signed or trusted merely because they exist.
The verifier must receive a checkpoint from outside the audited database's
trust boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
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


def _verified_snapshot(path: str | Path) -> list[tuple[int, str]]:
    """Verify the hash chain and capture its sequence/hash view in one read transaction."""
    db = Path(path)
    if not db.is_absolute():
        raise ValueError("Absolute database path required")

    # Read-only mode prevents accidentally creating a missing database.
    with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=5) as conn:
        conn.execute("BEGIN")
        try:
            rows = conn.execute(
                "SELECT seq,payload,previous_hash,event_hash FROM audit_events ORDER BY seq"
            ).fetchall()
            previous = GENESIS
            previous_seq = 0
            snapshot: list[tuple[int, str]] = []
            for seq, payload, prior, digest in rows:
                if seq != previous_seq + 1 or prior != previous:
                    raise ValueError("Audit chain verification failed")
                calculated = hashlib.sha256((prior + "\n" + payload).encode("utf-8")).hexdigest()
                if digest != calculated:
                    raise ValueError("Audit chain verification failed")
                snapshot.append((seq, digest))
                previous = digest
                previous_seq = seq
            return snapshot
        finally:
            conn.rollback()


def audit_checkpoint(path: str | Path, *, database_identity: str) -> AuditCheckpoint:
    """Export an internally consistent checkpoint from a verified read snapshot."""
    snapshot = _verified_snapshot(path)
    if not snapshot:
        return AuditCheckpoint(0, GENESIS, database_identity)
    seq, digest = snapshot[-1]
    return AuditCheckpoint(seq, digest, database_identity)


def verify_anchored_checkpoint(
    path: str | Path,
    *,
    trusted_checkpoint: AuditCheckpoint,
    expected_database_identity: str,
) -> bool:
    """Check that a trusted anchored prefix remains in the verified read snapshot."""
    if trusted_checkpoint.database_identity != expected_database_identity:
        return False
    try:
        snapshot = _verified_snapshot(path)
    except (ValueError, sqlite3.Error, OSError):
        return False
    if trusted_checkpoint.sequence == 0:
        return trusted_checkpoint.event_hash == GENESIS
    index = trusted_checkpoint.sequence - 1
    return index < len(snapshot) and snapshot[index] == (
        trusted_checkpoint.sequence,
        trusted_checkpoint.event_hash,
    )
