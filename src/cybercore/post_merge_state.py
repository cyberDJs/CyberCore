from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tempfile

from cybercore.post_merge import PostMergeTransitionError, PostMergeTransitionPreview


@dataclass(frozen=True, slots=True)
class PostMergeStatePlan:
    kernel_path: Path
    project_state_path: Path
    kernel_content: str
    project_state_content: str

    def write(self) -> None:
        targets = (
            (self.kernel_path, self.kernel_content),
            (self.project_state_path, self.project_state_content),
        )
        staged_updates: dict[Path, Path] = {}
        staged_rollbacks: dict[Path, Path] = {}
        replaced: list[Path] = []
        try:
            for target, content in targets:
                staged_updates[target] = _stage(target, content.encode("utf-8"), ".new")
                staged_rollbacks[target] = _stage(target, target.read_bytes(), ".rollback")
            for target, _content in targets:
                os.replace(staged_updates[target], target)
                replaced.append(target)
        except Exception:
            rollback_error: Exception | None = None
            for target in reversed(replaced):
                try:
                    os.replace(staged_rollbacks[target], target)
                except Exception as exc:  # pragma: no cover
                    rollback_error = rollback_error or exc
            if rollback_error is not None:
                raise PostMergeTransitionError(
                    "Post-merge state write failed and rollback was incomplete"
                ) from rollback_error
            raise
        finally:
            for staged in (*staged_updates.values(), *staged_rollbacks.values()):
                staged.unlink(missing_ok=True)


def _stage(target: Path, content: bytes, suffix: str) -> Path:
    descriptor, raw_path = tempfile.mkstemp(
        prefix=f".{target.name}.cybercore-post-merge-",
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


def _literal_replacement(value: str) -> Callable[[re.Match[str]], str]:
    def replace(_match: re.Match[str]) -> str:
        return value

    return replace


def _replace_required(
    pattern: str,
    replacement: str | Callable[[re.Match[str]], str],
    content: str,
    label: str,
) -> str:
    replacement_fn = _literal_replacement(replacement) if isinstance(replacement, str) else replacement
    updated, count = re.subn(pattern, replacement_fn, content, count=1, flags=re.MULTILINE)
    if count != 1:
        raise PostMergeTransitionError(f"Unable to update {label}")
    return updated


def _replace_optional(pattern: str, replacement: str, content: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, content, count=1, flags=re.MULTILINE)
    if count > 1:
        raise PostMergeTransitionError(f"Unable to update {label}")
    return updated


def _yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _require_non_empty(label: str, value: str | None) -> str:
    if value is None:
        raise PostMergeTransitionError(f"{label} is required")
    normalized = value.strip()
    if not normalized:
        raise PostMergeTransitionError(f"{label} must be non-empty")
    return normalized


def _normalize_non_empty_items(label: str, values: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in values:
        item = value.strip()
        if not item:
            raise PostMergeTransitionError(f"{label} must not contain empty values")
        normalized.append(item)
    return tuple(normalized)


def _set_status(current: str, key: str, value: str) -> str:
    pattern = rf"(?m)^  {re.escape(key)}: .+$"
    if re.search(pattern, current):
        return re.sub(pattern, f"  {key}: {value}", current, count=1)
    marker = "\ncompleted:\n"
    if marker not in current:
        raise PostMergeTransitionError("Unable to update capability status")
    return current.replace(marker, f"\n  {key}: {value}{marker}", 1)


def _set_current(current: str, key: str, value: str) -> str:
    pattern = rf"(?m)^  {re.escape(key)}: .+$"
    if re.search(pattern, current):
        return re.sub(pattern, f"  {key}: {value}", current, count=1)
    marker = "\nstatus:\n"
    if marker not in current:
        raise PostMergeTransitionError("Unable to update current project state")
    return current.replace(marker, f"\n  {key}: {value}{marker}", 1)


def _set_project_state_checkpoint(
    current: str,
    preview: PostMergeTransitionPreview,
) -> str:
    checkpoint = preview.main_commit
    base_branch = preview.pull_request.base_branch
    old_pattern = r"^- Current canonical main: `[^`]+`$"
    if re.search(old_pattern, current, flags=re.MULTILINE):
        return re.sub(
            old_pattern,
            (
                f"- Canonical main ref: GitHub `{base_branch}` (resolve live)\n"
                f"- Last verified canonical checkpoint: `{checkpoint}`"
            ),
            current,
            count=1,
            flags=re.MULTILINE,
        )
    checkpoint_pattern = r"^- Last verified canonical checkpoint: `[^`]+`$"
    if re.search(checkpoint_pattern, current, flags=re.MULTILINE):
        return re.sub(
            checkpoint_pattern,
            f"- Last verified canonical checkpoint: `{checkpoint}`",
            current,
            count=1,
            flags=re.MULTILINE,
        )
    raise PostMergeTransitionError("Unable to update Project State checkpoint")


def _replace_next_tasks(current: str, next_tasks: tuple[str, ...]) -> str:
    task_block = (
        "next:\n" + "".join(f"  - {_yaml_string(task)}\n" for task in next_tasks)
        if next_tasks
        else "next: []\n"
    )
    return _replace_required(
        r"(?ms)^next:(?:[ \t]*\[\])?\n.*?(?=^rules:)",
        task_block,
        current,
        "next task list",
    )


def _insert_completed_entry(current: str, completed_entry: str) -> str:
    updated, count = re.subn(
        r"(?m)^next:(?:[ \t]*\[\])?$",
        lambda match: completed_entry + match.group(0),
        current,
        count=1,
    )
    if count != 1:
        raise PostMergeTransitionError("Unable to record completed artifact")
    return updated


def _kernel_transition(
    current: str,
    preview: PostMergeTransitionPreview,
    *,
    completed_artifact: str,
    verification: str,
    next_artifact: str | None,
    next_milestone: str | None,
    next_branch: str | None,
    terminal: bool,
    completed_status: str | None,
    next_status: str | None,
    next_tasks: tuple[str, ...],
) -> str:
    active_match = re.search(r"(?m)^  active_artifact: (\S+)$", current)
    if active_match is None or active_match.group(1) != completed_artifact:
        actual = active_match.group(1) if active_match else "missing"
        raise PostMergeTransitionError(
            f"Active artifact mismatch: {actual} != {completed_artifact}"
        )

    completed_marker = f"  - artifact: {completed_artifact}\n"
    if completed_marker not in current:
        completed_entry = (
            f"  - artifact: {completed_artifact}\n"
            f"    pull_request: {preview.pull_request.number}\n"
            f"    merge_commit: {preview.pull_request.merge_commit}\n"
            f"    verification: {_yaml_string(verification)}\n"
        )
        current = _insert_completed_entry(current, completed_entry)

    current = _set_current(current, "last_verified_main", preview.main_commit)
    current = _replace_required(
        r"^  tests: .+$", f"  tests: {_yaml_string(verification)}", current, "test baseline"
    )
    if completed_status:
        current = _set_status(current, completed_status, "verified")

    if terminal:
        milestone = _yaml_string(f"Canonical checkpoint after PR #{preview.pull_request.number}")
        current = _replace_required(
            r"^  milestone: .+$",
            f"  milestone: {milestone}",
            current,
            "current milestone",
        )
        current = _replace_required(
            r"^  active_artifact: .+$", "  active_artifact: null", current, "active artifact"
        )
        current = _replace_required(
            r"^  branch: .+$",
            f"  branch: {preview.pull_request.base_branch}",
            current,
            "active branch",
        )
        current = _replace_required(
            r"^  pull_request: .+$", "  pull_request: null", current, "pull request"
        )
        current = _replace_next_tasks(current, next_tasks)
    else:
        if next_artifact is None or next_milestone is None or next_branch is None:
            raise PostMergeTransitionError("Successor state contract is incomplete")
        current = _replace_required(
            r"^  milestone: .+$", f"  milestone: {next_milestone}", current, "current milestone"
        )
        current = _replace_required(
            r"^  active_artifact: .+$",
            f"  active_artifact: {next_artifact}",
            current,
            "active artifact",
        )
        current = _replace_required(
            r"^  branch: .+$", f"  branch: {next_branch}", current, "active branch"
        )
        current = _replace_required(
            r"^  pull_request: .+$", "  pull_request: null", current, "pull request"
        )
        if next_status:
            current = _set_status(current, next_status, "planned")
        if next_tasks:
            current = _replace_next_tasks(current, next_tasks)
    return current


def _project_state_transition(
    current: str,
    preview: PostMergeTransitionPreview,
    *,
    completed_artifact: str,
    verification: str,
    next_artifact: str | None,
    next_milestone: str | None,
    next_branch: str | None,
    next_action: str,
    terminal: bool,
    next_objective: str | None,
    next_scope: tuple[str, ...],
) -> str:
    current = _set_project_state_checkpoint(current, preview)

    if terminal:
        base_branch = preview.pull_request.base_branch
        current = _replace_optional(
            r"^- Current coordination artifact: .+$",
            "- Current coordination artifact: none — terminal canonical state",
            current,
            "Project State coordination artifact",
        )
        current = _replace_optional(
            r"^- Current coordination branch: .+$",
            f"- Current coordination branch: `{base_branch}`",
            current,
            "Project State coordination branch",
        )
        current = _replace_optional(
            r"^- Current coordination pull request: .+$",
            "- Current coordination pull request: none",
            current,
            "Project State coordination pull request",
        )
        current = _replace_required(
            r"^- Active branch: `[^`]+`$",
            f"- Active branch: `{base_branch}`",
            current,
            "Project State active branch",
        )
        current = _replace_required(
            r"^- Active work block: `[^`]+`$",
            "- Active work block: `none`",
            current,
            "Project State active work block",
        )
        current = _replace_required(
            r"(?ms)(^## Current milestone\n\n).*?(?=\n## )",
            lambda match: (
                match.group(1)
                + f"Canonical checkpoint after merged PR #{preview.pull_request.number}.\n"
            ),
            current,
            "Project State milestone",
        )
        if re.search(r"(?m)^## Active objective$", current):
            current = _replace_required(
                r"(?ms)(^## Active objective\n\n).*?(?=\n## Current status)",
                lambda match: (
                    match.group(1)
                    + "No active coordination work block. Select the next bounded candidate "
                    + f"explicitly against the live canonical `{base_branch}`.\n"
                ),
                current,
                "Project State terminal objective",
            )
        current = _replace_required(
            r"(?ms)(^## Current status\n\n).*?(?=\n## )",
            lambda match: (
                match.group(1)
                + "- Work block: idle\n"
                + f"- Branch: `{base_branch}`\n"
                + "- Project Kernel: present\n"
                + "- Runtime implementation: canonical\n"
                + f"- Tests: {verification.replace('_', ' ')}\n"
                + "- Pull request: none\n"
            ),
            current,
            "Project State status",
        )
    else:
        if next_artifact is None or next_milestone is None or next_branch is None:
            raise PostMergeTransitionError("Successor state contract is incomplete")
        current = _replace_optional(
            r"^- Current coordination artifact: .+$",
            f"- Current coordination artifact: {next_artifact}",
            current,
            "Project State coordination artifact",
        )
        current = _replace_optional(
            r"^- Current coordination branch: .+$",
            f"- Current coordination branch: `{next_branch}`",
            current,
            "Project State coordination branch",
        )
        current = _replace_optional(
            r"^- Current coordination pull request: .+$",
            "- Current coordination pull request: not created",
            current,
            "Project State coordination pull request",
        )
        current = _replace_required(
            r"^- Active branch: `[^`]+`$",
            f"- Active branch: `{next_branch}`",
            current,
            "Project State active branch",
        )
        current = _replace_required(
            r"^- Active work block: `[^`]+`$",
            f"- Active work block: `{next_artifact} {next_milestone}`",
            current,
            "Project State active work block",
        )
        current = _replace_required(
            r"(?ms)(^## Current milestone\n\n).*?(?=\n## )",
            lambda match: match.group(1) + f"{next_milestone}.\n",
            current,
            "Project State milestone",
        )
        if next_objective is not None:
            scope_text = "Scope:\n\n" + "".join(
                f"{index}. {item.rstrip('.;')};\n" for index, item in enumerate(next_scope, start=1)
            )
            current = _replace_required(
                r"(?ms)(^## Active objective\n\n).*?(?=\n## Current status)",
                lambda match: match.group(1) + f"{next_objective}\n\n{scope_text}",
                current,
                "Project State objective and scope",
            )
        current = _replace_required(
            r"(?ms)(^## Current status\n\n).*?(?=\n## )",
            lambda match: (
                match.group(1)
                + "- Work block: active\n"
                + f"- Branch: `{next_branch}`\n"
                + "- Project Kernel: present\n"
                + "- Runtime implementation: planned\n"
                + f"- Tests: {verification.replace('_', ' ')}\n"
                + "- Pull request: not created\n"
            ),
            current,
            "Project State status",
        )

    current = _replace_required(
        r"(?ms)(^## Next action\n\n).*?(?=\n<!-- CYBERCORE:CHECKPOINT:START -->)",
        lambda match: match.group(1) + f"{next_action}\n\n",
        current,
        "Project State next action",
    )

    heading = f"### PR #{preview.pull_request.number} — {preview.pull_request.title}"
    if heading not in current:
        completed = (
            f"{heading}\n\n"
            "Merged into `main` as:\n\n"
            "```text\n"
            f"{preview.pull_request.merge_commit}\n"
            "```\n\n"
            f"Completed artifact: `{completed_artifact}`.\n\n"
            "Verification:\n\n"
            f"- `pytest -q`: **{verification.replace('_', ' ')}**.\n\n"
        )
        current = current.replace(
            "\n## Current milestone\n", "\n" + completed + "## Current milestone\n", 1
        )
    return current


def plan_post_merge_state_update(
    repo: Path,
    preview: PostMergeTransitionPreview,
    *,
    completed_artifact: str,
    verification: str,
    next_action: str,
    next_artifact: str | None = None,
    next_milestone: str | None = None,
    next_branch: str | None = None,
    terminal: bool = False,
    completed_status: str | None = None,
    next_status: str | None = None,
    next_objective: str | None = None,
    next_scope: tuple[str, ...] = (),
    next_tasks: tuple[str, ...] = (),
) -> PostMergeStatePlan:
    completed_artifact = _require_non_empty("completed artifact", completed_artifact)
    verification = _require_non_empty("verification", verification)
    next_action = _require_non_empty("next action", next_action)
    next_scope = _normalize_non_empty_items("next scope", next_scope)
    next_tasks = _normalize_non_empty_items("next tasks", next_tasks)

    if terminal:
        if (
            any(
                value is not None
                for value in (
                    next_artifact,
                    next_milestone,
                    next_branch,
                    next_status,
                    next_objective,
                )
            )
            or next_scope
        ):
            raise PostMergeTransitionError(
                "Terminal closeout cannot declare a successor work block contract"
            )
    else:
        next_artifact = _require_non_empty("next artifact", next_artifact)
        next_milestone = _require_non_empty("next milestone", next_milestone)
        next_branch = _require_non_empty("next branch", next_branch)
        if next_objective is not None:
            next_objective = _require_non_empty("next objective", next_objective)
        if next_objective is not None and not next_scope:
            raise PostMergeTransitionError("A next objective requires at least one scope item")

    kernel_path = repo / ".cybercore" / "project.yaml"
    project_state_path = repo / "PROJECT_STATE.md"
    if not kernel_path.is_file() or not project_state_path.is_file():
        raise PostMergeTransitionError("Canonical Project Kernel or Project State is missing")

    kernel_content = _kernel_transition(
        kernel_path.read_text(encoding="utf-8"),
        preview,
        completed_artifact=completed_artifact,
        verification=verification,
        next_artifact=next_artifact,
        next_milestone=next_milestone,
        next_branch=next_branch,
        terminal=terminal,
        completed_status=completed_status,
        next_status=next_status,
        next_tasks=next_tasks,
    )
    project_state_content = _project_state_transition(
        project_state_path.read_text(encoding="utf-8"),
        preview,
        completed_artifact=completed_artifact,
        verification=verification,
        next_artifact=next_artifact,
        next_milestone=next_milestone,
        next_branch=next_branch,
        next_action=next_action,
        terminal=terminal,
        next_objective=next_objective,
        next_scope=next_scope,
    )
    return PostMergeStatePlan(
        kernel_path=kernel_path,
        project_state_path=project_state_path,
        kernel_content=kernel_content,
        project_state_content=project_state_content,
    )


def render_post_merge_state_preview(plan: PostMergeStatePlan) -> str:
    return (
        "=== .cybercore/project.yaml ===\n"
        + plan.kernel_content
        + "\n=== PROJECT_STATE.md ===\n"
        + plan.project_state_content
    )
