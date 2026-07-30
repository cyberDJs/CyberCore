from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import subprocess
from typing import Any

from cybercore.trusted_operation_context import enforce_trusted_operation_context


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
    context = enforce_trusted_operation_context(
        repo,
        operation="checkpoint",
        risk="low",
    )

    subject = _git(repo, "log", "-1", "--pretty=%s")
    porcelain = _git(repo, "status", "--porcelain=v1")
    changed_paths = tuple(
        line[3:] for line in porcelain.splitlines() if len(line) >= 4
    )
    generated = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    return RepositoryCheckpoint(
        generated_at=generated.isoformat().replace("+00:00", "Z"),
        repository=context.repository,
        branch=context.branch,
        commit=context.commit,
        commit_subject=subject,
        dirty=context.dirty,
        changed_paths=changed_paths,
        project_state_present=context.project_state_present,
        project_kernel_present=context.project_kernel_present,
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
