from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cybercore.checkpoint import RepositoryCheckpoint


PROJECT_STATE_START = "<!-- CYBERCORE:CHECKPOINT:START -->"
PROJECT_STATE_END = "<!-- CYBERCORE:CHECKPOINT:END -->"


@dataclass(frozen=True, slots=True)
class MemoryUpdatePlan:
    project_state_path: Path
    worklog_path: Path
    project_state_content: str
    worklog_content: str

    def write(self) -> None:
        self.project_state_path.write_text(self.project_state_content, encoding="utf-8")
        self.worklog_path.write_text(self.worklog_content, encoding="utf-8")


def _checkpoint_block(checkpoint: RepositoryCheckpoint, test_result: str | None) -> str:
    test_line = test_result or "not supplied"
    cleanliness = "dirty" if checkpoint.dirty else "clean"
    return "\n".join(
        [
            PROJECT_STATE_START,
            "## Automated repository checkpoint",
            "",
            f"- Generated: `{checkpoint.generated_at}`",
            f"- Branch: `{checkpoint.branch}`",
            f"- Commit: `{checkpoint.commit}`",
            f"- Commit subject: {checkpoint.commit_subject}",
            f"- Working tree: **{cleanliness}**",
            f"- Test evidence: `{test_line}`",
            f"- Project Kernel: {'present' if checkpoint.project_kernel_present else 'missing'}",
            f"- Project State: {'present' if checkpoint.project_state_present else 'missing'}",
            PROJECT_STATE_END,
        ]
    )


def _replace_managed_block(current: str, block: str) -> str:
    if PROJECT_STATE_START not in current or PROJECT_STATE_END not in current:
        return current.rstrip() + "\n\n" + block + "\n"
    start = current.index(PROJECT_STATE_START)
    end = current.index(PROJECT_STATE_END, start) + len(PROJECT_STATE_END)
    return current[:start].rstrip() + "\n\n" + block + "\n" + current[end:].lstrip("\n")


def _worklog_entry(
    checkpoint: RepositoryCheckpoint,
    test_result: str | None,
    next_action: str | None,
) -> str:
    lines = [
        f"## Checkpoint {checkpoint.generated_at}",
        "",
        f"- Branch: `{checkpoint.branch}`",
        f"- Commit: `{checkpoint.commit}`",
        f"- Commit subject: {checkpoint.commit_subject}",
        f"- Working tree: **{'dirty' if checkpoint.dirty else 'clean'}**",
        f"- Test evidence: `{test_result or 'not supplied'}`",
    ]
    if next_action:
        lines.append(f"- Next action: {next_action}")
    return "\n".join(lines) + "\n"


def plan_memory_update(
    repo: Path,
    checkpoint: RepositoryCheckpoint,
    *,
    test_result: str | None = None,
    next_action: str | None = None,
) -> MemoryUpdatePlan:
    project_state_path = repo / "PROJECT_STATE.md"
    worklog_path = repo / "WORKLOG.md"
    if not project_state_path.is_file():
        raise FileNotFoundError(f"Project State not found: {project_state_path}")

    current_state = project_state_path.read_text(encoding="utf-8")
    current_worklog = (
        worklog_path.read_text(encoding="utf-8")
        if worklog_path.is_file()
        else "# CyberCore Worklog\n"
    )
    block = _checkpoint_block(checkpoint, test_result)
    state_content = _replace_managed_block(current_state, block)
    entry = _worklog_entry(checkpoint, test_result, next_action)
    worklog_content = current_worklog.rstrip() + "\n\n" + entry

    return MemoryUpdatePlan(
        project_state_path=project_state_path,
        worklog_path=worklog_path,
        project_state_content=state_content,
        worklog_content=worklog_content,
    )


def render_memory_preview(plan: MemoryUpdatePlan) -> str:
    return (
        "=== PROJECT_STATE.md ===\n"
        + plan.project_state_content
        + "\n=== WORKLOG.md ===\n"
        + plan.worklog_content
    )
