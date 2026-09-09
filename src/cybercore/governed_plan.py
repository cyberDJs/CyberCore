from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import math
import re


class OperationClass(str, Enum):
    READ_ONLY = "READ_ONLY"
    COMPUTE = "COMPUTE"
    FILE_WRITE = "FILE_WRITE"
    REPO_WRITE = "REPO_WRITE"
    REMOTE_WRITE = "REMOTE_WRITE"
    DEPLOY = "DEPLOY"
    DESTRUCTIVE = "DESTRUCTIVE"
    PRIVILEGED = "PRIVILEGED"
    BLOCKED = "BLOCKED"


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class CommandBinding:
    classification: OperationClass
    argv_prefix: tuple[str, ...]
    exact: bool = False

    def __post_init__(self) -> None:
        if not self.argv_prefix or any(not part for part in self.argv_prefix):
            raise ValueError("command binding argv_prefix must not be empty")
        if any("\0" in part for part in self.argv_prefix):
            raise ValueError("command binding argv_prefix must not contain NUL")
        if self.classification is OperationClass.BLOCKED:
            raise ValueError("BLOCKED cannot be an authorized command binding")


@dataclass(frozen=True, slots=True)
class CommandSpec:
    argv: tuple[str, ...]
    cwd: str
    classification: OperationClass
    timeout_seconds: float = 60.0
    code_sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.argv or not self.argv[0].strip():
            raise ValueError("command argv must contain an executable")
        if any("\0" in arg for arg in self.argv):
            raise ValueError("command argv must not contain NUL")
        if "\0" in self.cwd:
            raise ValueError("command cwd must not contain NUL")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("command timeout must be finite and greater than zero")
        if self.code_sha256 is not None and not _SHA256_RE.fullmatch(self.code_sha256):
            raise ValueError("code_sha256 must be a lowercase SHA-256 hex digest")


@dataclass(frozen=True, slots=True)
class AuthorizationGrant:
    operation_id: str
    canonical_target: str
    allowed_classes: frozenset[OperationClass]
    allowed_command_prefixes: tuple[tuple[str, ...], ...]
    issuer: str
    issued_at: datetime
    expires_at: datetime
    nonce: str
    allowed_command_bindings: tuple[CommandBinding, ...] = ()

    def __post_init__(self) -> None:
        if not self.operation_id.strip():
            raise ValueError("grant operation_id is required")
        if not self.canonical_target.strip():
            raise ValueError("grant canonical_target is required")
        if not self.issuer.strip():
            raise ValueError("grant issuer is required")
        if not self.nonce.strip():
            raise ValueError("grant nonce is required")
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("grant timestamps must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("grant expires_at must be after issued_at")
        if not self.allowed_classes:
            raise ValueError("grant must contain at least one allowed operation class")
        if OperationClass.BLOCKED in self.allowed_classes:
            raise ValueError("BLOCKED cannot be an allowed operation class")
        if not self.allowed_command_prefixes:
            raise ValueError("grant must contain at least one allowed command prefix")
        if any(not prefix for prefix in self.allowed_command_prefixes):
            raise ValueError("allowed command prefixes must not be empty")
        if any("\0" in part for prefix in self.allowed_command_prefixes for part in prefix):
            raise ValueError("allowed command prefixes must not contain NUL")

        if self.allowed_command_bindings:
            allowed_prefixes = set(self.allowed_command_prefixes)
            for binding in self.allowed_command_bindings:
                if binding.classification not in self.allowed_classes:
                    raise ValueError("command binding class is outside allowed_classes")
                if binding.argv_prefix not in allowed_prefixes:
                    raise ValueError("command binding prefix is outside allowed_command_prefixes")

    def is_current(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(timezone.utc)
        return self.issued_at <= current < self.expires_at


@dataclass(frozen=True, slots=True)
class CommandPlan:
    operation_id: str
    canonical_target: str
    commands: tuple[CommandSpec, ...]
    grant: AuthorizationGrant

    def __post_init__(self) -> None:
        if not self.operation_id.strip():
            raise ValueError("plan operation_id is required")
        if not self.canonical_target.strip():
            raise ValueError("plan canonical_target is required")
        if not self.commands:
            raise ValueError("plan must contain at least one command")
