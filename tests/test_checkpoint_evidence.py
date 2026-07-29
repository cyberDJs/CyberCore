from __future__ import annotations

import json
from pathlib import Path

import pytest

from cybercore.checkpoint import RepositoryCheckpoint
from cybercore.checkpoint_evidence import (
    CheckpointEvidenceError,
    resolve_test_result,
)


def _checkpoint(repo: Path, commit: str = "abc123") -> RepositoryCheckpoint:
    return RepositoryCheckpoint(
        generated_at="2026-07-29T21:00:00Z",
        repository=str(repo.resolve()),
        branch="feat/verification-evidence",
        commit=commit,
        commit_subject="test commit",
        dirty=False,
        changed_paths=(),
        project_state_present=True,
        project_kernel_present=True,
    )


def _evidence(path: Path, repo: Path, *, commit: str = "abc123", exit_code: int = 0) -> None:
    path.write_text(
        json.dumps(
            {
                "command": "pytest -q",
                "exit_code": exit_code,
                "duration": 4.25,
                "summary": "28 passed",
                "repository": str(repo.resolve()),
                "commit": commit,
                "generated_at": "2026-07-29T21:00:00Z",
            }
        ),
        encoding="utf-8",
    )


def test_resolve_test_result_accepts_matching_evidence(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    _evidence(evidence_path, tmp_path)

    summary, evidence = resolve_test_result(
        _checkpoint(tmp_path), evidence_path=evidence_path
    )

    assert summary == "28 passed"
    assert evidence is not None
    assert evidence.command == "pytest -q"


def test_resolve_test_result_preserves_manual_fallback(tmp_path: Path) -> None:
    summary, evidence = resolve_test_result(
        _checkpoint(tmp_path), test_result="manual verification"
    )

    assert summary == "manual verification"
    assert evidence is None


def test_resolve_test_result_rejects_conflicting_sources(tmp_path: Path) -> None:
    with pytest.raises(CheckpointEvidenceError, match="cannot be combined"):
        resolve_test_result(
            _checkpoint(tmp_path),
            evidence_path=tmp_path / "evidence.json",
            test_result="manual",
        )


def test_resolve_test_result_rejects_wrong_commit(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    _evidence(evidence_path, tmp_path, commit="wrong")

    with pytest.raises(ValueError, match="commit"):
        resolve_test_result(_checkpoint(tmp_path), evidence_path=evidence_path)
