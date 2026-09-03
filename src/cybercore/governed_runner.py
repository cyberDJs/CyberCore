from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import subprocess

from cybercore.governed_plan import CommandPlan, CommandSpec, OperationClass
from cybercore.governed_receipt import CommandReceipt, ExecutionReceipt


class GovernedRunnerError(RuntimeError):
    """Raised when a command plan violates the governed runner contract."""


_BLOCKED_EXECUTABLES = {
    "bash",
    "sh",
    "zsh",
    "fish",
    "sudo",
    "su",
    "doas",
    "rm",
    "shred",
    "dd",
    "mkfs",
    "eval",
    "exec",
    "env",
    "printenv",
}

_SHELL_META = ("|", "&", ";", ">", "<", "`", "$(`", "\n", "\r")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _matches_prefix(argv: tuple[str, ...], prefix: tuple[str, ...]) -> bool:
    return len(argv) >= len(prefix) and argv[: len(prefix)] == prefix


def _contains_shell_meta(argv: tuple[str, ...]) -> bool:
    return any(token in arg for arg in argv for token in _SHELL_META)


def _resolved_cwd(root: Path, raw_cwd: str) -> Path:
    candidate = Path(raw_cwd)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if resolved != root and root not in resolved.parents:
        raise GovernedRunnerError(f"command cwd escapes allowed root: {resolved}")
    if not resolved.is_dir():
        raise GovernedRunnerError(f"command cwd does not exist: {resolved}")
    return resolved


def validate_command(plan: CommandPlan, command: CommandSpec, *, root: Path) -> Path:
    grant = plan.grant
    if plan.operation_id != grant.operation_id:
        raise GovernedRunnerError("plan operation_id does not match authorization grant")
    if plan.canonical_target != grant.canonical_target:
        raise GovernedRunnerError("plan canonical_target does not match authorization grant")
    if not grant.is_current():
        raise GovernedRunnerError("authorization grant is expired or not yet valid")
    if command.classification is OperationClass.BLOCKED:
        raise GovernedRunnerError("BLOCKED command class cannot be executed")
    if command.classification not in grant.allowed_classes:
        raise GovernedRunnerError(
            f"operation class is not authorized: {command.classification.value}"
        )

    executable = Path(command.argv[0]).name
    if executable in _BLOCKED_EXECUTABLES:
        raise GovernedRunnerError(f"executable is denied by policy: {executable}")
    if _contains_shell_meta(command.argv):
        raise GovernedRunnerError("shell metacharacters are denied by policy")
    if not any(
        _matches_prefix(command.argv, prefix)
        for prefix in grant.allowed_command_prefixes
    ):
        raise GovernedRunnerError(f"command is outside authorized prefixes: {command.argv!r}")

    return _resolved_cwd(root, command.cwd)


class GovernedRunner:
    """Execute an already-authorized command plan without interpreting new authority."""

    def __init__(self, allowed_root: Path):
        self.allowed_root = allowed_root.expanduser().resolve()
        if not self.allowed_root.is_dir():
            raise GovernedRunnerError(f"allowed root does not exist: {self.allowed_root}")

    def execute(self, plan: CommandPlan) -> ExecutionReceipt:
        receipts: list[CommandReceipt] = []
        status = "IMPLEMENTED"

        for command in plan.commands:
            cwd = validate_command(plan, command, root=self.allowed_root)
            started = datetime.now(timezone.utc)
            timed_out = False
            exit_code: int | None
            stdout = b""
            stderr = b""

            environment = {
                "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
            }

            try:
                completed = subprocess.run(
                    list(command.argv),
                    cwd=cwd,
                    env=environment,
                    check=False,
                    capture_output=True,
                    timeout=command.timeout_seconds,
                    shell=False,
                )
                exit_code = completed.returncode
                stdout = completed.stdout
                stderr = completed.stderr
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                exit_code = None
                stdout = exc.stdout or b""
                stderr = exc.stderr or b""
            except OSError as exc:
                exit_code = None
                stderr = str(exc).encode("utf-8", errors="replace")

            finished = datetime.now(timezone.utc)
            receipts.append(
                CommandReceipt(
                    argv=command.argv,
                    cwd=str(cwd),
                    classification=command.classification,
                    started_at=started.isoformat(),
                    finished_at=finished.isoformat(),
                    exit_code=exit_code,
                    stdout_sha256=_digest(stdout),
                    stderr_sha256=_digest(stderr),
                    timed_out=timed_out,
                )
            )

            if timed_out or exit_code != 0:
                status = "FAILED"
                break

        return ExecutionReceipt(
            operation_id=plan.operation_id,
            canonical_target=plan.canonical_target,
            commands=tuple(receipts),
            status=status,
            verified=False,
        )
