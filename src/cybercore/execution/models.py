from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class ExecutionStatus(str, Enum):
    BLOCKED = "BLOCKED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ExecutionTarget:
    id: str
    hostname: str
    ssh_user: str
    subsystem: str = "cybercore-exec"


@dataclass(frozen=True)
class GovernedAction:
    operation_id: str
    operation: str
    target_id: str
    plan_id: str
    plan_revision: str
    authorization_reference: str
    arguments: Mapping[str, str] = field(default_factory=dict)

    @property
    def has_bound_plan(self) -> bool:
        return bool(self.plan_id.strip() and self.plan_revision.strip())


@dataclass(frozen=True)
class ExecutionReceipt:
    operation_id: str
    operation: str
    target_id: str
    plan_id: str
    plan_revision: str
    authorization_reference: str
    transport_argv: tuple[str, ...]
    started_at: str
    completed_at: str
    exit_code: int
    stdout_sha256: str
    stderr_sha256: str
    status: ExecutionStatus
    mutation_possible: bool
    secret_values_recorded: bool = False
