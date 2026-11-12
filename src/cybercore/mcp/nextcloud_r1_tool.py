from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from cybercore.execution.authorization import (
    ExecutionAuthorizationVerifier,
    FileBoundExecutionAuthorizationVerifier,
)
from cybercore.execution.models import ExecutionReceipt, GovernedAction
from cybercore.execution.policy import NEXTCLOUD_R1_TARGET
from cybercore.execution.ssh_runner import execute_action


TOOL_NAME = "nextcloud.r1.offhost"
NEXTCLOUD_R1_CLIENT_APPROVAL_PATH = Path(
    "/etc/cyberdjs-room/approvals/nextcloud-r1.json"
)
_ALLOWED_KEYS = frozenset(
    {
        "action",
        "operation_id",
        "plan_id",
        "plan_revision",
        "authorization_reference",
    }
)
_ACTION_TO_OPERATION = {
    "transfer": "nextcloud.r1.offhost.transfer",
    "status": "nextcloud.r1.offhost.status",
    "verify": "nextcloud.r1.offhost.verify",
}

ExecuteCallable = Callable[..., ExecutionReceipt]


def _required_string(arguments: Mapping[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _receipt_payload(receipt: ExecutionReceipt) -> dict[str, object]:
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
        "result": dict(receipt.result) if receipt.result is not None else None,
        "secret_values_recorded": receipt.secret_values_recorded,
    }


def build_nextcloud_r1_handler(
    *,
    authorization_verifier: ExecutionAuthorizationVerifier | None = None,
    executor: ExecuteCallable = execute_action,
) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    def handler(arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if frozenset(arguments) != _ALLOWED_KEYS:
            raise ValueError("Nextcloud R1 tool arguments do not match the exact schema")

        action_name = _required_string(arguments, "action")
        try:
            operation = _ACTION_TO_OPERATION[action_name]
        except KeyError as exc:
            raise ValueError("action must be one of: transfer, status, verify") from exc

        action = GovernedAction(
            operation_id=_required_string(arguments, "operation_id"),
            operation=operation,
            target_id=NEXTCLOUD_R1_TARGET.id,
            plan_id=_required_string(arguments, "plan_id"),
            plan_revision=_required_string(arguments, "plan_revision"),
            authorization_reference=_required_string(arguments, "authorization_reference"),
            arguments={},
        )
        receipt = executor(
            action,
            NEXTCLOUD_R1_TARGET,
            authorization_verifier=authorization_verifier,
        )
        return _receipt_payload(receipt)

    return handler



def build_bound_nextcloud_r1_handler(
    approval_path: str | Path = NEXTCLOUD_R1_CLIENT_APPROVAL_PATH,
) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    return build_nextcloud_r1_handler(
        authorization_verifier=FileBoundExecutionAuthorizationVerifier(approval_path)
    )
