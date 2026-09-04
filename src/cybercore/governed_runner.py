from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from typing import BinaryIO, Protocol
import uuid

from cybercore.governed_plan import (
    AuthorizationGrant,
    CommandPlan,
    CommandSpec,
    OperationClass,
)
from cybercore.governed_receipt import CommandReceipt, ExecutionReceipt


class GovernedRunnerError(RuntimeError):
    """Raised when a command plan violates the governed runner contract."""


_BLOCKED_EXECUTABLES = {
    "bash",
    "sh",
    "zsh",
    "fish",
    "dash",
    "ash",
    "ksh",
    "ksh93",
    "mksh",
    "csh",
    "tcsh",
    "yash",
    "xonsh",
    "nu",
    "nushell",
    "pwsh",
    "powershell",
    "busybox",
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

_SHELL_META = ("|", "&", ";", ">", "<", "`", "$(", "\n", "\r")
_TRUSTED_EXECUTABLE_PATH = "/usr/local/bin:/usr/bin:/bin"
_MAX_OUTPUT_BYTES_PER_STREAM = 1024 * 1024
_OUTPUT_READ_CHUNK_BYTES = 64 * 1024
_PROCESS_POLL_SECONDS = 0.01
_PROCESS_GROUP_TERM_GRACE_SECONDS = 0.1
_PROCESS_TERMINATION_BUDGET_SECONDS = 1.0
_REQUIRED_USER_BUS_ENV = ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS")
_APPROVED_EXECUTABLE_NAMES = {"git", "pytest"}
_PYTHON_EXECUTABLE_RE = re.compile(r"^python(?:3(?:\.\d+)?)?$")
_REPLAY_SENSITIVE_CLASSES = frozenset(
    {
        OperationClass.FILE_WRITE,
        OperationClass.REPO_WRITE,
        OperationClass.REMOTE_WRITE,
        OperationClass.DEPLOY,
        OperationClass.DESTRUCTIVE,
        OperationClass.PRIVILEGED,
    }
)


@dataclass(frozen=True, slots=True)
class _FileIdentity:
    device: int
    inode: int
    size: int
    mtime_ns: int
    mode: int
    sha256: str


@dataclass(frozen=True, slots=True)
class _PreparedCommand:
    spec: CommandSpec
    cwd: Path
    argv: tuple[str, ...]
    cwd_identity: tuple[int, int]
    executable_identity: _FileIdentity


class _Containment(Protocol):
    def spawn(
        self,
        prepared: _PreparedCommand,
        *,
        env: dict[str, str],
        timeout_seconds: float,
        grant_expires_at: datetime,
    ) -> subprocess.Popen[bytes]: ...

    def terminate(self, process: subprocess.Popen[bytes], *, deadline: float) -> None: ...


class _SystemdContainment:
    """Contain commands in a transient user-service cgroup; fail closed if unavailable."""

    def __init__(self) -> None:
        if os.name != "posix":
            raise GovernedRunnerError("strong process containment is unavailable on this platform")
        systemd_run = shutil.which("systemd-run", path=_TRUSTED_EXECUTABLE_PATH)
        systemctl = shutil.which("systemctl", path=_TRUSTED_EXECUTABLE_PATH)
        python3 = shutil.which("python3", path=_TRUSTED_EXECUTABLE_PATH)
        if systemd_run is None or systemctl is None or python3 is None:
            raise GovernedRunnerError("systemd cgroup containment tools are unavailable")
        self._systemd_run = str(Path(systemd_run).resolve())
        self._systemctl = str(Path(systemctl).resolve())
        self._wrapper_python = str(Path(python3).resolve())
        self._units: dict[int, str] = {}

    def spawn(
        self,
        prepared: _PreparedCommand,
        *,
        env: dict[str, str],
        timeout_seconds: float,
        grant_expires_at: datetime,
    ) -> subprocess.Popen[bytes]:
        unit = f"cybercore-governed-{uuid.uuid4().hex}"
        payload = _stable_exec_wrapper_argv(
            prepared,
            grant_expires_at=grant_expires_at,
            wrapper_python=self._wrapper_python,
        )
        wrapped = (
            self._systemd_run,
            "--user",
            "--quiet",
            "--collect",
            "--wait",
            "--pipe",
            f"--unit={unit}",
            "--working-directory=/",
            f"--property=RuntimeMaxSec={timeout_seconds}s",
            f"--property=TimeoutStopSec={_PROCESS_TERMINATION_BUDGET_SECONDS}s",
            "--property=KillMode=control-group",
            "--property=SendSIGKILL=yes",
            f"--setenv=PATH={env['PATH']}",
            f"--setenv=LANG={env['LANG']}",
            f"--setenv=LC_ALL={env['LC_ALL']}",
            "--",
            *payload,
        )
        process = subprocess.Popen(
            list(wrapped),
            cwd="/",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            shell=False,
        )
        self._units[process.pid] = unit
        return process

    def terminate(self, process: subprocess.Popen[bytes], *, deadline: float) -> None:
        unit = self._units.get(process.pid)
        if unit is None:
            raise GovernedRunnerError("containment unit identity is missing")
        containment_env = _bounded_environment(include_user_bus=True)
        signals = ("TERM", "KILL")
        for index, sig in enumerate(signals):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            phases_left = len(signals) - index
            control_timeout = remaining / phases_left
            try:
                subprocess.run(
                    [
                        self._systemctl,
                        "--user",
                        "kill",
                        "--kill-whom=all",
                        f"--signal={sig}",
                        unit,
                    ],
                    env=containment_env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=False,
                    check=False,
                    timeout=control_timeout,
                )
            except subprocess.TimeoutExpired:
                continue
            if process.poll() is not None:
                return
            if sig == "TERM":
                remaining = deadline - time.monotonic()
                if remaining > 0:
                    time.sleep(min(_PROCESS_GROUP_TERM_GRACE_SECONDS, remaining / 2))

        if process.poll() is None:
            process.kill()
            remaining = deadline - time.monotonic()
            if remaining > 0:
                try:
                    process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    pass


class _DigestState:
    def __init__(self, byte_limit: int) -> None:
        self.byte_limit = byte_limit
        self.total_bytes = 0
        self.limit_exceeded = False
        self._digest = hashlib.sha256()

    def consume(self, chunk: bytes) -> None:
        self._digest.update(chunk)
        self.total_bytes += len(chunk)
        if self.total_bytes > self.byte_limit:
            self.limit_exceeded = True

    def hexdigest(self) -> str:
        return self._digest.hexdigest()


def _bounded_environment(*, include_user_bus: bool) -> dict[str, str]:
    environment = {
        "PATH": _TRUSTED_EXECUTABLE_PATH,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    if include_user_bus:
        for name in _REQUIRED_USER_BUS_ENV:
            value = os.environ.get(name)
            if value:
                environment[name] = value
    return environment


def _default_nonce_state_dir() -> Path:
    configured = os.environ.get("XDG_STATE_HOME")
    state_home = Path(configured).expanduser() if configured else Path.home() / ".local" / "state"
    return state_home / "cybercore" / "governed-runner" / "consumed-nonces"


def _requires_nonce_consumption(plan: CommandPlan) -> bool:
    return any(command.classification in _REPLAY_SENSITIVE_CLASSES for command in plan.commands)


def _consume_authorization_nonce(grant: AuthorizationGrant, *, state_dir: Path) -> None:
    try:
        state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as exc:
        raise GovernedRunnerError("authorization nonce state directory is unavailable") from exc

    nonce_key = hashlib.sha256(
        f"{grant.issuer}\0{grant.nonce}".encode("utf-8", errors="strict")
    ).hexdigest()
    marker = state_dir / nonce_key
    payload = (
        f"issuer={grant.issuer}\n"
        f"operation_id={grant.operation_id}\n"
        f"canonical_target={grant.canonical_target}\n"
        f"expires_at={grant.expires_at.isoformat()}\n"
    ).encode("utf-8")
    try:
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise GovernedRunnerError("authorization grant nonce has already been consumed") from exc
    except OSError as exc:
        raise GovernedRunnerError("authorization grant nonce cannot be consumed") from exc

    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        try:
            marker.unlink()
        except OSError:
            pass
        raise GovernedRunnerError("authorization grant nonce cannot be persisted") from exc

    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        directory_fd = os.open(state_dir, directory_flags)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        # The marker may already be durable. Keep it and fail closed rather than
        # risk making a consumed authorization reusable.
        raise GovernedRunnerError(
            "authorization grant nonce directory cannot be persisted"
        ) from exc


_STABLE_EXEC_WRAPPER = r"""
import hashlib
import os
import sys
import time


def fail(message, code=126):
    os.write(2, (message + "\n").encode("utf-8", errors="replace"))
    raise SystemExit(code)


cwd_path = sys.argv[1]
expected_cwd_device = int(sys.argv[2])
expected_cwd_inode = int(sys.argv[3])
executable_path = sys.argv[4]
expected_device = int(sys.argv[5])
expected_inode = int(sys.argv[6])
expected_size = int(sys.argv[7])
expected_mtime_ns = int(sys.argv[8])
expected_mode = int(sys.argv[9])
expected_sha256 = sys.argv[10]
expires_at = float(sys.argv[11])
target_argv = sys.argv[12:]

if time.time() >= expires_at:
    fail("authorization grant expired before service exec", 125)

cwd_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
try:
    cwd_fd = os.open(cwd_path, cwd_flags)
except OSError:
    fail("validated cwd cannot be opened inside service")

try:
    cwd_stat = os.fstat(cwd_fd)
    if (cwd_stat.st_dev, cwd_stat.st_ino) != (expected_cwd_device, expected_cwd_inode):
        fail("validated cwd identity changed before service exec")

    try:
        source_fd = os.open(executable_path, os.O_RDONLY)
    except OSError:
        fail("validated executable cannot be opened inside service")

    try:
        executable_stat = os.fstat(source_fd)
        observed = (
            executable_stat.st_dev,
            executable_stat.st_ino,
            executable_stat.st_size,
            executable_stat.st_mtime_ns,
            executable_stat.st_mode,
        )
        expected = (
            expected_device,
            expected_inode,
            expected_size,
            expected_mtime_ns,
            expected_mode,
        )
        if observed != expected:
            fail("validated executable metadata changed before service exec")

        if not hasattr(os, "memfd_create") or os.execve not in os.supports_fd:
            fail("stable executable handle execution is unavailable")
        executable_fd = os.memfd_create("cybercore-governed-exec", flags=0)
        try:
            digest = hashlib.sha256()
            while True:
                chunk = os.read(source_fd, 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                view = memoryview(chunk)
                while view:
                    written = os.write(executable_fd, view)
                    view = view[written:]
            if digest.hexdigest() != expected_sha256:
                fail("validated executable content changed before service exec")
            if time.time() >= expires_at:
                fail("authorization grant expired before service exec", 125)

            os.fchmod(executable_fd, 0o700)
            os.lseek(executable_fd, 0, os.SEEK_SET)
            os.set_inheritable(executable_fd, True)
            os.fchdir(cwd_fd)
            payload_env = {
                key: os.environ[key]
                for key in ("PATH", "LANG", "LC_ALL")
                if key in os.environ
            }
            os.execve(executable_fd, target_argv, payload_env)
        finally:
            os.close(executable_fd)
    finally:
        os.close(source_fd)
finally:
    os.close(cwd_fd)
"""


def _stable_exec_wrapper_argv(
    prepared: _PreparedCommand,
    *,
    grant_expires_at: datetime,
    wrapper_python: str,
) -> tuple[str, ...]:
    executable = prepared.executable_identity
    cwd_device, cwd_inode = prepared.cwd_identity
    return (
        wrapper_python,
        "-c",
        _STABLE_EXEC_WRAPPER,
        str(prepared.cwd),
        str(cwd_device),
        str(cwd_inode),
        prepared.argv[0],
        str(executable.device),
        str(executable.inode),
        str(executable.size),
        str(executable.mtime_ns),
        str(executable.mode),
        executable.sha256,
        repr(grant_expires_at.timestamp()),
        *prepared.argv,
    )


def _matches_prefix(argv: tuple[str, ...], prefix: tuple[str, ...]) -> bool:
    return len(argv) >= len(prefix) and argv[: len(prefix)] == prefix


def _contains_shell_meta(argv: tuple[str, ...]) -> bool:
    return any(token in arg for arg in argv for token in _SHELL_META)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise GovernedRunnerError(f"executable cannot be hashed: {path}") from exc
    return digest.hexdigest()


def _cwd_identity(path: Path) -> tuple[int, int]:
    try:
        stat = path.stat()
    except OSError as exc:
        raise GovernedRunnerError(f"command cwd cannot be inspected: {path}") from exc
    return stat.st_dev, stat.st_ino


def _executable_identity(path: Path) -> _FileIdentity:
    try:
        stat = path.stat()
    except OSError as exc:
        raise GovernedRunnerError(f"executable cannot be inspected: {path}") from exc
    return _FileIdentity(
        device=stat.st_dev,
        inode=stat.st_ino,
        size=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        mode=stat.st_mode,
        sha256=_hash_file(path),
    )


def _resolved_cwd(root: Path, raw_cwd: str) -> Path:
    candidate = Path(raw_cwd)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise GovernedRunnerError(f"command cwd cannot be resolved: {candidate}") from exc
    if resolved != root and root not in resolved.parents:
        raise GovernedRunnerError(f"command cwd escapes allowed root: {resolved}")
    if not resolved.is_dir():
        raise GovernedRunnerError(f"command cwd does not exist: {resolved}")
    return resolved


def _deny_blocked_executable(executable: str) -> None:
    name = Path(executable).name.lower()
    if name in _BLOCKED_EXECUTABLES:
        raise GovernedRunnerError(f"executable is denied by policy: {name}")


def _require_positive_executable_policy(executable: str) -> None:
    name = Path(executable).name.lower()
    if name in _APPROVED_EXECUTABLE_NAMES or _PYTHON_EXECUTABLE_RE.fullmatch(name):
        return
    raise GovernedRunnerError(f"executable is not approved by positive policy: {name}")


def _resolve_executable(raw_executable: str) -> str:
    candidate = Path(raw_executable)
    if candidate.is_absolute():
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise GovernedRunnerError(
                f"authorized executable cannot be resolved: {raw_executable}"
            ) from exc
        if not resolved.is_file() or not os.access(resolved, os.X_OK):
            raise GovernedRunnerError(f"authorized executable is not executable: {resolved}")
        return str(resolved)

    if candidate.parent != Path("."):
        raise GovernedRunnerError(
            f"relative executable paths are denied by policy: {raw_executable}"
        )

    resolved_name = shutil.which(raw_executable, path=_TRUSTED_EXECUTABLE_PATH)
    if resolved_name is None:
        raise GovernedRunnerError(
            f"authorized executable was not found on the trusted path: {raw_executable}"
        )
    resolved = Path(resolved_name).resolve(strict=True)
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise GovernedRunnerError(f"authorized executable is not executable: {resolved}")
    return str(resolved)


def _validate_plan_binding(plan: CommandPlan) -> None:
    grant = plan.grant
    if plan.operation_id != grant.operation_id:
        raise GovernedRunnerError("plan operation_id does not match authorization grant")
    if plan.canonical_target != grant.canonical_target:
        raise GovernedRunnerError("plan canonical_target does not match authorization grant")
    if not grant.is_current():
        raise GovernedRunnerError("authorization grant is expired or not yet valid")


def _prepare_command(plan: CommandPlan, command: CommandSpec, *, root: Path) -> _PreparedCommand:
    grant = plan.grant
    if command.classification is OperationClass.BLOCKED:
        raise GovernedRunnerError("BLOCKED command class cannot be executed")
    if command.classification not in grant.allowed_classes:
        raise GovernedRunnerError(
            f"operation class is not authorized: {command.classification.value}"
        )

    _deny_blocked_executable(command.argv[0])
    raw_executable = Path(command.argv[0])
    if not raw_executable.is_absolute():
        _require_positive_executable_policy(command.argv[0])
    if _contains_shell_meta(command.argv):
        raise GovernedRunnerError("shell metacharacters are denied by policy")
    if not any(_matches_prefix(command.argv, prefix) for prefix in grant.allowed_command_prefixes):
        raise GovernedRunnerError(f"command is outside authorized prefixes: {command.argv!r}")

    cwd = _resolved_cwd(root, command.cwd)
    resolved_executable = _resolve_executable(command.argv[0])
    _deny_blocked_executable(resolved_executable)
    _require_positive_executable_policy(resolved_executable)
    executable_path = Path(resolved_executable)
    return _PreparedCommand(
        spec=command,
        cwd=cwd,
        argv=(resolved_executable, *command.argv[1:]),
        cwd_identity=_cwd_identity(cwd),
        executable_identity=_executable_identity(executable_path),
    )


def _prepare_plan(plan: CommandPlan, *, root: Path) -> tuple[_PreparedCommand, ...]:
    _validate_plan_binding(plan)
    return tuple(_prepare_command(plan, command, root=root) for command in plan.commands)


def _revalidate_prepared_command(
    plan: CommandPlan,
    prepared: _PreparedCommand,
    *,
    root: Path,
) -> _PreparedCommand:
    _validate_plan_binding(plan)
    current = _prepare_command(plan, prepared.spec, root=root)
    if current.cwd_identity != prepared.cwd_identity or current.cwd != prepared.cwd:
        raise GovernedRunnerError("command cwd changed after plan validation")
    if (
        current.executable_identity != prepared.executable_identity
        or current.argv[0] != prepared.argv[0]
    ):
        raise GovernedRunnerError("command executable changed after plan validation")
    return current


def _drain_stream(
    stream: BinaryIO,
    state: _DigestState,
    limit_event: threading.Event,
) -> None:
    try:
        while chunk := stream.read(_OUTPUT_READ_CHUNK_BYTES):
            state.consume(chunk)
            if state.limit_exceeded:
                limit_event.set()
    except (OSError, ValueError):
        pass
    finally:
        try:
            stream.close()
        except OSError:
            pass


def _revalidation_failure_receipt(
    prepared: _PreparedCommand,
    exc: GovernedRunnerError,
) -> CommandReceipt:
    timestamp = datetime.now(timezone.utc).isoformat()
    empty_digest = hashlib.sha256(b"").hexdigest()
    error_digest = hashlib.sha256(str(exc).encode("utf-8", errors="replace")).hexdigest()
    return CommandReceipt(
        argv=prepared.argv,
        cwd=str(prepared.cwd),
        classification=prepared.spec.classification,
        started_at=timestamp,
        finished_at=timestamp,
        exit_code=None,
        stdout_sha256=empty_digest,
        stderr_sha256=error_digest,
        timed_out=False,
    )


def _terminate_with_cleanup_budget(
    containment: _Containment,
    process: subprocess.Popen[bytes],
    *,
    cleanup_deadline: float | None = None,
) -> float:
    bounded_deadline = cleanup_deadline or (time.monotonic() + _PROCESS_TERMINATION_BUDGET_SECONDS)
    containment.terminate(process, deadline=bounded_deadline)
    return bounded_deadline


def _join_drain_threads_until_deadline(
    containment: _Containment,
    process: subprocess.Popen[bytes],
    stdout_thread: threading.Thread,
    stderr_thread: threading.Thread,
    deadline: float,
    cleanup_deadline: float | None = None,
) -> bool:
    threads = (stdout_thread, stderr_thread)
    for thread in threads:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        thread.join(timeout=remaining)

    if not any(thread.is_alive() for thread in threads):
        return True

    if cleanup_deadline is None:
        cleanup_deadline = _terminate_with_cleanup_budget(containment, process)
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass
    for thread in threads:
        remaining = cleanup_deadline - time.monotonic()
        if remaining <= 0:
            break
        thread.join(timeout=min(_PROCESS_GROUP_TERM_GRACE_SECONDS, remaining))
    return False


class GovernedRunner:
    """Execute an already-authorized command plan without interpreting new authority."""

    def __init__(
        self,
        allowed_root: Path,
        *,
        containment: _Containment | None = None,
        nonce_state_dir: Path | None = None,
    ):
        self.allowed_root = allowed_root.expanduser().resolve()
        if not self.allowed_root.is_dir():
            raise GovernedRunnerError(f"allowed root does not exist: {self.allowed_root}")
        self._containment = containment
        self._nonce_state_dir = (
            (nonce_state_dir or _default_nonce_state_dir()).expanduser().resolve()
        )

    def execute(self, plan: CommandPlan) -> ExecutionReceipt:
        prepared_commands = _prepare_plan(plan, root=self.allowed_root)
        containment = self._containment or _SystemdContainment()
        if _requires_nonce_consumption(plan):
            _consume_authorization_nonce(plan.grant, state_dir=self._nonce_state_dir)
        receipts: list[CommandReceipt] = []
        status = "IMPLEMENTED"
        environment = _bounded_environment(include_user_bus=self._containment is None)

        for prepared in prepared_commands:
            try:
                current = _revalidate_prepared_command(plan, prepared, root=self.allowed_root)
                _validate_plan_binding(plan)
            except GovernedRunnerError as exc:
                receipts.append(_revalidation_failure_receipt(prepared, exc))
                status = "FAILED"
                break
            command = current.spec
            started = datetime.now(timezone.utc)
            timed_out = False
            output_limit_exceeded = False
            exit_code: int | None = None
            stdout_state = _DigestState(_MAX_OUTPUT_BYTES_PER_STREAM)
            stderr_state = _DigestState(_MAX_OUTPUT_BYTES_PER_STREAM)
            output_limit_event = threading.Event()
            deadline = time.monotonic() + command.timeout_seconds
            cleanup_deadline: float | None = None

            try:
                process = containment.spawn(
                    current,
                    env=environment,
                    timeout_seconds=command.timeout_seconds,
                    grant_expires_at=plan.grant.expires_at,
                )
            except OSError as exc:
                stderr_state.consume(str(exc).encode("utf-8", errors="replace"))
            else:
                assert process.stdout is not None
                assert process.stderr is not None
                stdout_thread = threading.Thread(
                    target=_drain_stream,
                    args=(process.stdout, stdout_state, output_limit_event),
                    daemon=True,
                )
                stderr_thread = threading.Thread(
                    target=_drain_stream,
                    args=(process.stderr, stderr_state, output_limit_event),
                    daemon=True,
                )
                stdout_thread.start()
                stderr_thread.start()

                while process.poll() is None:
                    if output_limit_event.is_set():
                        output_limit_exceeded = True
                        cleanup_deadline = _terminate_with_cleanup_budget(
                            containment,
                            process,
                            cleanup_deadline=cleanup_deadline,
                        )
                        break
                    if time.monotonic() >= deadline:
                        timed_out = True
                        cleanup_deadline = _terminate_with_cleanup_budget(
                            containment,
                            process,
                            cleanup_deadline=cleanup_deadline,
                        )
                        break
                    time.sleep(_PROCESS_POLL_SECONDS)

                if process.poll() is None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        timed_out = True
                        cleanup_deadline = _terminate_with_cleanup_budget(
                            containment,
                            process,
                            cleanup_deadline=cleanup_deadline,
                        )
                    else:
                        try:
                            process.wait(timeout=remaining)
                        except subprocess.TimeoutExpired:
                            timed_out = True
                            cleanup_deadline = _terminate_with_cleanup_budget(
                                containment,
                                process,
                                cleanup_deadline=cleanup_deadline,
                            )

                exit_code = process.returncode
                drains_finished_before_deadline = _join_drain_threads_until_deadline(
                    containment,
                    process,
                    stdout_thread,
                    stderr_thread,
                    deadline,
                    cleanup_deadline=cleanup_deadline,
                )
                if not drains_finished_before_deadline:
                    timed_out = True
                output_limit_exceeded = output_limit_exceeded or output_limit_event.is_set()

            finished = datetime.now(timezone.utc)
            receipts.append(
                CommandReceipt(
                    argv=current.argv,
                    cwd=str(current.cwd),
                    classification=command.classification,
                    started_at=started.isoformat(),
                    finished_at=finished.isoformat(),
                    exit_code=exit_code,
                    stdout_sha256=stdout_state.hexdigest(),
                    stderr_sha256=stderr_state.hexdigest(),
                    timed_out=timed_out,
                )
            )

            if timed_out or output_limit_exceeded or exit_code != 0:
                status = "FAILED"
                break

        return ExecutionReceipt(
            operation_id=plan.operation_id,
            canonical_target=plan.canonical_target,
            commands=tuple(receipts),
            status=status,
            verified=False,
        )
