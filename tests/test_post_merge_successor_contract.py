from __future__ import annotations

from pathlib import Path

from cybercore.post_merge import MergedPullRequest, PostMergeTransitionPreview
from cybercore.post_merge_state import plan_post_merge_state_update


def test_successor_contract_replaces_predecessor_state(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".cybercore").mkdir(parents=True)
    (repo / ".cybercore" / "project.yaml").write_text(
        """version: 1
current:
  milestone: Post-Merge State Transition v0.1
  active_artifact: WB-0019
  branch: feat/post-merge-state-transition
  pull_request: null
status:
  tests: 66_passed
  post_merge_state_transition: planned
completed:
  - artifact: WB-0018
    pull_request: 22
    merge_commit: old
    verification: 52_passed
next:
  - define an explicit post-merge state transition command
rules:
  one_active_artifact: true
""",
        encoding="utf-8",
    )
    (repo / "PROJECT_STATE.md").write_text(
        """# CyberCore Project State

- Last verified canonical checkpoint: `old-main`
- Active branch: `feat/post-merge-state-transition`
- Active work block: `WB-0019 Post-Merge State Transition`

## Completed checkpoints

## Current milestone

Post-Merge State Transition v0.1.

## Active objective

Create a controlled transition that closes a merged work block.

Scope:

1. define an explicit post-merge state transition command;
2. verify merged pull requests;

## Current status

- Work block: active
- Branch: `feat/post-merge-state-transition`
- Project Kernel: present
- Runtime implementation: implemented
- Tests: 66 passed
- Pull request: not created

## Next action

Prepare PR #23

<!-- CYBERCORE:CHECKPOINT:START -->
checkpoint
<!-- CYBERCORE:CHECKPOINT:END -->
""",
        encoding="utf-8",
    )
    preview = PostMergeTransitionPreview(
        pull_request=MergedPullRequest(
            number=23,
            repository="cyberDJs/CyberCore",
            base_branch="main",
            head_branch="feat/post-merge-state-transition",
            head_sha="81cd9f9",
            merge_commit="ca2da8b",
            title="feat: add controlled post-merge state transitions",
        ),
        main_commit="ca2da8b",
    )

    plan = plan_post_merge_state_update(
        repo,
        preview,
        completed_artifact="WB-0019",
        verification="66_passed",
        next_artifact="WB-0020",
        next_milestone="Remote-Aware Repository Identity v0.1",
        next_branch="feat/remote-aware-repository-identity",
        next_action="Define remote identity normalization contract and tests.",
        completed_status="post_merge_state_transition",
        next_status="remote_aware_repository_identity",
        next_objective=(
            "Make repository identity stable across clone locations by preferring a "
            "normalized Git remote identity."
        ),
        next_scope=(
            "normalize HTTPS and SSH Git remote URLs",
            "use remote identity for checkpoint hashes",
            "preserve a local fallback for repositories without a remote",
        ),
        next_tasks=(
            "define remote identity normalization contract",
            "add cross-clone identity regression tests",
        ),
    )

    assert "post_merge_state_transition: verified" in plan.kernel_content
    assert "remote_aware_repository_identity: planned" in plan.kernel_content
    assert "define remote identity normalization contract" in plan.kernel_content
    assert "define an explicit post-merge state transition command" not in plan.kernel_content

    assert "Last verified canonical checkpoint: `ca2da8b`" in plan.project_state_content
    assert "Make repository identity stable across clone locations" in plan.project_state_content
    assert "normalize HTTPS and SSH Git remote URLs" in plan.project_state_content
    assert (
        "Create a controlled transition that closes a merged work block"
        not in plan.project_state_content
    )
    assert "- Tests: 66 passed" in plan.project_state_content
