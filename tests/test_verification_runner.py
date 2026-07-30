from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from cybercore.verification_runner import VerificationRunError, run_verification
from cybercore.verification_evidence import repository_evidence_binding


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
    assert "repository" not in payload
    assert payload["repository_binding"] == repository_evidence_binding(repo)
    assert str(repo.resolve()) not in json.dumps(payload)
    assert payload["commit"] == subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_run_verification_sanitizes_persisted_command_metadata(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    output = repo / "evidence.json"

    run_verification(
        repo,
        [
            sys.executable,
            "-c",
            "pass",
            "--token",
            "abc123",
            "--password=hunter2",
            "https://user:secret@example.test/repo.git",
            str(repo.resolve()),
        ],
        summary="verification passed",
        output=output,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    rendered = json.dumps(payload)
    assert "abc123" not in rendered
    assert "hunter2" not in rendered
    assert "user:secret" not in rendered
    assert str(repo.resolve()) not in rendered


def test_run_verification_sanitizes_persisted_summary(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    output = repo / "evidence.json"

    run_verification(
        repo,
        [sys.executable, "-c", "pass"],
        summary=(
            f"checked {repo.resolve()} with "
            "https://user:password@example.test/repo?access_token=tokensecret123 "
            "password=hunter2"
        ),
        output=output,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    rendered = json.dumps(payload)
    assert str(repo.resolve()) not in rendered
    assert "user:password" not in rendered
    assert "tokensecret123" not in rendered
    assert "hunter2" not in rendered
    assert "[REDACTED_PATH]" in payload["summary"]


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
