from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any


@dataclass(frozen=True, slots=True)
class RunState:
    run_id: str
    manifest_digest: str
    status: str
    step_index: int
    consecutive_failures: int
    last_step_fingerprint: str | None
    duplicate_count: int
    evaluator_score: float
    started_at: float
    updated_at: float


@dataclass(frozen=True, slots=True)
class RunEvent:
    id: int
    run_id: str
    step_index: int
    kind: str
    payload: dict[str, object]
    created_at: float


class LongRunStateStore:
    def __init__(self, path: Path, *, create: bool = True) -> None:
        self.path = path
        self.create = create
        if create:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._init()
        elif not self.path.is_file():
            raise FileNotFoundError(f"LongRun state database does not exist: {self.path}")

    def _connect(self) -> sqlite3.Connection:
        if self.create:
            connection = sqlite3.connect(self.path)
        else:
            connection = sqlite3.connect(f"file:{self.path}?mode=rw", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def _init(self) -> None:
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    manifest_digest TEXT NOT NULL,
                    status TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    consecutive_failures INTEGER NOT NULL,
                    last_step_fingerprint TEXT,
                    duplicate_count INTEGER NOT NULL,
                    evaluator_score REAL NOT NULL,
                    started_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)

    @staticmethod
    def _run_values(state: RunState) -> tuple[object, ...]:
        return (
            state.run_id,
            state.manifest_digest,
            state.status,
            state.step_index,
            state.consecutive_failures,
            state.last_step_fingerprint,
            state.duplicate_count,
            state.evaluator_score,
            state.started_at,
            state.updated_at,
        )

    @staticmethod
    def _update_values(state: RunState) -> tuple[object, ...]:
        return (
            state.manifest_digest,
            state.status,
            state.step_index,
            state.consecutive_failures,
            state.last_step_fingerprint,
            state.duplicate_count,
            state.evaluator_score,
            state.started_at,
            state.updated_at,
            state.run_id,
        )

    @staticmethod
    def _encode_payload(payload: dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _append_encoded_event(
        db: sqlite3.Connection,
        run_id: str,
        step_index: int,
        kind: str,
        payload: str,
        created_at: float,
    ) -> None:
        db.execute(
            "INSERT INTO events(run_id, step_index, kind, payload, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (run_id, step_index, kind, payload, created_at),
        )

    def create_run(self, state: RunState) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                self._run_values(state),
            )

    def create_with_event(
        self,
        state: RunState,
        kind: str,
        payload: dict[str, Any],
        created_at: float,
    ) -> None:
        encoded = self._encode_payload(payload)
        with self._connect() as db:
            db.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                self._run_values(state),
            )
            self._append_encoded_event(
                db,
                state.run_id,
                state.step_index,
                kind,
                encoded,
                created_at,
            )

    def load(self, run_id: str) -> RunState | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return RunState(**dict(row)) if row else None

    def list_events(self, run_id: str, *, limit: int = 100) -> list[RunEvent]:
        if limit < 1 or limit > 1000:
            raise ValueError("event limit must be between 1 and 1000")
        with self._connect() as db:
            rows = db.execute(
                "SELECT id, run_id, step_index, kind, payload, created_at "
                "FROM events WHERE run_id = ? ORDER BY id DESC LIMIT ?",
                (run_id, limit),
            ).fetchall()
        events: list[RunEvent] = []
        for row in reversed(rows):
            payload = json.loads(row["payload"])
            if not isinstance(payload, dict):
                raise RuntimeError("stored LongRun event payload is not an object")
            events.append(
                RunEvent(
                    id=row["id"],
                    run_id=row["run_id"],
                    step_index=row["step_index"],
                    kind=row["kind"],
                    payload=payload,
                    created_at=row["created_at"],
                )
            )
        return events

    def save(self, state: RunState) -> None:
        with self._connect() as db:
            db.execute(
                """UPDATE runs SET manifest_digest=?, status=?, step_index=?,
                consecutive_failures=?, last_step_fingerprint=?, duplicate_count=?,
                evaluator_score=?, started_at=?, updated_at=? WHERE run_id=?""",
                self._update_values(state),
            )

    def save_with_event(
        self,
        state: RunState,
        kind: str,
        payload: dict[str, Any],
        created_at: float,
    ) -> None:
        encoded = self._encode_payload(payload)
        with self._connect() as db:
            db.execute(
                """UPDATE runs SET manifest_digest=?, status=?, step_index=?,
                consecutive_failures=?, last_step_fingerprint=?, duplicate_count=?,
                evaluator_score=?, started_at=?, updated_at=? WHERE run_id=?""",
                self._update_values(state),
            )
            self._append_encoded_event(
                db,
                state.run_id,
                state.step_index,
                kind,
                encoded,
                created_at,
            )

    def append_event(
        self,
        run_id: str,
        step_index: int,
        kind: str,
        payload: dict[str, Any],
        created_at: float,
    ) -> None:
        encoded = self._encode_payload(payload)
        with self._connect() as db:
            self._append_encoded_event(db, run_id, step_index, kind, encoded, created_at)
