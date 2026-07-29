from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess

from cybercore.checkpoint import collect_checkpoint
from cybercore.checkpoint_memory import plan_memory_update


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "CyberCore Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / ".cybercore").mkdir()
    (tmp_path / ".cybercore" / "project.yaml").write_text(
        """version: 1
current:
  milestone: Idempotent Canonical Memory v0.1
  active_artifact: WB-0018
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
""",
        encoding="utf-8",
    )
    (tmp_path / "WORKLOG.md").write_text("# CyberCore Worklog\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    return tmp_path


def test_repeated_plan_converges_for_same_checkpoint_identity(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    first_time = datetime(2026, 7, 30, 0, 0, tzinfo=timezone.utc)
    second_time = first_time + timedelta(minutes=5)

    first = plan_memory_update(
        repo,
        collect_checkpoint(repo, now=first_time),
        test_result="50 passed",
        next_action="Prepare PR #22",
    )
    first.write()

    second = plan_memory_update(
        repo,
        collect_checkpoint(repo, now=second_time),
        test_result="50 passed",
        next_action="Prepare PR #22",
    )

    assert second.project_state_content == first.project_state_content
    assert second.worklog_content == first.worklog_content


def test_changed_evidence_creates_new_canonical_checkpoint(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(
        repo,
        now=datetime(2026, 7, 30, 0, 0, tzinfo=timezone.utc),
    )

    first = plan_memory_update(repo, checkpoint, test_result="50 passed")
    first.write()
    second = plan_memory_update(repo, checkpoint, test_result="51 passed")

    assert second.project_state_content != first.project_state_content
    assert second.worklog_content.count("CYBERCORE:WORKLOG-CHECKPOINT:") == 2
    assert "51 passed" in second.project_state_content
