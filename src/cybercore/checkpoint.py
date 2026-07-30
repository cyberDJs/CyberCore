from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import subprocess
from typing import Any

from cybercore.repository_identity_policy import (
    enforce_configured_repository_identity_policy,
)


class CheckpointError(RuntimeError):
    """Raised when repository checkpoint data cannot be collected."""


@dataclass(frozen=True, slots=True)
class RepositoryCheckpoint:
    generated_at: str
    repository: str
    branch: str
    commit: str
    commit_subject: str
    dirty: bool
    changed_paths: tuple[str, ...]
    project_state_present: bool
    project_kernel_present: bool

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["changed_paths"] = list(self.changed_paths)
        return payload


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise CheckpointError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout.rstrip("\r\n")


def collect_checkpoint(repo: Path, *, now: datetime | None = None) -> RepositoryCheckpoint:
    repo = repo.expanduser().resolve()
    if not (repo / ".git").exists():
        raise CheckpointError(f"Not a Git repository: {repo}")

    enforce_configured_repository_identity_policy(repo, operation="Checkpoint collection")

    branch = _git(repo, "branch", "--show-current") or "detached"
    commit = _git(repo, "rev-parse", "HEAD")
    subject = _git(repo, "log", "-1", "--pretty=%s")
    porcelain = _git(repo, "status", "--porcelain=v1")
    changed_paths = tuple(
        line[3:] for line in porcelain.splitlines() if len(line) >= 4
    )
    generated = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    return RepositoryCheckpoint(
        generated_at=generated.isoformat().replace("+00:00", "Z"),
        repository=str(repo),
        branch=branch,
        commit=commit,
        commit_subject=subject,
        dirty=bool(changed_paths),
        changed_paths=changed_paths,
        project_state_present=(repo / "PROJECT_STATE.md").is_file(),
        project_kernel_present=(repo / ".cybercore" / "project.yaml").is_file(),
    )


def render_checkpoint(checkpoint: RepositoryCheckpoint) -> str:
    cleanliness = "dirty" if checkpoint.dirty else "clean"
    lines = [
        "# CyberCore Repository Checkpoint",
        "",
        f"- Generated: `{checkpoint.generated_at}`",
        f"- Repository: `{checkpoint.repository}`",
        f"- Branch: `{checkpoint.branch}`",
        f"- Commit: `{checkpoint.commit}`",
        f"- Commit subject: {checkpoint.commit_subject}",
        f"- Working tree: **{cleanliness}**",
        f"- Project Kernel: {'present' if checkpoint.project_kernel_present else 'missing'}",
        f"- Project State: {'present' if checkpoint.project_state_present else 'missing'}",
    ]
    if checkpoint.changed_paths:
        lines.extend(["", "## Changed paths", ""])
        lines.extend(f"- `{path}`" for path in checkpoint.changed_paths)
    return "\n".join(lines) + "\n"
