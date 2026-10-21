"""Cross-process replay tests: each worker opens an independent SQLite connection."""

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pytest

from cybercore.action_kernel_sqlite_replay import SQLiteReplayGuard


def _claim_from_process(args: tuple[str, str]) -> bool:
    path, key = args
    return SQLiteReplayGuard(path, timeout=15).claim_once(key)


def test_same_claim_is_atomic_across_processes(tmp_path: Path) -> None:
    path = str(tmp_path / "process-claims.sqlite")
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(_claim_from_process, [(path, "same-key")] * 16))
    assert results.count(True) == 1
    assert results.count(False) == 15
    # A new guard after all workers have exited cannot resurrect the claim.
    assert not SQLiteReplayGuard(path).claim_once("same-key")


def test_distinct_claims_across_processes(tmp_path: Path) -> None:
    path = str(tmp_path / "process-claims.sqlite")
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(_claim_from_process, [(path, f"unique-{i}") for i in range(8)]))
    assert results == [True] * 8


def test_missing_database_directory_fails_closed_in_child(tmp_path: Path) -> None:
    path = str(tmp_path / "missing" / "claims.sqlite")
    with ProcessPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_claim_from_process, (path, "key"))
        with pytest.raises(Exception, match="unable to open database"):
            future.result()
    assert not Path(path).exists()
