from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from cybercore.action_kernel_sqlite_replay import SQLiteReplayGuard


def test_claim_survives_reopen(tmp_path: Path) -> None:
    path = tmp_path / "claims.sqlite"
    assert SQLiteReplayGuard(path).claim_once("actor:task:correlation")
    assert not SQLiteReplayGuard(path).claim_once("actor:task:correlation")
    assert SQLiteReplayGuard(path).claim_once("actor:other:correlation")


def test_atomic_claim_across_connections(tmp_path: Path) -> None:
    path = tmp_path / "claims.sqlite"

    def claim(_: int) -> bool:
        return SQLiteReplayGuard(path).claim_once("same-key")

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(claim, range(24)))
    assert results.count(True) == 1
    assert results.count(False) == 23


def test_invalid_paths_and_keys_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        SQLiteReplayGuard("relative.db")
    guard = SQLiteReplayGuard(tmp_path / "claims.sqlite")
    for key in ("", "x" * 1025):
        with pytest.raises(ValueError):
            guard.claim_once(key)


def test_unavailable_directory_does_not_grant_claim(tmp_path: Path) -> None:
    guard = SQLiteReplayGuard(tmp_path / "missing" / "claims.sqlite")
    with pytest.raises(OSError):
        guard.claim_once("key")
