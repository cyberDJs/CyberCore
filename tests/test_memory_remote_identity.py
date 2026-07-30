from __future__ import annotations

import hashlib
from pathlib import Path
import re
import subprocess

from cybercore.checkpoint import RepositoryCheckpoint
from cybercore.memory import (
    PROJECT_STATE_CHECKPOINT_PREFIX,
    WORKLOG_CHECKPOINT_PREFIX,
    plan_memory_update,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _repo(tmp_path: Path, name: str, remote: str) -> Path:
    repo = tmp_path / name
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "remote", "add", "origin", remote)
    (repo / ".cybercore").mkdir()
    (repo / ".cybercore" / "project.yaml").write_text(
        """version: 1
current:
  milestone: Remote-Aware Repository Identity v0.1
  active_artifact: WB-0020
  branch: feat/remote-aware-repository-identity
  pull_request: null
""",
        encoding="utf-8",
    )
    (repo / "PROJECT_STATE.md").write_text(
        """# CyberCore Project State

- Active branch: `old`
- Active work block: `WB-0020 Remote-Aware Repository Identity`

## Current milestone

Old milestone.

## Current status

- Work block: active

## Next action

Continue.
""",
        encoding="utf-8",
    )
    (repo / "WORKLOG.md").write_text("# CyberCore Worklog\n", encoding="utf-8")
    return repo


def _checkpoint(repo: Path) -> RepositoryCheckpoint:
    return RepositoryCheckpoint(
        generated_at="2026-07-30T04:00:00Z",
        repository=str(repo),
        branch="feat/remote-aware-repository-identity",
        commit="same-commit",
        commit_subject="test checkpoint",
        dirty=False,
        changed_paths=(),
        project_state_present=True,
        project_kernel_present=True,
    )


def _marker(content: str, prefix: str) -> str:
    match = re.search(rf"{re.escape(prefix)}([0-9a-f]{{64}})", content)
    assert match is not None
    return match.group(1)


def test_checkpoint_identity_is_equal_across_clone_paths(tmp_path: Path) -> None:
    first = _repo(tmp_path, "first", "https://github.com/cyberDJs/CyberCore.git")
    second = _repo(tmp_path, "second", "git@github.com:cyberDJs/CyberCore.git")

    first_plan = plan_memory_update(first, _checkpoint(first), test_result="76 passed")
    second_plan = plan_memory_update(second, _checkpoint(second), test_result="76 passed")

    assert _marker(first_plan.project_state_content, PROJECT_STATE_CHECKPOINT_PREFIX) == _marker(
        second_plan.project_state_content,
        PROJECT_STATE_CHECKPOINT_PREFIX,
    )
    assert _marker(first_plan.worklog_content, WORKLOG_CHECKPOINT_PREFIX) == _marker(
        second_plan.worklog_content,
        WORKLOG_CHECKPOINT_PREFIX,
    )


def test_legacy_path_markers_are_migrated_without_duplicate_entries(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "legacy", "https://github.com/cyberDJs/CyberCore.git")
    checkpoint = _checkpoint(repo)
    legacy_canonical = "\0".join(
        [str(repo.resolve()), checkpoint.commit, "76 passed"]
    )
    legacy_identity = hashlib.sha256(legacy_canonical.encode("utf-8")).hexdigest()

    (repo / "PROJECT_STATE.md").write_text(
        (repo / "PROJECT_STATE.md").read_text(encoding="utf-8")
        + "\n<!-- CYBERCORE:CHECKPOINT:START -->\n"
        + f"<!-- {PROJECT_STATE_CHECKPOINT_PREFIX}{legacy_identity} -->\n"
        + "## Automated repository checkpoint\n\n"
        + "- Generated: `legacy`\n"
        + "<!-- CYBERCORE:CHECKPOINT:END -->\n",
        encoding="utf-8",
    )
    (repo / "WORKLOG.md").write_text(
        "# CyberCore Worklog\n\n"
        + f"<!-- {WORKLOG_CHECKPOINT_PREFIX}{legacy_identity} -->\n"
        + "## Checkpoint legacy\n",
        encoding="utf-8",
    )

    plan = plan_memory_update(repo, checkpoint, test_result="76 passed")

    assert legacy_identity not in plan.project_state_content
    assert legacy_identity not in plan.worklog_content
    assert plan.project_state_content.count(PROJECT_STATE_CHECKPOINT_PREFIX) == 1
    assert plan.worklog_content.count(WORKLOG_CHECKPOINT_PREFIX) == 1
    assert plan.worklog_content.count("## Checkpoint") == 1


def test_memory_module_checkpoint_subjects_are_sanitized(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "sanitized", "https://github.com/cyberDJs/CyberCore.git")
    checkpoint = _checkpoint(repo)
    checkpoint = RepositoryCheckpoint(
        generated_at=checkpoint.generated_at,
        repository=checkpoint.repository,
        branch=checkpoint.branch,
        commit=checkpoint.commit,
        commit_subject=(
            "Fix /Users/Jan/private-repo from "
            "https://user:password@example.test/repo?token=tokensecret123"
        ),
        dirty=checkpoint.dirty,
        changed_paths=checkpoint.changed_paths,
        project_state_present=checkpoint.project_state_present,
        project_kernel_present=checkpoint.project_kernel_present,
    )

    plan = plan_memory_update(repo, checkpoint, test_result="76 passed")

    assert "/Users/Jan/private-repo" not in plan.project_state_content
    assert "/Users/Jan/private-repo" not in plan.worklog_content
    assert "user:password" not in plan.project_state_content
    assert "user:password" not in plan.worklog_content
    assert "tokensecret123" not in plan.project_state_content
    assert "tokensecret123" not in plan.worklog_content
