from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import tempfile

from cybercore.checkpoint import RepositoryCheckpoint


PROJECT_STATE_START = "<!-- CYBERCORE:CHECKPOINT:START -->"
PROJECT_STATE_END = "<!-- CYBERCORE:CHECKPOINT:END -->"
PROJECT_STATE_CHECKPOINT_PREFIX = "CYBERCORE:PROJECT-STATE-CHECKPOINT:"
WORKLOG_CHECKPOINT_PREFIX = "CYBERCORE:WORKLOG-CHECKPOINT:"


@dataclass(frozen=True, slots=True)
class MemoryUpdatePlan:
    project_state_path: Path
    worklog_path: Path
    project_state_content: str
    worklog_content: str

    def write(self) -> None:
        targets = (
            (self.project_state_path, self.project_state_content),
            (self.worklog_path, self.worklog_content),
        )
        staged_updates: dict[Path, Path] = {}
        staged_rollbacks: dict[Path, Path | None] = {}
        replaced: list[Path] = []

        try:
            for target, content in targets:
                target.parent.mkdir(parents=True, exist_ok=True)
                staged_updates[target] = _stage_bytes(
                    target,
                    content.encode("utf-8"),
                    suffix=".new",
                )
                staged_rollbacks[target] = (
                    _stage_bytes(target, target.read_bytes(), suffix=".rollback")
                    if target.exists()
                    else None
                )

            for target, _content in targets:
                os.replace(staged_updates[target], target)
                replaced.append(target)
        except Exception:
            rollback_error: Exception | None = None
            for target in reversed(replaced):
                rollback = staged_rollbacks[target]
                try:
                    if rollback is None:
                        target.unlink(missing_ok=True)
                    else:
                        os.replace(rollback, target)
                except Exception as exc:  # pragma: no cover - catastrophic filesystem failure
                    rollback_error = rollback_error or exc
            if rollback_error is not None:
                raise RuntimeError(
                    "Canonical memory write failed and rollback was incomplete"
                ) from rollback_error
            raise
        finally:
            for staged in (*staged_updates.values(), *staged_rollbacks.values()):
                if staged is not None:
                    staged.unlink(missing_ok=True)


def _stage_bytes(target: Path, content: bytes, *, suffix: str) -> Path:
    descriptor, raw_path = tempfile.mkstemp(
        prefix=f".{target.name}.cybercore-memory-",
        suffix=suffix,
        dir=target.parent,
    )
    staged = Path(raw_path)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        staged.unlink(missing_ok=True)
        raise
    return staged


def _project_state_marker(identity: str) -> str:
    return f"<!-- {PROJECT_STATE_CHECKPOINT_PREFIX}{identity} -->"


def _checkpoint_block(
    checkpoint: RepositoryCheckpoint,
    test_result: str | None,
    *,
    identity: str,
) -> str:
    test_line = test_result or "not supplied"
    cleanliness = "dirty" if checkpoint.dirty else "clean"
    return "\n".join(
        [
            PROJECT_STATE_START,
            _project_state_marker(identity),
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


def _remove_legacy_checkpoint_blocks(current: str) -> str:
    """Remove legacy generated checkpoint fields without consuming human prose."""
    generated_prefixes = (
        "- Generated:",
        "- Branch:",
        "- Commit:",
        "- Commit subject:",
        "- Working tree:",
        "- Test evidence:",
        "- Project Kernel:",
        "- Project State:",
    )
    lines = current.splitlines(keepends=True)
    kept: list[str] = []
    index = 0

    while index < len(lines):
        if lines[index].strip() != "## Automated repository checkpoint":
            kept.append(lines[index])
            index += 1
            continue

        index += 1
        while index < len(lines):
            stripped = lines[index].strip()
            if not stripped or stripped.startswith(generated_prefixes):
                index += 1
                continue
            break

    return "".join(kept)


def _replace_managed_block(
    current: str,
    block: str,
    *,
    identity: str,
) -> str:
    complete_block = re.compile(
        re.escape(PROJECT_STATE_START) + r".*?" + re.escape(PROJECT_STATE_END),
        re.DOTALL,
    )
    marker = _project_state_marker(identity)
    preserved = next(
        (
            match.group(0)
            for match in complete_block.finditer(current)
            if marker in match.group(0)
        ),
        None,
    )
    cleaned = complete_block.sub("", current)
    orphan_marker = re.compile(
        rf"(?m)^[ \t]*(?:{re.escape(PROJECT_STATE_START)}|{re.escape(PROJECT_STATE_END)})[ \t]*\n?"
    )
    cleaned = orphan_marker.sub("", cleaned)
    cleaned = _remove_legacy_checkpoint_blocks(cleaned)
    return cleaned.rstrip() + "\n\n" + (preserved or block) + "\n"


def _kernel_current_values(repo: Path) -> tuple[str | None, str | None]:
    kernel = repo / ".cybercore" / "project.yaml"
    if not kernel.is_file():
        return None, None

    milestone: str | None = None
    artifact: str | None = None
    in_current = False
    for raw_line in kernel.read_text(encoding="utf-8").splitlines():
        if raw_line == "current:":
            in_current = True
            continue
        if in_current and raw_line and not raw_line.startswith("  "):
            break
        if not in_current:
            continue
        stripped = raw_line.strip()
        if stripped.startswith("milestone:"):
            milestone = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("active_artifact:"):
            artifact = stripped.split(":", 1)[1].strip()
    return milestone, artifact


def _synchronize_state_fields(
    current: str,
    checkpoint: RepositoryCheckpoint,
    *,
    milestone: str | None,
    artifact: str | None,
    test_result: str | None,
    next_action: str | None,
) -> str:
    updated = re.sub(
        r"(?m)^- Active branch: `[^`]*`$",
        f"- Active branch: `{checkpoint.branch}`",
        current,
    )
    if artifact:
        label = artifact
        if milestone:
            name = re.sub(r"\s+v\d+(?:\.\d+)*$", "", milestone).strip()
            label = f"{artifact} {name}"
        updated = re.sub(
            r"(?m)^- Active work block: `[^`]*`$",
            f"- Active work block: `{label}`",
            updated,
        )
    if milestone:
        updated = re.sub(
            r"(?ms)(^## Current milestone\n\n).*?(?=\n## |\Z)",
            rf"\1{milestone}.\n",
            updated,
        )
    status_lines = [
        "- Work block: active",
        f"- Branch: `{checkpoint.branch}`",
        "- Project Kernel: present" if checkpoint.project_kernel_present else "- Project Kernel: missing",
        "- Runtime implementation: implemented",
        f"- Tests: {test_result or 'not supplied'}",
        "- Pull request: not created",
    ]
    updated = re.sub(
        r"(?ms)(^## Current status\n\n).*?(?=\n## |\Z)",
        "\\1" + "\n".join(status_lines) + "\n",
        updated,
    )
    if next_action:
        updated = re.sub(
            r"(?ms)(^## Next action\n\n).*?(?=\n## |\Z)",
            rf"\1{next_action}\n",
            updated,
        )
    return updated


def _checkpoint_identity(
    checkpoint: RepositoryCheckpoint,
    test_result: str | None,
) -> str:
    canonical = "\0".join(
        [
            str(Path(checkpoint.repository).resolve()),
            checkpoint.commit,
            test_result or "not supplied",
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _worklog_marker(identity: str) -> str:
    return f"<!-- {WORKLOG_CHECKPOINT_PREFIX}{identity} -->"


def _worklog_entry(
    checkpoint: RepositoryCheckpoint,
    test_result: str | None,
    next_action: str | None,
    *,
    identity: str,
) -> str:
    lines = [
        _worklog_marker(identity),
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


def _append_worklog_entry(current: str, entry: str, *, identity: str) -> str:
    if _worklog_marker(identity) in current:
        return current
    return current.rstrip() + "\n\n" + entry


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
    milestone, artifact = _kernel_current_values(repo)
    synchronized = _synchronize_state_fields(
        current_state,
        checkpoint,
        milestone=milestone,
        artifact=artifact,
        test_result=test_result,
        next_action=next_action,
    )
    identity = _checkpoint_identity(checkpoint, test_result)
    block = _checkpoint_block(checkpoint, test_result, identity=identity)
    state_content = _replace_managed_block(
        synchronized,
        block,
        identity=identity,
    )
    entry = _worklog_entry(
        checkpoint,
        test_result,
        next_action,
        identity=identity,
    )
    worklog_content = _append_worklog_entry(
        current_worklog,
        entry,
        identity=identity,
    )

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
