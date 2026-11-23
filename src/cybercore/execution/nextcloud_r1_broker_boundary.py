"""Issue #113: accepted-socket and fd-bound approval boundary candidate.

This module still provides no listener, CLI, systemd unit or deployment path.
It consumes one already-accepted AF_UNIX SOCK_SEQPACKET connection, obtains the
peer UID from SO_PEERCRED, validates one root-owned approval manifest through a
trusted directory fd, and then delegates to the inert one-shot broker core.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import os
from pathlib import Path
import socket
import stat
import struct
import threading
import time
from typing import Callable

from cybercore.execution.nextcloud_r1_broker_core import Request, Rejected, broker_once


ISSUE = 113
TARGET = "cyberskills-vps"
ACTION_TO_OPERATION = {
    "transfer": "nextcloud.r1.offhost.transfer",
    "rollback": "nextcloud.r1.offhost.rollback",
}
MAX_APPROVAL_BYTES = 8_192
DEFAULT_MAX_REQUEST_BYTES = 4_096
DEFAULT_MAX_TTL_NS = 120 * 1_000_000_000
_REQUIRED_REQUEST_KEYS = frozenset({"action", "authorization_reference_sha256"})
_REQUIRED_MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "issue",
        "target_id",
        "action",
        "plan_id",
        "plan_revision",
        "operation_id",
        "source_identity",
        "boot_id",
        "issued_monotonic_ns",
        "expires_monotonic_ns",
        "authorization_reference_sha256",
    }
)


@dataclass(frozen=True)
class BoundaryConfig:
    approval_dir: Path
    state_dir: Path
    trust_root: Path
    expected_peer_uid: int
    trusted_owner_uid: int
    plan_id: str
    plan_revision: str
    source_identity: str
    approval_leaf: str = "approval.json"
    max_ttl_ns: int = DEFAULT_MAX_TTL_NS
    max_request_bytes: int = DEFAULT_MAX_REQUEST_BYTES

    def __post_init__(self) -> None:
        for value in (self.approval_dir, self.state_dir, self.trust_root):
            if not isinstance(value, Path) or not value.is_absolute():
                raise ValueError("broker filesystem paths must be absolute Path values")
        if (
            isinstance(self.expected_peer_uid, bool)
            or not isinstance(self.expected_peer_uid, int)
            or self.expected_peer_uid <= 0
        ):
            raise ValueError("expected_peer_uid must be a positive integer")
        if (
            isinstance(self.trusted_owner_uid, bool)
            or not isinstance(self.trusted_owner_uid, int)
            or self.trusted_owner_uid < 0
        ):
            raise ValueError("trusted_owner_uid must be a non-negative integer")
        for name, value in (
            ("plan_id", self.plan_id),
            ("plan_revision", self.plan_revision),
            ("source_identity", self.source_identity),
        ):
            _require_string(value, name)
        if not self.approval_leaf or self.approval_leaf in {".", ".."} or "/" in self.approval_leaf:
            raise ValueError("approval_leaf must be one fixed leaf name")
        if isinstance(self.max_ttl_ns, bool) or not isinstance(self.max_ttl_ns, int):
            raise ValueError("max_ttl_ns must be an integer")
        if self.max_ttl_ns <= 0:
            raise ValueError("max_ttl_ns must be positive")
        if (
            isinstance(self.max_request_bytes, bool)
            or not isinstance(self.max_request_bytes, int)
            or not 128 <= self.max_request_bytes <= 65_536
        ):
            raise ValueError("max_request_bytes is outside the supported range")


@dataclass(frozen=True)
class BoundApproval:
    request: Request
    deadline_monotonic_ns: int
    approval_sha256: str
    authorization_reference_sha256: str


@dataclass(frozen=True)
class BoundaryAuthorizationDecision:
    authorized: bool
    deadline_monotonic_ns: int | None = None
    approval_sha256: str | None = None


class BoundApprovalVerifier:
    def __init__(self, approval: BoundApproval) -> None:
        self._approval = approval

    def verify(
        self,
        *,
        operation_id: str,
        operation: str,
        target_id: str,
        plan_id: str,
        plan_revision: str,
        authorization_reference: str,
    ) -> BoundaryAuthorizationDecision:
        request = self._approval.request
        exact = (
            operation_id == request.operation_id
            and operation == request.operation
            and target_id == request.target_id
            and plan_id == request.plan_id
            and plan_revision == request.plan_revision
        )
        supplied_digest = _require_sha256(
            authorization_reference,
            "authorization_reference_sha256",
        )
        digest_matches = hmac.compare_digest(
            supplied_digest,
            self._approval.authorization_reference_sha256,
        )
        if not exact or not digest_matches:
            return BoundaryAuthorizationDecision(False)
        return BoundaryAuthorizationDecision(
            True,
            deadline_monotonic_ns=self._approval.deadline_monotonic_ns,
            approval_sha256=self._approval.approval_sha256,
        )


def _read_boot_id() -> str:
    with open("/proc/sys/kernel/random/boot_id", "r", encoding="ascii") as handle:
        return handle.read().strip()


def _require_string(value: object, name: str, *, max_length: int = 256) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > max_length
        or any(ord(character) < 0x20 for character in value)
    ):
        raise Rejected(f"{name} is invalid")
    return value


def _require_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise Rejected(f"{name} must be an integer")
    return value


def _require_sha256(value: object, name: str) -> str:
    digest = _require_string(value, name, max_length=64).lower()
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise Rejected(f"{name} is not SHA-256")
    return digest


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise Rejected("duplicate JSON key")
        value[key] = item
    return value


def _decode_object(raw: bytes) -> dict[str, object]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Rejected("invalid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise Rejected("JSON root must be an object")
    return dict(value)


def _validate_directory_fd(fd: int, *, owner_uid: int) -> None:
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode):
        raise Rejected("trusted filesystem component is not a directory")
    if info.st_uid != owner_uid:
        raise Rejected("trusted filesystem component has unexpected owner")
    if info.st_mode & 0o022:
        raise Rejected("trusted filesystem component is writable by an untrusted principal")


def _open_trusted_directory(path: Path, *, trust_root: Path, owner_uid: int) -> int:
    root_parts = trust_root.parts
    path_parts = path.parts
    if len(path_parts) < len(root_parts) or path_parts[: len(root_parts)] != root_parts:
        raise Rejected("approval directory is outside the configured trust root")

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        current = os.open(trust_root, flags)
    except OSError as exc:
        raise Rejected("trust root is unavailable") from exc

    try:
        _validate_directory_fd(current, owner_uid=owner_uid)
        for component in path_parts[len(root_parts) :]:
            if component in {"", ".", ".."}:
                raise Rejected("invalid trusted filesystem component")
            try:
                next_fd = os.open(component, flags, dir_fd=current)
            except OSError as exc:
                raise Rejected("approval directory is unavailable or symlinked") from exc
            try:
                _validate_directory_fd(next_fd, owner_uid=owner_uid)
            except Exception:
                os.close(next_fd)
                raise
            os.close(current)
            current = next_fd
        return current
    except Exception:
        os.close(current)
        raise


def _read_verified_leaf(
    dir_fd: int,
    leaf: str,
    *,
    owner_uid: int,
    max_bytes: int,
) -> bytes:
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        fd = os.open(leaf, flags, dir_fd=dir_fd)
    except OSError as exc:
        raise Rejected("approval manifest is unavailable or symlinked") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise Rejected("approval manifest is not a regular file")
        if info.st_uid != owner_uid:
            raise Rejected("approval manifest has unexpected owner")
        if info.st_mode & 0o022:
            raise Rejected("approval manifest is writable by an untrusted principal")
        if info.st_nlink != 1:
            raise Rejected("approval manifest link count is invalid")
        if info.st_size <= 0 or info.st_size > max_bytes:
            raise Rejected("approval manifest size is invalid")
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining > 0:
            chunk = os.read(fd, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > max_bytes or len(raw) != info.st_size:
            raise Rejected("approval manifest changed or exceeded its size bound")
        return raw
    finally:
        os.close(fd)


class FdBoundApprovalStore:
    def __init__(
        self,
        config: BoundaryConfig,
        *,
        boot_id_provider: Callable[[], str] = _read_boot_id,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self.config = config
        try:
            self._boot_id = _require_string(boot_id_provider(), "boot_id", max_length=128)
        except Exception as exc:
            raise Rejected("boot identity is unavailable") from exc
        self._monotonic_provider = monotonic_ns
        self._clock_lock = threading.Lock()
        self._clock_high_water: int | None = None
        self._clock_invalid = False
        self._dir_fd = _open_trusted_directory(
            config.approval_dir,
            trust_root=config.trust_root,
            owner_uid=config.trusted_owner_uid,
        )

    def close(self) -> None:
        if self._dir_fd >= 0:
            os.close(self._dir_fd)
            self._dir_fd = -1

    def __enter__(self) -> "FdBoundApprovalStore":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def sample_monotonic_ns(self) -> int:
        with self._clock_lock:
            if self._clock_invalid:
                raise Rejected("approval monotonic clock authority is unavailable")
            try:
                value = self._monotonic_provider()
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError("invalid monotonic sample")
                if self._clock_high_water is not None and value < self._clock_high_water:
                    raise ValueError("monotonic clock regressed")
            except Exception as exc:
                self._clock_invalid = True
                raise Rejected("approval monotonic clock authority is unavailable") from exc
            self._clock_high_water = value
            return value

    def load(self, *, action: str, authorization_reference_sha256: str) -> BoundApproval:
        if self._dir_fd < 0:
            raise Rejected("approval store is closed")
        if action not in ACTION_TO_OPERATION:
            raise Rejected("unsupported broker action")
        supplied_digest = _require_sha256(
            authorization_reference_sha256,
            "authorization_reference_sha256",
        )

        raw = _read_verified_leaf(
            self._dir_fd,
            self.config.approval_leaf,
            owner_uid=self.config.trusted_owner_uid,
            max_bytes=MAX_APPROVAL_BYTES,
        )
        payload = _decode_object(raw)
        if frozenset(payload) != _REQUIRED_MANIFEST_KEYS:
            raise Rejected("approval manifest fields do not match the exact schema")

        if _require_int(payload["schema_version"], "schema_version") != 1:
            raise Rejected("approval manifest schema version is unsupported")
        if _require_int(payload["issue"], "issue") != ISSUE:
            raise Rejected("approval manifest issue does not match")
        if _require_string(payload["target_id"], "target_id") != TARGET:
            raise Rejected("approval manifest target does not match")
        if _require_string(payload["action"], "action") != action:
            raise Rejected("approval manifest action does not match")
        if _require_string(payload["plan_id"], "plan_id") != self.config.plan_id:
            raise Rejected("approval manifest plan does not match")
        if _require_string(payload["plan_revision"], "plan_revision") != self.config.plan_revision:
            raise Rejected("approval manifest plan revision does not match")
        if (
            _require_string(payload["source_identity"], "source_identity")
            != self.config.source_identity
        ):
            raise Rejected("approval manifest source identity does not match")
        if _require_string(payload["boot_id"], "boot_id", max_length=128) != self._boot_id:
            raise Rejected("approval manifest belongs to another boot")

        operation_id = _require_string(payload["operation_id"], "operation_id")
        issued = _require_int(payload["issued_monotonic_ns"], "issued_monotonic_ns")
        expires = _require_int(payload["expires_monotonic_ns"], "expires_monotonic_ns")
        if issued < 0 or expires <= issued or expires - issued > self.config.max_ttl_ns:
            raise Rejected("approval monotonic validity window is invalid")
        now = self.sample_monotonic_ns()
        if now < issued or now >= expires:
            raise Rejected("approval manifest is outside its monotonic validity window")

        approved_digest = _require_sha256(
            payload["authorization_reference_sha256"],
            "authorization_reference_sha256",
        )
        if not hmac.compare_digest(supplied_digest, approved_digest):
            raise Rejected("approval reference digest does not match the bound manifest")

        request = Request(
            operation_id=operation_id,
            operation=ACTION_TO_OPERATION[action],
            target_id=TARGET,
            plan_id=self.config.plan_id,
            plan_revision=self.config.plan_revision,
            authorization_reference=supplied_digest,
        )
        return BoundApproval(
            request=request,
            deadline_monotonic_ns=expires,
            approval_sha256=hashlib.sha256(raw).hexdigest(),
            authorization_reference_sha256=approved_digest,
        )


def _peer_uid(client: socket.socket) -> int:
    if not hasattr(socket, "SO_PEERCRED"):
        raise Rejected("SO_PEERCRED is unavailable")
    size = struct.calcsize("3i")
    raw = client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, size)
    _pid, uid, _gid = struct.unpack("3i", raw)
    return int(uid)


def _parse_request(raw: bytes, *, max_bytes: int) -> tuple[str, str]:
    if not raw or len(raw) > max_bytes:
        raise Rejected("broker request size is invalid")
    payload = _decode_object(raw)
    if frozenset(payload) != _REQUIRED_REQUEST_KEYS:
        raise Rejected("broker request fields do not match the exact schema")
    action = _require_string(payload["action"], "action", max_length=32)
    authorization_reference_sha256 = _require_sha256(
        payload["authorization_reference_sha256"],
        "authorization_reference_sha256",
    )
    if action not in ACTION_TO_OPERATION:
        raise Rejected("unsupported broker action")
    return action, authorization_reference_sha256


def _wire_response(client: socket.socket, payload: dict[str, object]) -> None:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sent = client.send(raw)
    if sent != len(raw):
        raise OSError("short broker response")


def handle_accepted_client(
    client: socket.socket,
    *,
    config: BoundaryConfig,
    approval_store: FdBoundApprovalStore,
    runner: Callable[[tuple[str, ...]], int],
) -> dict[str, object]:
    """Handle one already-accepted SOCK_SEQPACKET request and then return."""
    try:
        socket_type = client.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
        if socket_type != socket.SOCK_SEQPACKET:
            raise Rejected("broker requires SOCK_SEQPACKET")
        if os.geteuid() != config.trusted_owner_uid:
            raise Rejected("broker process does not match trusted owner")
        if approval_store.config != config:
            raise Rejected("approval store configuration does not match broker boundary")

        peer_uid = _peer_uid(client)
        if peer_uid != config.expected_peer_uid:
            raise Rejected("peer identity not permitted")

        raw, ancillary, flags, _address = client.recvmsg(config.max_request_bytes + 1, 0)
        if ancillary or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC):
            raise Rejected("broker request transport metadata is invalid")
        action, authorization_reference_sha256 = _parse_request(
            raw,
            max_bytes=config.max_request_bytes,
        )
        approval = approval_store.load(
            action=action,
            authorization_reference_sha256=authorization_reference_sha256,
        )
        result = broker_once(
            approval.request,
            peer_uid=peer_uid,
            expected_peer_uid=config.expected_peer_uid,
            verifier=BoundApprovalVerifier(approval),
            state_dir=config.state_dir,
            runner=runner,
            owner_uid=config.trusted_owner_uid,
            monotonic_ns=approval_store.sample_monotonic_ns,
        )
        response = {
            "ok": result["status"] == "DISPATCHED",
            "status": result["status"],
            "operation_sha256": result["operation_sha256"],
        }
    except Rejected:
        response = {"ok": False, "status": "DENIED"}
    except Exception:
        response = {"ok": False, "status": "ERROR"}

    _wire_response(client, response)
    return response
