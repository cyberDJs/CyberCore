from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
from typing import Any, Callable

import pytest

from cybercore.post_merge import (
    PostMergeTransitionError,
    plan_post_merge_transition,
    render_post_merge_preview,
)


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._stream = io.BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._stream.read()


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "CyberCore Tests")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "remote", "add", "origin", "https://github.com/cyberDJs/CyberCore.git")
    (repo / "README.md").write_text("# test\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")
    return repo, _git(repo, "rev-parse", "HEAD")


def _payload(merge_commit: str, *, merged: bool = True, base: str = "main") -> dict[str, object]:
    return {
        "number": 22,
        "merged": merged,
        "merge_commit_sha": merge_commit,
        "title": "feat: canonical memory",
        "base": {"ref": base},
        "head": {"ref": "feat/idempotent-canonical-memory", "sha": "head-sha"},
    }


def _branch_payload(commit: str) -> dict[str, object]:
    return {"name": "main", "commit": {"sha": commit}}


def _opener(
    pr_payload: dict[str, object],
    branch_commit: str,
) -> Callable[..., _Response]:
    def open_request(request: Any, *_args: object, **_kwargs: object) -> _Response:
        url = request.full_url
        if "/pulls/" in url:
            return _Response(pr_payload)
        if "/branches/" in url:
            return _Response(_branch_payload(branch_commit))
        raise AssertionError(f"unexpected URL: {url}")

    return open_request


def test_post_merge_preview_verifies_merged_pr_on_main(tmp_path: Path) -> None:
    repo, merge_commit = _repo(tmp_path)

    preview = plan_post_merge_transition(
        repo,
        22,
        expected_head_sha="head-sha",
        opener=_opener(_payload(merge_commit), merge_commit),
    )

    assert preview.pull_request.merge_commit == merge_commit
    assert preview.main_commit == merge_commit
    rendered = render_post_merge_preview(preview)
    assert "POST-MERGE TRANSITION PREVIEW" in rendered
    assert "Mutation: none" in rendered


def test_post_merge_preview_rejects_unmerged_pr(tmp_path: Path) -> None:
    repo, merge_commit = _repo(tmp_path)

    with pytest.raises(PostMergeTransitionError, match="is not merged"):
        plan_post_merge_transition(
            repo,
            22,
            opener=_opener(_payload(merge_commit, merged=False), merge_commit),
        )


def test_post_merge_preview_rejects_wrong_base_branch(tmp_path: Path) -> None:
    repo, merge_commit = _repo(tmp_path)

    with pytest.raises(PostMergeTransitionError, match="targets develop"):
        plan_post_merge_transition(
            repo,
            22,
            opener=_opener(_payload(merge_commit, base="develop"), merge_commit),
        )


def test_post_merge_preview_rejects_head_sha_mismatch(tmp_path: Path) -> None:
    repo, merge_commit = _repo(tmp_path)

    with pytest.raises(PostMergeTransitionError, match="head SHA mismatch"):
        plan_post_merge_transition(
            repo,
            22,
            expected_head_sha="different-sha",
            opener=_opener(_payload(merge_commit), merge_commit),
        )


def test_post_merge_preview_rejects_local_only_main_descendant(tmp_path: Path) -> None:
    repo, merge_commit = _repo(tmp_path)
    (repo / "local-only.txt").write_text("local only\n", encoding="utf-8")
    _git(repo, "add", "local-only.txt")
    _git(repo, "commit", "-m", "local-only descendant")

    with pytest.raises(PostMergeTransitionError, match="does not match GitHub main"):
        plan_post_merge_transition(
            repo,
            22,
            opener=_opener(_payload(merge_commit), merge_commit),
        )


def test_post_merge_preview_requires_clean_worktree(tmp_path: Path) -> None:
    repo, merge_commit = _repo(tmp_path)
    (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")

    with pytest.raises(PostMergeTransitionError, match="Working tree must be clean"):
        plan_post_merge_transition(
            repo,
            22,
            opener=_opener(_payload(merge_commit), merge_commit),
        )
