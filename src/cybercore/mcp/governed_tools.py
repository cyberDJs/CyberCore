from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from cybercore.execution.authorization import ExecutionAuthorizationVerifier
from cybercore.execution.models import GovernedAction
from cybercore.execution.policy import NEXTCLOUD_R1_TARGET
from cybercore.execution.ssh_runner import execute_action

NEXTCLOUD_R1_TOOL = "governed.nextcloud_r1_offhost_transfer"
_REQUIRED_ARGUMENTS = frozenset(
    {"operation_id", "plan_id", "plan_revision", "authorization_reference"}
)


def _required_string(arguments: Mapping[str, Any], name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def build_nextcloud_r1_tool_handler(
    authorization_verifier: ExecutionAuthorizationVerifier,
) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    def invoke(arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if frozenset(arguments) != _REQUIRED_ARGUMENTS:
            raise ValueError("governed Nextcloud R1 arguments do not match the exact schema")
        action = GovernedAction(
            operation_id=_required_string(arguments, "operation_id"),
            operation="nextcloud.r1.offhost.transfer",
            target_id=NEXTCLOUD_R1_TARGET.id,
            plan_id=_required_string(arguments, "plan_id"),
            plan_revision=_required_string(arguments, "plan_revision"),
            authorization_reference=_required_string(arguments, "authorization_reference"),
            arguments={},
        )
        receipt = execute_action(
            action,
            NEXTCLOUD_R1_TARGET,
            authorization_verifier=authorization_verifier,
        )
        return {
            "operation_id": receipt.operation_id,
            "operation": receipt.operation,
            "target_id": receipt.target_id,
            "plan_id": receipt.plan_id,
            "plan_revision": receipt.plan_revision,
            "authorization_reference_sha256": receipt.authorization_reference_sha256,
            "started_at": receipt.started_at,
            "completed_at": receipt.completed_at,
            "exit_code": receipt.exit_code,
            "stdout_sha256": receipt.stdout_sha256,
            "stderr_sha256": receipt.stderr_sha256,
            "status": receipt.status.value,
            "mutation_possible": receipt.mutation_possible,
            "secret_values_recorded": receipt.secret_values_recorded,
        }

    return invoke
