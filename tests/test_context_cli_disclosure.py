from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from cybercore.entrypoint import main


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


def test_context_cli_defaults_to_standard_json_disclosure(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)

    exit_code = main(["--repo", str(repo), "--json", "context"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["trusted"] is True
    assert payload["branch"] == "main"
    assert payload["repository"] == "[REDACTED]"


def test_context_cli_redacted_json_preserves_public_types(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)

    exit_code = main(["--repo", str(repo), "--json", "context", "--redact"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["trusted"] is True
    assert payload["dirty"] is False
    assert payload["branch"] == "[REDACTED]"
    assert payload["repository"] == "[REDACTED]"


def test_context_cli_full_json_discloses_repository_path(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)

    exit_code = main(["--repo", str(repo), "--json", "context", "--full"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["repository"] == str(repo.resolve())
    assert payload["trusted"] is True


def test_context_cli_text_uses_the_same_disclosure_policy(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)

    exit_code = main(["--repo", str(repo), "context"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "trusted: True" in output
    assert "branch: main" in output
    assert "repository: [REDACTED]" in output
    assert str(repo.resolve()) not in output


def test_context_cli_error_does_not_leak_local_path(tmp_path: Path, capsys) -> None:
    exit_code = main(["--repo", str(tmp_path), "context"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "Not a Git repository" in captured.err
    assert str(tmp_path.resolve()) not in captured.err


def test_context_cli_rejects_redact_and_full_together(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        main(["--repo", str(repo), "context", "--redact", "--full"])

    assert exc_info.value.code == 2
