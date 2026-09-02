from __future__ import annotations

from pathlib import Path

import pytest

from cybercore.post_merge import (
    MergedPullRequest,
    PostMergeTransitionError,
    PostMergeTransitionPreview,
)
from cybercore.post_merge_state import plan_post_merge_state_update


def _preview() -> PostMergeTransitionPreview:
    return PostMergeTransitionPreview(
        pull_request=MergedPullRequest(
            number=22,
            repository="cyberDJs/CyberCore",
            base_branch="main",
            head_branch="feat/idempotent-canonical-memory",
            head_sha="5f16ec7",
            merge_commit="1e174e9",
            title="feat: make canonical memory idempotent and rollback-safe",
        ),
        main_commit="1e174e9",
    )


def _repo(tmp_path: Path, *, active: str = "WB-0018") -> Path:
    repo = tmp_path / "repo"
    (repo / ".cybercore").mkdir(parents=True)
    (repo / ".cybercore" / "project.yaml").write_text(
        """version: 1
current:
  milestone: Idempotent Canonical Memory v0.1
  active_artifact: %s
  branch: feat/idempotent-canonical-memory
  pull_request: null
  last_verified_main: old-main
status:
  tests: 46_passed
completed:
  - artifact: WB-0017
    pull_request: 21
    merge_commit: old
    verification: 46_passed
next:
  - old task
rules:
  one_active_artifact: true
"""
        % active,
        encoding="utf-8",
    )
    (repo / "PROJECT_STATE.md").write_text(
        """# CyberCore Project State

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Canonical product state: GitHub `main`
- Current canonical main: `old-main`
- Current coordination artifact: WB-0018
- Current coordination branch: `feat/idempotent-canonical-memory`
- Current coordination pull request: not created
- Active branch: `feat/idempotent-canonical-memory`
- Active work block: `WB-0018 Idempotent Canonical Memory`

## Completed checkpoints

## Current milestone

Idempotent Canonical Memory v0.1.

## Active objective

Complete the active work block.

Scope:

1. preserve state;

## Current status

- Work block: active
- Branch: `feat/idempotent-canonical-memory`
- Project Kernel: present
- Runtime implementation: implemented
- Tests: 52 passed
- Pull request: not created

## Next action

Prepare PR #22

<!-- CYBERCORE:CHECKPOINT:START -->
checkpoint
<!-- CYBERCORE:CHECKPOINT:END -->
""",
        encoding="utf-8",
    )
    return repo


def test_plan_updates_kernel_and_project_state(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    plan = plan_post_merge_state_update(
        repo,
        _preview(),
        completed_artifact="WB-0018",
        verification="52_passed",
        next_artifact="WB-0019",
        next_milestone="Post-Merge State Transition v0.1",
        next_branch="feat/post-merge-state-transition",
        next_action="Implement verified post-merge transition",
    )

    assert "active_artifact: WB-0019" in plan.kernel_content
    assert "last_verified_main: 1e174e9" in plan.kernel_content
    assert "merge_commit: 1e174e9" in plan.kernel_content
    assert "verification: 52_passed" in plan.kernel_content
    assert "Canonical main ref: GitHub `main` (resolve live)" in plan.project_state_content
    assert "Last verified canonical checkpoint: `1e174e9`" in plan.project_state_content
    assert "`WB-0019 Post-Merge State Transition v0.1`" in plan.project_state_content
    assert (
        "### PR #22 — feat: make canonical memory idempotent and rollback-safe"
        in plan.project_state_content
    )


def test_terminal_plan_closes_without_successor_self_reference(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    plan = plan_post_merge_state_update(
        repo,
        _preview(),
        completed_artifact="WB-0018",
        verification="52_passed",
        next_action="Select the next bounded candidate explicitly.",
        terminal=True,
        next_tasks=("select the next bounded candidate explicitly",),
    )

    assert "active_artifact: null" in plan.kernel_content
    assert "branch: main" in plan.kernel_content
    assert "pull_request: null" in plan.kernel_content
    assert "last_verified_main: 1e174e9" in plan.kernel_content
    assert "next:\n  - select the next bounded candidate explicitly\n" in plan.kernel_content
    assert "old task" not in plan.kernel_content
    assert "Canonical main ref: GitHub `main` (resolve live)" in plan.project_state_content
    assert "Last verified canonical checkpoint: `1e174e9`" in plan.project_state_content
    assert (
        "Current coordination artifact: none — terminal canonical state"
        in plan.project_state_content
    )
    assert "- Active branch: `main`" in plan.project_state_content
    assert "- Active work block: `none`" in plan.project_state_content
    assert "- Work block: idle" in plan.project_state_content
    assert "- Pull request: none" in plan.project_state_content


def test_terminal_plan_clears_predecessor_tasks_when_none_declared(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    plan = plan_post_merge_state_update(
        repo,
        _preview(),
        completed_artifact="WB-0018",
        verification="52_passed",
        next_action="Stop with no scheduled successor task.",
        terminal=True,
    )

    assert "next: []\n" in plan.kernel_content
    assert "old task" not in plan.kernel_content


def test_terminal_plan_rejects_successor_contract(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    with pytest.raises(PostMergeTransitionError, match="cannot declare a successor"):
        plan_post_merge_state_update(
            repo,
            _preview(),
            completed_artifact="WB-0018",
            verification="52_passed",
            next_action="Stop.",
            terminal=True,
            next_artifact="WB-0019",
        )


def test_plan_rejects_active_artifact_mismatch(tmp_path: Path) -> None:
    repo = _repo(tmp_path, active="WB-0017")

    with pytest.raises(PostMergeTransitionError, match="Active artifact mismatch"):
        plan_post_merge_state_update(
            repo,
            _preview(),
            completed_artifact="WB-0018",
            verification="52_passed",
            next_artifact="WB-0019",
            next_milestone="Post-Merge State Transition v0.1",
            next_branch="feat/post-merge-state-transition",
            next_action="Implement transition",
        )


def test_write_updates_both_files(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    plan = plan_post_merge_state_update(
        repo,
        _preview(),
        completed_artifact="WB-0018",
        verification="52_passed",
        next_artifact="WB-0019",
        next_milestone="Post-Merge State Transition v0.1",
        next_branch="feat/post-merge-state-transition",
        next_action="Implement transition",
    )

    plan.write()

    assert (repo / ".cybercore" / "project.yaml").read_text(encoding="utf-8") == plan.kernel_content
    assert (repo / "PROJECT_STATE.md").read_text(encoding="utf-8") == plan.project_state_content
