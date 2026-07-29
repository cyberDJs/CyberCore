from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from cybercore.verification_runner import VerificationRunError, run_verification


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "CyberCore Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / "README.md").write_text("test\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    return tmp_path


def test_run_verification_writes_success_evidence(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    output = repo / "evidence.json"

    evidence = run_verification(
        repo,
        [sys.executable, "-c", "print('ok')"],
        summary="verification passed",
        output=output,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert evidence.exit_code == 0
    assert payload["summary"] == "verification passed"
    assert payload["repository"] == str(repo.resolve())
    assert payload["commit"] == subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_run_verification_records_failed_exit_code(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    output = repo / "failed.json"

    evidence = run_verification(
        repo,
        [sys.executable, "-c", "raise SystemExit(7)"],
        summary="verification failed",
        output=output,
    )

    assert evidence.exit_code == 7
    assert json.loads(output.read_text(encoding="utf-8"))["exit_code"] == 7


def test_run_verification_rejects_empty_command(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    with pytest.raises(VerificationRunError, match="command is empty"):
        run_verification(repo, [], summary="x", output=repo / "evidence.json")


def test_run_verification_rejects_empty_summary(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    with pytest.raises(VerificationRunError, match="summary is empty"):
        run_verification(
            repo,
            [sys.executable, "-c", "pass"],
            summary=" ",
            output=repo / "evidence.json",
        )
