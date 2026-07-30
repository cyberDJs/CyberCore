from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "CyberCore Tests")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "remote", "add", "origin", "https://github.com/cyberDJs/CyberCore.git")
    (repo / ".cybercore").mkdir()
    (repo / ".cybercore" / "project.yaml").write_text(
        "version: 1\nidentity:\n  name: CyberCore\n"
        "  repository: git:github.com/cyberDJs/CyberCore\n",
        encoding="utf-8",
    )
    (repo / "PROJECT_STATE.md").write_text("# Project State\n", encoding="utf-8")
    (repo / "README.md").write_text("# Test\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "test fixture")
    return repo


def _run_module(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "cybercore", "--repo", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_module_entrypoint_routes_json_context(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    completed = _run_module(repo, "--json", "context")
    payload = json.loads(completed.stdout)

    assert completed.returncode == 0
    assert payload["trusted"] is True
    assert payload["repository"] == "[REDACTED]"


def test_module_entrypoint_routes_context_redact(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    completed = _run_module(repo, "context", "--redact")

    assert completed.returncode == 0
    assert "branch: [REDACTED]" in completed.stdout
    assert str(repo.resolve()) not in completed.stdout


def test_module_entrypoint_routes_identity(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    completed = _run_module(repo, "identity")

    assert completed.returncode == 0
    assert "REPOSITORY IDENTITY" in completed.stdout
    assert str(repo.resolve()) not in completed.stdout
