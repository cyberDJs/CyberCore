from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import subprocess

from cybercore.repository_identity_policy import (
    RepositoryIdentityPolicyError,
    evaluate_repository_identity_policy,
)


class TrustedOperationContextError(RuntimeError):
    """Raised when a trusted operation context cannot be collected or enforced."""


@dataclass(frozen=True, slots=True)
class ContextCheck:
    name: str
    passed: bool
    detail: str

    def as_dict(self) -> dict[str, str | bool]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TrustedOperationContext:
    repository: str
    operation: str
    risk: str
    branch: str
    commit: str
    dirty: bool
    project_kernel_present: bool
    project_state_present: bool
    trusted: bool
    checks: tuple[ContextCheck, ...]

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["checks"] = [check.as_dict() for check in self.checks]
        return payload


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "git command failed"
        raise TrustedOperationContextError(detail)
    return completed.stdout.rstrip("\r\n")


def _canonical_identity_configured(repo: Path) -> bool:
    project = repo / ".cybercore" / "project.yaml"
    try:
        content = project.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False
    return re.search(r"(?m)^\s{2}repository:\s*git:", content) is not None


def collect_trusted_operation_context(
    repo: Path,
    *,
    operation: str = "inspect",
    risk: str = "low",
    expected_branch: str | None = None,
    expected_commit: str | None = None,
    require_clean: bool = False,
) -> TrustedOperationContext:
    """Collect and evaluate a read-only safety context for an operation."""
    resolved = repo.expanduser().resolve()
    if not (resolved / ".git").exists():
        raise TrustedOperationContextError(f"Not a Git repository: {resolved}")
    if risk not in {"low", "medium", "high", "critical"}:
        raise TrustedOperationContextError(f"Unsupported risk level: {risk}")

    branch = _git(resolved, "branch", "--show-current") or "detached"
    commit = _git(resolved, "rev-parse", "HEAD")
    dirty = bool(_git(resolved, "status", "--porcelain=v1"))
    kernel_present = (resolved / ".cybercore" / "project.yaml").is_file()
    state_present = (resolved / "PROJECT_STATE.md").is_file()
    canonical = _canonical_identity_configured(resolved)

    checks: list[ContextCheck] = [
        ContextCheck("git_repository", True, "Git repository detected."),
        ContextCheck(
            "project_kernel",
            kernel_present or not canonical,
            "Project Kernel is present."
            if kernel_present
            else "Project Kernel is optional for a legacy project without canonical identity.",
        ),
        ContextCheck(
            "project_state",
            state_present or not canonical,
            "Project State is present."
            if state_present
            else "Project State is optional for a legacy project without canonical identity.",
        ),
    ]

    if canonical:
        try:
            identity = evaluate_repository_identity_policy(resolved)
        except RepositoryIdentityPolicyError as exc:
            checks.append(ContextCheck("repository_identity", False, str(exc)))
        else:
            checks.append(
                ContextCheck(
                    "repository_identity",
                    identity.compliant,
                    identity.message,
                )
            )
    else:
        checks.append(
            ContextCheck(
                "repository_identity",
                True,
                "Canonical repository identity is not configured; legacy compatibility applies.",
            )
        )

    if expected_branch is not None:
        checks.append(
            ContextCheck(
                "expected_branch",
                branch == expected_branch,
                f"Current branch is {branch}; expected {expected_branch}.",
            )
        )

    if expected_commit is not None:
        checks.append(
            ContextCheck(
                "expected_commit",
                commit == expected_commit,
                f"Current commit is {commit}; expected {expected_commit}.",
            )
        )

    if require_clean:
        checks.append(
            ContextCheck(
                "clean_working_tree",
                not dirty,
                "Working tree is clean." if not dirty else "Working tree is dirty.",
            )
        )

    trusted = all(check.passed for check in checks)
    return TrustedOperationContext(
        repository=str(resolved),
        operation=operation,
        risk=risk,
        branch=branch,
        commit=commit,
        dirty=dirty,
        project_kernel_present=kernel_present,
        project_state_present=state_present,
        trusted=trusted,
        checks=tuple(checks),
    )


def enforce_trusted_operation_context(
    repo: Path,
    *,
    operation: str,
    risk: str,
    expected_branch: str | None = None,
    expected_commit: str | None = None,
    require_clean: bool = False,
) -> TrustedOperationContext:
    """Collect a context and reject the operation when any required check fails."""
    context = collect_trusted_operation_context(
        repo,
        operation=operation,
        risk=risk,
        expected_branch=expected_branch,
        expected_commit=expected_commit,
        require_clean=require_clean,
    )
    if context.trusted:
        return context
    failures = "; ".join(
        f"{check.name}: {check.detail}" for check in context.checks if not check.passed
    )
    raise TrustedOperationContextError(
        f"Trusted operation context rejected {operation}: {failures}"
    )


def render_trusted_operation_context(context: TrustedOperationContext) -> str:
    lines = [
        "TRUSTED OPERATION CONTEXT",
        f"Status: {'trusted' if context.trusted else 'untrusted'}",
        f"Operation: {context.operation}",
        f"Risk: {context.risk}",
        f"Repository: {context.repository}",
        f"Branch: {context.branch}",
        f"Commit: {context.commit}",
        f"Working tree: {'dirty' if context.dirty else 'clean'}",
        "Checks:",
    ]
    for check in context.checks:
        lines.append(f"- {'PASS' if check.passed else 'FAIL'} {check.name}: {check.detail}")
    return "\n".join(lines) + "\n"
