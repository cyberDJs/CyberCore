"""Durable single-host replay protection for local, read-only Action Kernel dry-runs.

One SQLite database is the authority for all cooperating local processes.
This is NOT a distributed/multi-host authorization store.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteReplayGuard:
    """Atomic, non-expiring claims; fail closed on corruption or unavailable storage.

    Claims intentionally remain forever until an explicit offline administrative
    retention procedure. Removing a claim would permit replay of an old receipt.
    """

    def __init__(self, path: str | Path, *, timeout: float = 5.0) -> None:
        self._path = Path(path)
        if str(self._path) == ":memory:" or not self._path.is_absolute():
            raise ValueError("Replay database must use an absolute file path")
        if timeout <= 0:
            raise ValueError("Timeout must be positive")
        self._timeout = timeout

    def claim_once(self, key: str) -> bool:
        if not isinstance(key, str) or not key or len(key.encode("utf-8")) > 1024:
            raise ValueError("Invalid replay key")
        # A local, writable filesystem and protected database directory are required.
        # No network filesystem or remote multi-host sharing is supported.
        with sqlite3.connect(self._path, timeout=self._timeout) as conn:
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute("PRAGMA synchronous = FULL")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS replay_claims "
                "(key TEXT PRIMARY KEY NOT NULL, claimed_at TEXT NOT NULL "
                "DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')))"
            )
            cursor = conn.execute(
                "INSERT OR IGNORE INTO replay_claims (key) VALUES (?)", (key,)
            )
            conn.commit()
            return cursor.rowcount == 1
