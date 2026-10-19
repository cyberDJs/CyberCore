"""Pure wire adapters for CyberHIVE node checks and Nexus action receipts.

No network or filesystem I/O, and no authority to dispatch node actions.
The caller must run the Action Kernel policy before using these functions.
"""

from __future__ import annotations

from typing import Any

from cybercore.action_kernel import ExecutionReceipt, TaskRequest

NEXUS_ACTION_VERSION = "action/v1"


def to_hive_health_dry_run(request: TaskRequest, *, trusted_actor: str) -> dict[str, Any]:
    """Produce a strictly read-only, dry-run CyberHIVE AgentActionRequest-shaped payload."""
    if not trusted_actor or request.actor != trusted_actor:
        raise ValueError("actor mismatch")
    if request.capability != "diagnostics.synthetic_status.v1":
        raise ValueError("unsupported capability")
    if request.arguments:
        raise ValueError("arguments prohibited")
    if not request.target_id or not request.task_id or not request.correlation_id:
        raise ValueError("missing identifiers")
    return {
        "id": request.task_id,
        "target_node": request.target_id,
        "action": "health_check",
        "payload": {},
        "dry_run": True,
        "approval_tokens": [],
        "requested_by": trusted_actor,
        "correlation_id": request.correlation_id,
        "created_at": request.requested_at.isoformat(),
    }


def to_nexus_action_result(receipt: ExecutionReceipt) -> dict[str, Any]:
    """Map Action Kernel receipt to Nexus action/v1 result, without inventing provider evidence."""
    status = {
        "EXECUTED": "completed",
        "DENIED": "rejected",
        "FAILED": "failed",
    }.get(receipt.status)
    if status is None:
        raise ValueError("unsupported execution status")
    return {
        "contract": NEXUS_ACTION_VERSION,
        "kind": "result",
        "actionId": receipt.task_id,
        "idempotencyKey": receipt.correlation_id,
        "status": status,
        "startedAt": receipt.policy.evaluated_at.isoformat(),
        "completedAt": receipt.completed_at.isoformat(),
        "providerReceipt": (
            {
                "capability": receipt.capability,
                "targetId": receipt.target_id,
                "reason": receipt.reason,
                "evidenceSha256": receipt.evidence_sha256,
            }
            if status == "completed"
            else None
        ),
        "error": (
            None if status == "completed" else {"code": receipt.reason, "message": receipt.reason}
        ),
    }
