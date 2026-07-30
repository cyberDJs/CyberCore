from __future__ import annotations

import json
from pathlib import Path
import subprocess

from cybercore.entrypoint import main
from cybercore.trusted_operation_context import collect_trusted_operation_context


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


def test_clean_repository_context_is_trusted(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    context = collect_trusted_operation_context(
        repo,
        operation="checkpoint",
        risk="low",
        expected_branch="main",
        require_clean=True,
    )

    assert context.trusted is True
    assert context.branch == "main"
    assert context.dirty is False
    assert all(check.passed for check in context.checks)


def test_dirty_repository_fails_when_clean_tree_is_required(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "README.md").write_text("dirty\n", encoding="utf-8")

    context = collect_trusted_operation_context(repo, require_clean=True)

    assert context.trusted is False
    failed = {check.name for check in context.checks if not check.passed}
    assert "clean_working_tree" in failed


def test_dirty_repository_is_reported_but_not_rejected_by_default(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "README.md").write_text("dirty\n", encoding="utf-8")

    context = collect_trusted_operation_context(repo)

    assert context.dirty is True
    assert context.trusted is True


def test_expected_branch_mismatch_is_untrusted(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    context = collect_trusted_operation_context(repo, expected_branch="feature/other")

    assert context.trusted is False
    check = next(item for item in context.checks if item.name == "expected_branch")
    assert check.passed is False
    assert "feature/other" in check.detail


def test_expected_commit_mismatch_is_untrusted(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    context = collect_trusted_operation_context(repo, expected_commit="0" * 40)

    assert context.trusted is False
    check = next(item for item in context.checks if item.name == "expected_commit")
    assert check.passed is False


def test_missing_project_state_is_untrusted(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "PROJECT_STATE.md").unlink()

    context = collect_trusted_operation_context(repo)

    assert context.trusted is False
    check = next(item for item in context.checks if item.name == "project_state")
    assert check.passed is False


def test_context_cli_supports_json(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)

    exit_code = main(
        [
            "--repo",
            str(repo),
            "--json",
            "context",
            "--operation",
            "evidence",
            "--risk",
            "medium",
            "--expected-branch",
            "main",
            "--require-clean",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["trusted"] is True
    assert payload["operation"] == "evidence"
    assert payload["risk"] == "medium"
    assert payload["branch"] == "main"
    assert payload["checks"]
