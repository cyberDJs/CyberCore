from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from cybercore.post_merge import (
    MergedPullRequest,
    PostMergeTransitionError,
    PostMergeTransitionPreview,
)
from cybercore.post_merge_state import plan_post_merge_state_update


def _preview(*, base_branch: str = "main") -> PostMergeTransitionPreview:
    return PostMergeTransitionPreview(
        pull_request=MergedPullRequest(
            number=22,
            repository="cyberDJs/CyberCore",
            base_branch=base_branch,
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
    assert 'verification: "52_passed"' in plan.kernel_content
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
    assert 'next:\n  - "select the next bounded candidate explicitly"\n' in plan.kernel_content
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


def test_terminal_plan_records_completion_when_next_list_is_already_empty(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    kernel_path = repo / ".cybercore" / "project.yaml"
    kernel_path.write_text(
        kernel_path.read_text(encoding="utf-8").replace(
            "next:\n  - old task\n",
            "next: []\n",
        ),
        encoding="utf-8",
    )

    plan = plan_post_merge_state_update(
        repo,
        _preview(),
        completed_artifact="WB-0018",
        verification="52_passed",
        next_action="Stop with no scheduled successor task.",
        terminal=True,
    )

    assert "  - artifact: WB-0018\n" in plan.kernel_content
    assert "    pull_request: 22\n" in plan.kernel_content
    assert "    merge_commit: 1e174e9\n" in plan.kernel_content
    assert '    verification: "52_passed"\n' in plan.kernel_content
    assert "next: []\n" in plan.kernel_content


def test_plan_inserts_missing_kernel_checkpoint_on_own_line(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    kernel_path = repo / ".cybercore" / "project.yaml"
    kernel_path.write_text(
        kernel_path.read_text(encoding="utf-8").replace("  last_verified_main: old-main\n", ""),
        encoding="utf-8",
    )

    plan = plan_post_merge_state_update(
        repo,
        _preview(),
        completed_artifact="WB-0018",
        verification="52_passed",
        next_action="Stop with no scheduled successor task.",
        terminal=True,
    )

    assert "  pull_request: null\n  last_verified_main: 1e174e9\nstatus:\n" in plan.kernel_content
    assert "pull_request: null  last_verified_main" not in plan.kernel_content


def test_terminal_plan_quotes_kernel_strings_with_yaml_syntax(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    plan = plan_post_merge_state_update(
        repo,
        _preview(),
        completed_artifact="WB-0018",
        verification="CI #680: PASS",
        next_action="Stop with a quoted terminal task.",
        terminal=True,
        next_tasks=("repair: protocol mismatch",),
    )

    kernel = yaml.safe_load(plan.kernel_content)
    assert kernel["current"]["milestone"] == "Canonical checkpoint after PR #22"
    assert kernel["status"]["tests"] == "CI #680: PASS"
    assert kernel["completed"][1]["verification"] == "CI #680: PASS"
    assert kernel["next"] == ["repair: protocol mismatch"]
    assert 'milestone: "Canonical checkpoint after PR #22"' in plan.kernel_content
    assert 'verification: "CI #680: PASS"' in plan.kernel_content
    assert '  - "repair: protocol mismatch"' in plan.kernel_content


def test_terminal_plan_preserves_backslashes_in_verification_scalars(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    verification = "C:\\temp\\ci #681: PASS"

    plan = plan_post_merge_state_update(
        repo,
        _preview(),
        completed_artifact="WB-0018",
        verification=verification,
        next_action="Stop with a path-sensitive verification.",
        terminal=True,
    )

    kernel = yaml.safe_load(plan.kernel_content)
    assert kernel["status"]["tests"] == verification
    assert kernel["completed"][1]["verification"] == verification


def test_terminal_plan_preserves_backslashes_in_task_scalars(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    task = "repair\\path"

    plan = plan_post_merge_state_update(
        repo,
        _preview(),
        completed_artifact="WB-0018",
        verification="52_passed",
        next_action="Stop with a path-sensitive terminal task.",
        terminal=True,
        next_tasks=(task,),
    )

    kernel = yaml.safe_load(plan.kernel_content)
    assert kernel["next"] == [task]


def test_project_state_next_action_is_literal_replacement_text(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    next_action = r"1. repair the canonical findings \ now"

    plan = plan_post_merge_state_update(
        repo,
        _preview(),
        completed_artifact="WB-0018",
        verification="52_passed",
        next_action=next_action,
        terminal=True,
    )

    assert f"## Next action\n\n{next_action}\n" in plan.project_state_content


def test_terminal_objective_uses_selected_stable_branch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    plan = plan_post_merge_state_update(
        repo,
        _preview(base_branch="release/candidate"),
        completed_artifact="WB-0018",
        verification="52_passed",
        next_action="Stop on selected stable branch.",
        terminal=True,
    )

    assert "branch: release/candidate" in plan.kernel_content
    assert "- Active branch: `release/candidate`" in plan.project_state_content
    assert "live canonical `release/candidate`" in plan.project_state_content
    assert "live canonical `main`" not in plan.project_state_content


def test_terminal_plan_rejects_empty_public_boundary_values(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    with pytest.raises(PostMergeTransitionError, match="verification must be non-empty"):
        plan_post_merge_state_update(
            repo,
            _preview(),
            completed_artifact="WB-0018",
            verification="   ",
            next_action="Stop.",
            terminal=True,
        )

    with pytest.raises(PostMergeTransitionError, match="next action must be non-empty"):
        plan_post_merge_state_update(
            repo,
            _preview(),
            completed_artifact="WB-0018",
            verification="52_passed",
            next_action="",
            terminal=True,
        )

    with pytest.raises(PostMergeTransitionError, match="next tasks must not contain empty"):
        plan_post_merge_state_update(
            repo,
            _preview(),
            completed_artifact="WB-0018",
            verification="52_passed",
            next_action="Stop.",
            terminal=True,
            next_tasks=("valid task", "  "),
        )


def test_plan_fails_when_project_state_checkpoint_literal_is_absent(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    project_state_path = repo / "PROJECT_STATE.md"
    project_state_path.write_text(
        project_state_path.read_text(encoding="utf-8").replace(
            "- Current canonical main: `old-main`\n",
            "",
        ),
        encoding="utf-8",
    )

    with pytest.raises(PostMergeTransitionError, match="Project State checkpoint"):
        plan_post_merge_state_update(
            repo,
            _preview(),
            completed_artifact="WB-0018",
            verification="52_passed",
            next_action="Stop with no scheduled successor task.",
            terminal=True,
        )


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
