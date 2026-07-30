from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Any, Callable
from urllib.request import Request, urlopen

from cybercore.repository_identity_policy import (
    enforce_configured_repository_identity_policy,
)


class PostMergeTransitionError(RuntimeError):
    """Raised when a post-merge transition cannot be verified safely."""


@dataclass(frozen=True, slots=True)
class MergedPullRequest:
    number: int
    repository: str
    base_branch: str
    head_branch: str
    head_sha: str
    merge_commit: str
    title: str


@dataclass(frozen=True, slots=True)
class PostMergeTransitionPreview:
    pull_request: MergedPullRequest
    main_commit: str


def _run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "git command failed"
        raise PostMergeTransitionError(detail)
    return completed.stdout.strip()


def _repository_slug(repo: Path) -> str:
    remote = _run_git(repo, "remote", "get-url", "origin")
    normalized = remote.removesuffix(".git")
    if normalized.startswith("git@github.com:"):
        return normalized.split(":", 1)[1]
    marker = "github.com/"
    if marker in normalized:
        return normalized.split(marker, 1)[1]
    raise PostMergeTransitionError("Origin is not a supported GitHub repository")


def _fetch_pull_request(
    repository: str,
    number: int,
    *,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    request = Request(
        f"https://api.github.com/repos/{repository}/pulls/{number}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "CyberCore"},
    )
    try:
        with opener(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise PostMergeTransitionError(f"Unable to read GitHub PR #{number}: {exc}") from exc
    if not isinstance(payload, dict):
        raise PostMergeTransitionError("GitHub returned an invalid pull-request payload")
    return payload


def _require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise PostMergeTransitionError(f"GitHub PR payload is missing {key}")
    return value


def plan_post_merge_transition(
    repo: Path,
    pull_request_number: int,
    *,
    stable_branch: str = "main",
    expected_head_sha: str | None = None,
    opener: Callable[..., Any] = urlopen,
) -> PostMergeTransitionPreview:
    repo = repo.resolve()
    if not (repo / ".git").exists():
        raise PostMergeTransitionError(f"Not a Git repository: {repo}")

    enforce_configured_repository_identity_policy(
        repo,
        operation="Post-merge transition",
    )

    if _run_git(repo, "status", "--porcelain"):
        raise PostMergeTransitionError("Working tree must be clean")

    repository = _repository_slug(repo)
    payload = _fetch_pull_request(repository, pull_request_number, opener=opener)
    if payload.get("merged") is not True:
        raise PostMergeTransitionError(f"PR #{pull_request_number} is not merged")

    base = payload.get("base")
    head = payload.get("head")
    if not isinstance(base, dict) or not isinstance(head, dict):
        raise PostMergeTransitionError("GitHub PR payload is missing base or head metadata")
    base_branch = _require_string(base, "ref")
    head_branch = _require_string(head, "ref")
    head_sha = _require_string(head, "sha")
    merge_commit = _require_string(payload, "merge_commit_sha")
    title = _require_string(payload, "title")

    if base_branch != stable_branch:
        raise PostMergeTransitionError(
            f"PR #{pull_request_number} targets {base_branch}, expected {stable_branch}"
        )
    if expected_head_sha is not None and head_sha != expected_head_sha:
        raise PostMergeTransitionError(
            f"PR #{pull_request_number} head SHA mismatch: {head_sha} != {expected_head_sha}"
        )

    _run_git(repo, "cat-file", "-e", f"{merge_commit}^{{commit}}")
    ancestor = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", merge_commit, stable_branch],
        check=False,
        capture_output=True,
        text=True,
    )
    if ancestor.returncode != 0:
        raise PostMergeTransitionError(
            f"Merge commit {merge_commit} is not contained in {stable_branch}"
        )
    main_commit = _run_git(repo, "rev-parse", stable_branch)

    return PostMergeTransitionPreview(
        pull_request=MergedPullRequest(
            number=pull_request_number,
            repository=repository,
            base_branch=base_branch,
            head_branch=head_branch,
            head_sha=head_sha,
            merge_commit=merge_commit,
            title=title,
        ),
        main_commit=main_commit,
    )


def render_post_merge_preview(preview: PostMergeTransitionPreview) -> str:
    pull_request = preview.pull_request
    return "\n".join(
        [
            "POST-MERGE TRANSITION PREVIEW",
            f"Repository: {pull_request.repository}",
            f"Pull request: #{pull_request.number} — {pull_request.title}",
            f"Base branch: {pull_request.base_branch}",
            f"Head branch: {pull_request.head_branch}",
            f"Head SHA: {pull_request.head_sha}",
            f"Merge commit: {pull_request.merge_commit}",
            f"Current {pull_request.base_branch}: {preview.main_commit}",
            "Mutation: none",
            "",
        ]
    )
