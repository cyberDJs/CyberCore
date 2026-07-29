from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from cybercore.cli import main


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "CyberCore Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / ".cybercore").mkdir()
    (tmp_path / ".cybercore" / "project.yaml").write_text("version: 1\n", encoding="utf-8")
    (tmp_path / "PROJECT_STATE.md").write_text("# State\n", encoding="utf-8")
    (tmp_path / "WORKLOG.md").write_text("# Worklog\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    return tmp_path


def test_evidence_run_cli_writes_successful_evidence(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    output = Path(".cybercore/evidence/success.json")

    rc = main(
        [
            "--repo",
            str(repo),
            "evidence",
            "run",
            "--summary",
            "command passed",
            "--output",
            str(output),
            "--",
            sys.executable,
            "-c",
            "print('ok')",
        ]
    )

    assert rc == 0
    payload = json.loads((repo / output).read_text(encoding="utf-8"))
    assert payload["exit_code"] == 0
    assert payload["summary"] == "command passed"
    assert payload["repository"] == str(repo.resolve())


def test_evidence_run_cli_returns_command_exit_code(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    output = Path(".cybercore/evidence/failure.json")

    rc = main(
        [
            "--repo",
            str(repo),
            "evidence",
            "run",
            "--summary",
            "command failed",
            "--output",
            str(output),
            "--",
            sys.executable,
            "-c",
            "raise SystemExit(7)",
        ]
    )

    assert rc == 7
    payload = json.loads((repo / output).read_text(encoding="utf-8"))
    assert payload["exit_code"] == 7


def test_evidence_run_cli_rejects_empty_command(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    rc = main(
        [
            "--repo",
            str(repo),
            "evidence",
            "run",
            "--summary",
            "nothing",
            "--output",
            "evidence.json",
        ]
    )

    assert rc == 2
