from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess

from cybercore.checkpoint import collect_checkpoint
from cybercore.checkpoint_memory import (
    WORKLOG_CHECKPOINT_PREFIX,
    plan_memory_update,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "CyberCore Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / "PROJECT_STATE.md").write_text("# State\n", encoding="utf-8")
    (tmp_path / "WORKLOG.md").write_text("# CyberCore Worklog\n", encoding="utf-8")
    (tmp_path / ".cybercore").mkdir()
    (tmp_path / ".cybercore" / "project.yaml").write_text("version: 1\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    return tmp_path


def test_repeated_checkpoint_write_does_not_duplicate_worklog_entry(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    first_checkpoint = collect_checkpoint(
        repo,
        now=datetime(2026, 7, 30, 0, 0, tzinfo=timezone.utc),
    )
    first_plan = plan_memory_update(
        repo,
        first_checkpoint,
        test_result="46 passed",
        next_action="Continue WB-0018",
    )
    first_plan.write()

    second_checkpoint = collect_checkpoint(
        repo,
        now=datetime(2026, 7, 30, 1, 0, tzinfo=timezone.utc),
    )
    second_plan = plan_memory_update(
        repo,
        second_checkpoint,
        test_result="46 passed",
        next_action="Continue WB-0018",
    )
    second_plan.write()

    worklog = (repo / "WORKLOG.md").read_text(encoding="utf-8")
    assert worklog.count(WORKLOG_CHECKPOINT_PREFIX) == 1
    assert worklog.count("## Checkpoint ") == 1
    assert "2026-07-30T00:00:00Z" in worklog
    assert "2026-07-30T01:00:00Z" not in worklog


def test_changed_evidence_summary_creates_distinct_worklog_entry(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)

    first = plan_memory_update(repo, checkpoint, test_result="46 passed")
    first.write()
    second = plan_memory_update(repo, checkpoint, test_result="47 passed")
    second.write()

    worklog = (repo / "WORKLOG.md").read_text(encoding="utf-8")
    assert worklog.count(WORKLOG_CHECKPOINT_PREFIX) == 2
    assert "46 passed" in worklog
    assert "47 passed" in worklog
