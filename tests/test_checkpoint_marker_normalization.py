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


def _repo(tmp_path: Path, state: str) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "CyberCore Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / "PROJECT_STATE.md").write_text(state, encoding="utf-8")
    (tmp_path / "WORKLOG.md").write_text("# CyberCore Worklog\n", encoding="utf-8")
    (tmp_path / ".cybercore").mkdir()
    (tmp_path / ".cybercore" / "project.yaml").write_text("version: 1\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    return tmp_path


def test_memory_plan_removes_orphan_end_marker(tmp_path: Path) -> None:
    repo = _repo(
        tmp_path,
        "# State\n\nHuman section.\n\n"
        + PROJECT_STATE_END
        + "\n\nLegacy content.\n",
    )

    plan = plan_memory_update(repo, collect_checkpoint(repo), test_result="44 passed")

    assert plan.project_state_content.count(PROJECT_STATE_START) == 1
    assert plan.project_state_content.count(PROJECT_STATE_END) == 1
    assert "Human section." in plan.project_state_content
    assert "Legacy content." in plan.project_state_content


def test_memory_plan_collapses_multiple_complete_blocks(tmp_path: Path) -> None:
    old_block = (
        PROJECT_STATE_START
        + "\n## Automated repository checkpoint\n\n- Test evidence: `old`\n"
        + PROJECT_STATE_END
    )
    repo = _repo(tmp_path, f"# State\n\n{old_block}\n\n{old_block}\n")

    plan = plan_memory_update(repo, collect_checkpoint(repo), test_result="44 passed")

    assert plan.project_state_content.count(PROJECT_STATE_START) == 1
    assert plan.project_state_content.count(PROJECT_STATE_END) == 1
    assert "44 passed" in plan.project_state_content
    assert "`old`" not in plan.project_state_content
