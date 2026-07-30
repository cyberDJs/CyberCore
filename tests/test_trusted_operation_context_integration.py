from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from cybercore.checkpoint import CheckpointError, collect_checkpoint
from cybercore.trusted_operation_context import (
    TrustedOperationContextError,
    collect_trusted_operation_context,
    enforce_trusted_operation_context,
)


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repo(tmp_path: Path, *, canonical: bool = True) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "feature")
    _git(repo, "config", "user.name", "CyberCore Test")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / ".cybercore").mkdir()
    identity = "  repository: git:github.com/cyberDJs/CyberCore\n" if canonical else ""
    (repo / ".cybercore" / "project.yaml").write_text(
        "version: 1\nidentity:\n  name: CyberCore\n" + identity,
        encoding="utf-8",
    )
    (repo / "PROJECT_STATE.md").write_text("# State\n", encoding="utf-8")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "seed")
    if canonical:
        _git(repo, "remote", "add", "origin", "https://github.com/cyberDJs/CyberCore.git")
    return repo


def test_enforcement_rejects_dirty_tree(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")

    with pytest.raises(TrustedOperationContextError, match="clean_working_tree"):
        enforce_trusted_operation_context(
            repo,
            operation="apply",
            risk="critical",
            expected_branch="feature",
            require_clean=True,
        )


def test_enforcement_rejects_branch_mismatch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    with pytest.raises(TrustedOperationContextError, match="expected_branch"):
        enforce_trusted_operation_context(
            repo,
            operation="apply",
            risk="critical",
            expected_branch="main",
            require_clean=True,
        )


def test_legacy_project_remains_collectable(tmp_path: Path) -> None:
    repo = _repo(tmp_path, canonical=False)

    context = collect_trusted_operation_context(repo)

    assert context.trusted is True
    assert any(check.name == "repository_identity" for check in context.checks)


def test_checkpoint_preserves_domain_error(tmp_path: Path) -> None:
    with pytest.raises(CheckpointError, match="Not a Git repository"):
        collect_checkpoint(tmp_path)
