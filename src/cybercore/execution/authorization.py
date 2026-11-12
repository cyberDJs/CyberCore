from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import stat
from typing import Callable, Protocol


MAX_APPROVAL_MANIFEST_BYTES = 8_192
MAX_APPROVAL_TTL_SECONDS = 3_600
_REQUIRED_APPROVAL_KEYS = frozenset(
    {
        "schema_version",
        "approval_id",
        "operation_id",
        "operation",
        "target_id",
        "plan_id",
        "plan_revision",
        "authorization_reference_sha256",
        "issued_at",
        "expires_at",
    }
)
NowCallable = Callable[[], datetime]


@dataclass(frozen=True)
class ExecutionAuthorizationCheck:
    authorized: bool
    reason: str


class ExecutionAuthorizationVerifier(Protocol):
    def verify(
        self,
        *,
        operation_id: str,
        operation: str,
        target_id: str,
        plan_id: str,
        plan_revision: str,
        authorization_reference: str,
    ) -> ExecutionAuthorizationCheck: ...


class DenyAllExecutionAuthorizationVerifier:
    def verify(
        self,
        *,
        operation_id: str,
        operation: str,
        target_id: str,
        plan_id: str,
        plan_revision: str,
        authorization_reference: str,
    ) -> ExecutionAuthorizationCheck:
        return ExecutionAuthorizationCheck(
            authorized=False,
            reason="no execution authorization verifier was configured",
        )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_zulu_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("approval timestamps must be UTC Z timestamps")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("approval timestamps must be UTC")
    return parsed


def _required_manifest_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


class FileBoundExecutionAuthorizationVerifier:
    """Verify a short-lived exact action binding from a trusted local manifest.

    The manifest contains only the SHA-256 digest of the raw authorization
    reference. File ownership and directory integrity are the authority
    boundary; the manifest is not a secret.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        required_owner_uid: int = 0,
        now: NowCallable | None = None,
        max_ttl_seconds: int = MAX_APPROVAL_TTL_SECONDS,
    ) -> None:
        if isinstance(required_owner_uid, bool) or required_owner_uid < 0:
            raise ValueError("required_owner_uid must be a non-negative integer")
        if isinstance(max_ttl_seconds, bool) or max_ttl_seconds <= 0:
            raise ValueError("max_ttl_seconds must be positive")
        self.path = Path(path)
        self.required_owner_uid = required_owner_uid
        self._now = now or _utc_now
        self.max_ttl_seconds = max_ttl_seconds

    def _load_manifest(self) -> dict[str, object]:
        parent_info = os.lstat(self.path.parent)
        if not stat.S_ISDIR(parent_info.st_mode):
            raise ValueError("approval parent is not a directory")
        if parent_info.st_uid != self.required_owner_uid:
            raise ValueError("approval parent has unexpected owner")
        if parent_info.st_mode & 0o022:
            raise ValueError("approval parent is writable by an untrusted principal")

        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.path, flags)
        try:
            file_info = os.fstat(fd)
            if not stat.S_ISREG(file_info.st_mode):
                raise ValueError("approval manifest is not a regular file")
            if file_info.st_uid != self.required_owner_uid:
                raise ValueError("approval manifest has unexpected owner")
            if file_info.st_mode & 0o022:
                raise ValueError("approval manifest is writable by an untrusted principal")
            if file_info.st_size <= 0 or file_info.st_size > MAX_APPROVAL_MANIFEST_BYTES:
                raise ValueError("approval manifest size is invalid")

            chunks: list[bytes] = []
            remaining = MAX_APPROVAL_MANIFEST_BYTES + 1
            while remaining > 0:
                chunk = os.read(fd, remaining)
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
        finally:
            os.close(fd)

        if len(raw) > MAX_APPROVAL_MANIFEST_BYTES:
            raise ValueError("approval manifest exceeds the maximum size")
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("approval manifest root must be an object")
        payload: dict[str, object] = dict(value)
        if frozenset(payload) != _REQUIRED_APPROVAL_KEYS:
            raise ValueError("approval manifest fields do not match the exact schema")

        schema_version = payload["schema_version"]
        if isinstance(schema_version, bool) or schema_version != 1:
            raise ValueError("approval manifest schema version is unsupported")

        for key in (
            "approval_id",
            "operation_id",
            "operation",
            "target_id",
            "plan_id",
            "plan_revision",
        ):
            _required_manifest_string(payload, key)

        digest = _required_manifest_string(payload, "authorization_reference_sha256").lower()
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("authorization reference digest is not SHA-256")
        payload["authorization_reference_sha256"] = digest

        issued_at = _parse_zulu_timestamp(payload["issued_at"])
        expires_at = _parse_zulu_timestamp(payload["expires_at"])
        lifetime = expires_at - issued_at
        if lifetime <= timedelta(0) or lifetime > timedelta(seconds=self.max_ttl_seconds):
            raise ValueError("approval validity window is invalid")

        now = self._now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("authorization verifier clock must be timezone-aware")
        now = now.astimezone(timezone.utc)
        if now < issued_at or now >= expires_at:
            raise ValueError("approval manifest is not currently valid")

        return payload

    def verify(
        self,
        *,
        operation_id: str,
        operation: str,
        target_id: str,
        plan_id: str,
        plan_revision: str,
        authorization_reference: str,
    ) -> ExecutionAuthorizationCheck:
        try:
            payload = self._load_manifest()
        except (OSError, ValueError, TypeError, UnicodeError, json.JSONDecodeError):
            return ExecutionAuthorizationCheck(
                authorized=False,
                reason="approval manifest is unavailable, invalid, or outside its validity window",
            )

        expected = {
            "operation_id": operation_id,
            "operation": operation,
            "target_id": target_id,
            "plan_id": plan_id,
            "plan_revision": plan_revision,
        }
        for key, value in expected.items():
            if payload[key] != value:
                return ExecutionAuthorizationCheck(
                    authorized=False,
                    reason="approval manifest does not match the exact governed action",
                )

        supplied_digest = hashlib.sha256(authorization_reference.encode("utf-8")).hexdigest()
        approved_digest = str(payload["authorization_reference_sha256"])
        if not hmac.compare_digest(supplied_digest, approved_digest):
            return ExecutionAuthorizationCheck(
                authorized=False,
                reason="approval reference does not match the bound manifest",
            )

        return ExecutionAuthorizationCheck(
            authorized=True,
            reason=f"bound approval accepted: {payload['approval_id']}",
        )
