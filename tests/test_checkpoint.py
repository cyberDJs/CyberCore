from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess

import pytest

from cybercore.checkpoint import CheckpointError, collect_checkpoint, render_checkpoint


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_collect_checkpoint_from_clean_repository(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "CyberCore Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / "PROJECT_STATE.md").write_text("# State\n", encoding="utf-8")
    (tmp_path / ".cybercore").mkdir()
    (tmp_path / ".cybercore" / "project.yaml").write_text("version: 1\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial checkpoint")

    checkpoint = collect_checkpoint(
        tmp_path,
        now=datetime(2026, 7, 29, 18, 0, tzinfo=timezone.utc),
    )

    assert checkpoint.branch in {"main", "master"}
    assert checkpoint.commit_subject == "initial checkpoint"
    assert checkpoint.dirty is False
    assert checkpoint.changed_paths == ()
    assert checkpoint.project_state_present is True
    assert checkpoint.project_kernel_present is True
    assert checkpoint.generated_at == "2026-07-29T18:00:00Z"


def test_collect_checkpoint_detects_dirty_paths(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "CyberCore Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / "README.md").write_text("base\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "initial")
    (tmp_path / "README.md").write_text("changed\n", encoding="utf-8")

    checkpoint = collect_checkpoint(tmp_path)

    assert checkpoint.dirty is True
    assert checkpoint.changed_paths == ("README.md",)


def test_render_checkpoint_contains_core_state(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "CyberCore Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / "README.md").write_text("base\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "initial")

    rendered = render_checkpoint(collect_checkpoint(tmp_path))

    assert "# CyberCore Repository Checkpoint" in rendered
    assert "Working tree: **clean**" in rendered
    assert "Commit subject: initial" in rendered


def test_collect_checkpoint_rejects_non_repository(tmp_path: Path) -> None:
    with pytest.raises(CheckpointError, match="Not a Git repository"):
        collect_checkpoint(tmp_path)
