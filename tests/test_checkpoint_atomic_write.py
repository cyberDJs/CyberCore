from __future__ import annotations

import os
from pathlib import Path

import pytest

import cybercore.checkpoint_memory as checkpoint_memory
from cybercore.checkpoint_memory import MemoryUpdatePlan


def _plan(tmp_path: Path) -> MemoryUpdatePlan:
    project_state = tmp_path / "PROJECT_STATE.md"
    worklog = tmp_path / "WORKLOG.md"
    project_state.write_text("old state\n", encoding="utf-8")
    worklog.write_text("old worklog\n", encoding="utf-8")
    return MemoryUpdatePlan(
        project_state_path=project_state,
        worklog_path=worklog,
        project_state_content="new state\n",
        worklog_content="new worklog\n",
    )


def test_memory_write_replaces_both_files_and_cleans_staging(tmp_path: Path) -> None:
    plan = _plan(tmp_path)

    plan.write()

    assert plan.project_state_path.read_text(encoding="utf-8") == "new state\n"
    assert plan.worklog_path.read_text(encoding="utf-8") == "new worklog\n"
    assert not list(tmp_path.glob(".*.cybercore-memory-*"))


def test_memory_write_rolls_back_first_file_when_second_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan(tmp_path)
    real_replace = os.replace
    calls = 0

    def fail_second_replace(source: str | Path, target: str | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected worklog replacement failure")
        real_replace(source, target)

    monkeypatch.setattr(checkpoint_memory.os, "replace", fail_second_replace)

    with pytest.raises(OSError, match="injected worklog replacement failure"):
        plan.write()

    assert plan.project_state_path.read_text(encoding="utf-8") == "old state\n"
    assert plan.worklog_path.read_text(encoding="utf-8") == "old worklog\n"
    assert not list(tmp_path.glob(".*.cybercore-memory-*"))
