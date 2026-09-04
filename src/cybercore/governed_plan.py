from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import math


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


@dataclass(frozen=True, slots=True)
class CommandSpec:
    argv: tuple[str, ...]
    cwd: str
    classification: OperationClass
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.argv or not self.argv[0].strip():
            raise ValueError("command argv must contain an executable")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("command timeout must be finite and greater than zero")


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
        if not self.allowed_command_prefixes:
            raise ValueError("grant must contain at least one allowed command prefix")
        if any(not prefix for prefix in self.allowed_command_prefixes):
            raise ValueError("allowed command prefixes must not be empty")

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
