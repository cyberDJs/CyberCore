from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


MAX_REQUEST_BYTES = 16_384
_TARGET_ID = "tasks.cyberdjs.org"
_REQUIRED_KEYS = frozenset(
    {
        "operation_id",
        "operation",
        "target_id",
        "plan_id",
        "plan_revision",
        "authorization_reference",
        "arguments",
    }
)


class RequestValidationError(ValueError):
    """Raised when an inbound subsystem request fails the strict protocol contract."""


@dataclass(frozen=True)
class ServerRequest:
    operation_id: str
    operation: str
    target_id: str
    plan_id: str
    plan_revision: str
    authorization_reference: str
    arguments: Mapping[str, str]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ServerRequest":
        if frozenset(value) != _REQUIRED_KEYS:
            raise RequestValidationError("request fields do not match the exact protocol schema")

        string_fields = (
            "operation_id",
            "operation",
            "target_id",
            "plan_id",
            "plan_revision",
            "authorization_reference",
        )
        parsed: dict[str, str] = {}
        for field_name in string_fields:
            field_value = value[field_name]
            if not isinstance(field_value, str) or not field_value.strip():
                raise RequestValidationError(f"{field_name} must be a non-empty string")
            parsed[field_name] = field_value

        arguments = value["arguments"]
        if not isinstance(arguments, dict):
            raise RequestValidationError("arguments must be an object")
        if arguments:
            raise RequestValidationError("free-form operation arguments are not supported")
        if parsed["target_id"] != _TARGET_ID:
            raise RequestValidationError("request target is not the canonical server target")

        return cls(arguments={}, **parsed)


@dataclass(frozen=True)
class ServerReceipt:
    operation_id: str
    operation: str
    target_id: str
    plan_id: str
    plan_revision: str
    authorization_reference: str
    started_at: str
    completed_at: str
    exit_code: int
    stdout_sha256: str
    stderr_sha256: str
    status: str
    mutation_possible: bool
    secret_values_recorded: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.operation_id,
            "operation": self.operation,
            "target_id": self.target_id,
            "plan_id": self.plan_id,
            "plan_revision": self.plan_revision,
            "authorization_reference": self.authorization_reference,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "exit_code": self.exit_code,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "status": self.status,
            "mutation_possible": self.mutation_possible,
            "secret_values_recorded": self.secret_values_recorded,
        }
