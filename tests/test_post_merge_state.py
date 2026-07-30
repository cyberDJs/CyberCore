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
status:
  tests: 46_passed
completed:
  - artifact: WB-0017
    pull_request: 21
    merge_commit: old
    verification: 46_passed
next:
  - old task
"""
        % active,
        encoding="utf-8",
    )
    (repo / "PROJECT_STATE.md").write_text(
        """# CyberCore Project State

- Active branch: `feat/idempotent-canonical-memory`
- Active work block: `WB-0018 Idempotent Canonical Memory`

## Completed checkpoints

## Current milestone

Idempotent Canonical Memory v0.1.

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
    assert "merge_commit: 1e174e9" in plan.kernel_content
    assert "verification: 52_passed" in plan.kernel_content
    assert "`WB-0019 Post-Merge State Transition v0.1`" in plan.project_state_content
    assert (
        "### PR #22 — feat: make canonical memory idempotent and rollback-safe"
        in plan.project_state_content
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
