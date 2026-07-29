from __future__ import annotations

from pathlib import Path
import subprocess

from cybercore.checkpoint import collect_checkpoint
from cybercore.checkpoint_memory import (
    PROJECT_STATE_END,
    PROJECT_STATE_START,
    plan_memory_update,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_memory_plan_removes_unmarked_legacy_checkpoint(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "CyberCore Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / ".cybercore").mkdir()
    (tmp_path / ".cybercore" / "project.yaml").write_text(
        """version: 1
current:
  milestone: Verification Evidence Automation v0.1
  active_artifact: WB-0017
""",
        encoding="utf-8",
    )
    (tmp_path / "PROJECT_STATE.md").write_text(
        """# CyberCore Project State

## Current milestone

Old milestone.

## Current status

- Work block: stale

## Next action

Old action.

## Automated repository checkpoint

- Generated: `old`
- Branch: `old-branch`
- Commit: `old-commit`
- Working tree: **clean**

Human tail.
""",
        encoding="utf-8",
    )
    (tmp_path / "WORKLOG.md").write_text("# Worklog\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")

    plan = plan_memory_update(
        tmp_path,
        collect_checkpoint(tmp_path),
        test_result="46 passed",
        next_action="Prepare PR #21",
    )
    state = plan.project_state_content

    assert state.count("## Automated repository checkpoint") == 1
    assert state.count(PROJECT_STATE_START) == 1
    assert state.count(PROJECT_STATE_END) == 1
    assert "old-branch" not in state
    assert "old-commit" not in state
    assert "Human tail." in state
    assert "46 passed" in state
