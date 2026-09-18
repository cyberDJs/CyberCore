from __future__ import annotations

from dataclasses import asdict, dataclass

from cybercore.governed_plan import OperationClass


@dataclass(frozen=True, slots=True)
class CommandReceipt:
    argv: tuple[str, ...]
    cwd: str
    classification: OperationClass
    started_at: str
    finished_at: str
    exit_code: int | None
    stdout_sha256: str
    stderr_sha256: str
    timed_out: bool

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["classification"] = self.classification.value
        return payload


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    operation_id: str
    canonical_target: str
    commands: tuple[CommandReceipt, ...]
    status: str
    verified: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.operation_id,
            "canonical_target": self.canonical_target,
            "commands": [command.as_dict() for command in self.commands],
            "status": self.status,
            "verified": self.verified,
        }
