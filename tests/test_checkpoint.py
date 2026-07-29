from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess

import pytest

from cybercore.checkpoint import CheckpointError, collect_checkpoint, render_checkpoint
from cybercore.checkpoint_memory import (
    PROJECT_STATE_START,
    plan_memory_update,
    render_memory_preview,
)
from cybercore.cli import main


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "CyberCore Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / "PROJECT_STATE.md").write_text("# State\n\nHuman section.\n", encoding="utf-8")
    (tmp_path / "WORKLOG.md").write_text("# CyberCore Worklog\n", encoding="utf-8")
    (tmp_path / ".cybercore").mkdir()
    (tmp_path / ".cybercore" / "project.yaml").write_text("version: 1\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial checkpoint")
    return tmp_path


def test_collect_checkpoint_from_clean_repository(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    checkpoint = collect_checkpoint(
        repo,
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
    repo = _repo(tmp_path)

    rendered = render_checkpoint(collect_checkpoint(repo))

    assert "# CyberCore Repository Checkpoint" in rendered
    assert "Working tree: **clean**" in rendered
    assert "Commit subject: initial checkpoint" in rendered


def test_collect_checkpoint_rejects_non_repository(tmp_path: Path) -> None:
    with pytest.raises(CheckpointError, match="Not a Git repository"):
        collect_checkpoint(tmp_path)


def test_memory_plan_preserves_human_content_and_previews(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(
        repo,
        now=datetime(2026, 7, 29, 19, 0, tzinfo=timezone.utc),
    )

    plan = plan_memory_update(
        repo,
        checkpoint,
        test_result="18 passed in 3.23s",
        next_action="Open PR",
    )
    preview = render_memory_preview(plan)

    assert "Human section." in plan.project_state_content
    assert PROJECT_STATE_START in plan.project_state_content
    assert "18 passed in 3.23s" in preview
    assert "Next action: Open PR" in preview
    assert (repo / "PROJECT_STATE.md").read_text(encoding="utf-8") == "# State\n\nHuman section.\n"


def test_memory_plan_write_updates_both_files(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    plan = plan_memory_update(repo, checkpoint, test_result="22 passed")

    plan.write()

    assert PROJECT_STATE_START in (repo / "PROJECT_STATE.md").read_text(encoding="utf-8")
    assert "22 passed" in (repo / "WORKLOG.md").read_text(encoding="utf-8")


def test_memory_managed_block_is_replaced_not_duplicated(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    first = plan_memory_update(repo, collect_checkpoint(repo), test_result="first")
    first.write()
    second = plan_memory_update(repo, collect_checkpoint(repo), test_result="second")
    second.write()

    state = (repo / "PROJECT_STATE.md").read_text(encoding="utf-8")
    assert state.count(PROJECT_STATE_START) == 1
    assert "second" in state
    assert "first" not in state


def test_cli_write_requires_memory(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo(tmp_path)

    rc = main(["--repo", str(repo), "checkpoint", "--write"])

    assert rc == 2
    assert "--write requires --memory" in capsys.readouterr().err
