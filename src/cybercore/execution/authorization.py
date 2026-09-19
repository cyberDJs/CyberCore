from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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
