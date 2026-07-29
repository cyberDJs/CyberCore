from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

import pytest

from cybercore.checkpoint import collect_checkpoint
from cybercore.verification_evidence import (
    VerificationEvidence,
    VerificationEvidenceError,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "CyberCore Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / "README.md").write_text("verification\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "verification target")
    return tmp_path


def _payload(repo: Path, commit: str) -> dict[str, object]:
    return {
        "command": "pytest -q",
        "exit_code": 0,
        "duration": 4.25,
        "summary": "26 passed",
        "repository": str(repo.resolve()),
        "commit": commit,
        "generated_at": "2026-07-29T21:00:00Z",
    }


def test_load_and_validate_successful_evidence(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(
        repo, now=datetime(2026, 7, 29, 21, 0, tzinfo=timezone.utc)
    )
    path = repo / "evidence.json"
    path.write_text(json.dumps(_payload(repo, checkpoint.commit)), encoding="utf-8")

    evidence = VerificationEvidence.from_file(path)
    evidence.validate_for(checkpoint)

    assert evidence.exit_code == 0
    assert evidence.checkpoint_summary() == "26 passed via `pytest -q` in 4.25s"


def test_rejects_failed_verification_command(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    payload = _payload(repo, checkpoint.commit)
    payload["exit_code"] = 1
    evidence = VerificationEvidence.from_dict(payload)

    with pytest.raises(VerificationEvidenceError, match="failed with exit code 1"):
        evidence.validate_for(checkpoint)


def test_rejects_repository_mismatch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    payload = _payload(repo, checkpoint.commit)
    payload["repository"] = str(repo / "other")
    evidence = VerificationEvidence.from_dict(payload)

    with pytest.raises(VerificationEvidenceError, match="repository does not match"):
        evidence.validate_for(checkpoint)


def test_rejects_commit_mismatch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    evidence = VerificationEvidence.from_dict(_payload(repo, "0" * 40))

    with pytest.raises(VerificationEvidenceError, match="commit does not match"):
        evidence.validate_for(checkpoint)


def test_rejects_missing_required_fields() -> None:
    with pytest.raises(VerificationEvidenceError, match="missing fields"):
        VerificationEvidence.from_dict({"command": "pytest -q"})
