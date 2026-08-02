from __future__ import annotations

import json
from pathlib import Path
import subprocess

from cybercore.checkpoint import collect_checkpoint
from cybercore.cli import main


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "CyberCore Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / "PROJECT_STATE.md").write_text("# State\n", encoding="utf-8")
    (tmp_path / "WORKLOG.md").write_text("# CyberCore Worklog\n", encoding="utf-8")
    (tmp_path / ".cybercore").mkdir()
    (tmp_path / ".cybercore" / "project.yaml").write_text(
        """version: 1
current:
  milestone: Verification Evidence Automation v0.1
  active_artifact: WB-0017
  branch: feat/verification-evidence
""",
        encoding="utf-8",
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    return tmp_path


def _write_evidence(repo: Path, path: Path, *, commit: str | None = None) -> None:
    checkpoint = collect_checkpoint(repo)
    path.write_text(
        json.dumps(
            {
                "command": "pytest -q",
                "exit_code": 0,
                "duration": 5.9,
                "summary": "32 passed",
                "repository": str(repo.resolve()),
                "commit": commit or checkpoint.commit,
                "generated_at": "2026-07-29T21:00:00Z",
            }
        ),
        encoding="utf-8",
    )


def test_cli_memory_accepts_matching_evidence(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    evidence = repo / "evidence.json"
    _write_evidence(repo, evidence)

    rc = main(
        [
            "--repo",
            str(repo),
            "checkpoint",
            "--memory",
            "--evidence",
            "evidence.json",
        ]
    )

    output = capsys.readouterr().out
    assert rc == 0
    assert "32 passed" in output
    assert (repo / "PROJECT_STATE.md").read_text(encoding="utf-8") == "# State\n"


def test_cli_rejects_evidence_with_manual_result(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    evidence = repo / "evidence.json"
    _write_evidence(repo, evidence)

    rc = main(
        [
            "--repo",
            str(repo),
            "checkpoint",
            "--memory",
            "--evidence",
            "evidence.json",
            "--test-result",
            "manual",
        ]
    )

    assert rc == 2
    assert "cannot be combined" in capsys.readouterr().err


def test_cli_rejects_evidence_for_wrong_commit(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    evidence = repo / "evidence.json"
    _write_evidence(repo, evidence, commit="wrong")

    rc = main(
        [
            "--repo",
            str(repo),
            "checkpoint",
            "--memory",
            "--evidence",
            "evidence.json",
        ]
    )

    assert rc == 2
    assert "commit" in capsys.readouterr().err


def test_cli_requires_memory_for_evidence(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    evidence = repo / "evidence.json"
    _write_evidence(repo, evidence)

    rc = main(
        [
            "--repo",
            str(repo),
            "checkpoint",
            "--evidence",
            "evidence.json",
        ]
    )

    assert rc == 2
    assert "--evidence requires --memory" in capsys.readouterr().err
