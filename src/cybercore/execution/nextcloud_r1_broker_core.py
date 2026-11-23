"""Issue #113: inert one-shot privilege broker transaction core.

NOT a daemon or deployment. A future root-owned socket layer must obtain
peer_uid with SO_PEERCRED and prove direct systemd/Polkit starts are denied.
The only runner dependency is injected; this module never starts units itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import time
from typing import Callable, Protocol


class Verifier(Protocol):
    def verify(
        self,
        *,
        operation_id: str,
        operation: str,
        target_id: str,
        plan_id: str,
        plan_revision: str,
        authorization_reference: str,
    ) -> object: ...


SYSTEMCTL = "/usr/bin/systemctl"
TARGET = "cyberskills-vps"
ALLOWED = {
    "nextcloud.r1.offhost.transfer": (
        SYSTEMCTL,
        "start",
        "--no-block",
        "cybercore-nextcloud-r1-transfer.service",
    ),
    "nextcloud.r1.offhost.rollback": (
        SYSTEMCTL,
        "start",
        "cybercore-nextcloud-r1-rollback.service",
    ),
}


@dataclass(frozen=True)
class Request:
    operation_id: str
    operation: str
    target_id: str
    plan_id: str
    plan_revision: str
    authorization_reference: str


class Rejected(ValueError):
    """No side effect permitted, including automatic retry."""


def _sync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _root_private_dir(path: Path, *, owner_uid: int) -> None:
    # Production passes owner_uid=0. Tests may use a private synthetic owner.
    info = path.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != owner_uid
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise Rejected("unsafe broker state directory")


def _write_all(fd: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        written = os.write(fd, raw[offset:])
        if written <= 0:
            raise OSError("short write while persisting broker state")
        offset += written


def _write_once(path: Path, payload: dict[str, object], *, owner_uid: int) -> None:
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600,
    )
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != owner_uid
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
        ):
            raise Rejected("unsafe transaction receipt inode")
        _write_all(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)
    _sync_dir(path.parent)


def _lock(path: Path, *, owner_uid: int) -> int:
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != owner_uid
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
        ):
            raise Rejected("unsafe broker lock inode")
        fcntl.flock(fd, fcntl.LOCK_EX)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _key(request: Request) -> str:
    fields = (
        request.operation_id,
        request.operation,
        request.target_id,
        request.plan_id,
        request.plan_revision,
    )
    return hashlib.sha256(json.dumps(fields, separators=(",", ":")).encode()).hexdigest()


def _sample_monotonic_ns(clock: Callable[[], int]) -> int:
    try:
        value = clock()
    except Exception as exc:
        raise Rejected("authorization monotonic clock unavailable") from exc
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise Rejected("authorization monotonic clock is invalid")
    return value


def _terminal_result(
    outcome: Path,
    *,
    state: str,
    key: str,
    owner_uid: int,
    approval_sha256: str | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "state": state,
        "issue": 113,
        "operation_sha256": key,
        "exit_code": 126,
    }
    if approval_sha256 is not None:
        payload["approval_manifest_sha256"] = approval_sha256
    _write_once(outcome, payload, owner_uid=owner_uid)
    return {
        "status": state,
        "issue": 113,
        "operation_sha256": key,
        "unit_start_proven": False,
        "transfer_performed": False,
    }


def broker_once(
    request: Request,
    *,
    peer_uid: int,
    expected_peer_uid: int,
    verifier: Verifier,
    state_dir: Path,
    runner: Callable[[tuple[str, ...]], int],
    owner_uid: int = 0,
    monotonic_ns: Callable[[], int] = time.monotonic_ns,
) -> dict[str, object]:
    """One-shot transition: deny -> PREPARED durable -> fixed runner -> result.

    A crash leaves PREPARED, never retried. The caller must pass a kernel
    SO_PEERCRED-derived uid; no socket listener is provided in this candidate.
    """
    if os.geteuid() != owner_uid:
        raise Rejected("broker must run under trusted state owner")
    if (
        expected_peer_uid <= 0
        or peer_uid != expected_peer_uid
        or isinstance(peer_uid, bool)
        or isinstance(expected_peer_uid, bool)
    ):
        raise Rejected("peer identity not permitted")
    if request.target_id != TARGET or request.operation not in ALLOWED:
        raise Rejected("unsupported target or fixed operation")
    for field in (
        request.operation_id,
        request.plan_id,
        request.plan_revision,
        request.authorization_reference,
    ):
        if not isinstance(field, str) or not field or len(field) > 256:
            raise Rejected("invalid request field")
    _root_private_dir(state_dir, owner_uid=owner_uid)
    fd = _lock(state_dir / "broker.lock", owner_uid=owner_uid)
    try:
        key = _key(request)
        prepared = state_dir / (key + ".prepared.json")
        outcome = state_dir / (key + ".result.json")
        if prepared.exists() or prepared.is_symlink() or outcome.exists() or outcome.is_symlink():
            raise Rejected("operation has already been prepared; recovery needs separate approval")
        verdict = verifier.verify(
            operation_id=request.operation_id,
            operation=request.operation,
            target_id=request.target_id,
            plan_id=request.plan_id,
            plan_revision=request.plan_revision,
            authorization_reference=request.authorization_reference,
        )
        if getattr(verdict, "authorized", False) is not True:
            raise Rejected("no valid exact action authorization")

        deadline = getattr(verdict, "deadline_monotonic_ns", None)
        if deadline is not None:
            if isinstance(deadline, bool) or not isinstance(deadline, int) or deadline <= 0:
                raise Rejected("authorization deadline is invalid")
            if _sample_monotonic_ns(monotonic_ns) >= deadline:
                raise Rejected("authorization expired before prepare")

        approval_sha256 = getattr(verdict, "approval_sha256", None)
        if approval_sha256 is not None:
            if (
                not isinstance(approval_sha256, str)
                or len(approval_sha256) != 64
                or any(character not in "0123456789abcdef" for character in approval_sha256)
            ):
                raise Rejected("approval manifest digest is invalid")

        prepared_payload: dict[str, object] = {
            "state": "PREPARED",
            "issue": 113,
            "operation_sha256": key,
            "operation": request.operation,
            "target": TARGET,
            "peer_uid": peer_uid,
            "prepared_at": datetime.now(timezone.utc).isoformat(),
        }
        if approval_sha256 is not None:
            prepared_payload["approval_manifest_sha256"] = approval_sha256
        _write_once(prepared, prepared_payload, owner_uid=owner_uid)

        # Everything after PREPARED is non-retryable until independent reconcile.
        if deadline is not None:
            try:
                current_monotonic = _sample_monotonic_ns(monotonic_ns)
            except Rejected:
                return _terminal_result(
                    outcome,
                    state="AUTHORIZATION_CLOCK_UNKNOWN",
                    key=key,
                    owner_uid=owner_uid,
                    approval_sha256=approval_sha256,
                )
            if current_monotonic >= deadline:
                return _terminal_result(
                    outcome,
                    state="AUTHORIZATION_EXPIRED",
                    key=key,
                    owner_uid=owner_uid,
                    approval_sha256=approval_sha256,
                )

        argv = ALLOWED[request.operation]
        try:
            rc = int(runner(argv))
            state = "DISPATCHED" if rc == 0 else "DISPATCH_FAILED"
        except Exception:
            rc = 125
            state = "DISPATCH_UNKNOWN"
        outcome_payload: dict[str, object] = {
            "state": state,
            "issue": 113,
            "operation_sha256": key,
            "exit_code": rc,
        }
        if approval_sha256 is not None:
            outcome_payload["approval_manifest_sha256"] = approval_sha256
        _write_once(outcome, outcome_payload, owner_uid=owner_uid)
        return {
            "status": state,
            "issue": 113,
            "operation_sha256": key,
            "unit_start_proven": False,
            "transfer_performed": False,
        }
    finally:
        os.close(fd)
