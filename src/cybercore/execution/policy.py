from __future__ import annotations

from dataclasses import dataclass

from cybercore.execution.models import ExecutionTarget, GovernedAction


VIKUNJA_TARGET = ExecutionTarget(
    id="tasks.cyberdjs.org",
    hostname="162.35.117.219",
    ssh_user="cybercore-exec",
)

SUPPORTED_OPERATIONS = frozenset(
    {
        "vikunja.backup.install",
        "vikunja.backup.run",
        "vikunja.backup.status",
        "vikunja.health.verify",
    }
)

_MUTATING_OPERATIONS = frozenset({"vikunja.backup.install", "vikunja.backup.run"})
_ALLOWED_ARGUMENTS: dict[str, frozenset[str]] = {
    "vikunja.backup.install": frozenset(),
    "vikunja.backup.run": frozenset(),
    "vikunja.backup.status": frozenset(),
    "vikunja.health.verify": frozenset(),
}


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    mutating: bool = False


def evaluate_action(action: GovernedAction, target: ExecutionTarget) -> PolicyDecision:
    if target != VIKUNJA_TARGET:
        return PolicyDecision(False, "execution target is not the canonical WB-0037 target")
    if action.target_id != target.id:
        return PolicyDecision(False, "action target does not match execution target")
    if action.operation not in SUPPORTED_OPERATIONS:
        return PolicyDecision(False, "operation is not supported by WB-0037 V1")
    if not action.operation_id.strip():
        return PolicyDecision(False, "operation_id is required")
    if not action.has_bound_plan:
        return PolicyDecision(False, "exact plan id and revision are required")
    if not action.authorization_reference.strip():
        return PolicyDecision(False, "authorization reference is required")

    allowed_keys = _ALLOWED_ARGUMENTS[action.operation]
    supplied_keys = frozenset(action.arguments)
    if supplied_keys != allowed_keys:
        return PolicyDecision(False, "operation arguments do not match the exact allowlist")

    mutating = action.operation in _MUTATING_OPERATIONS
    return PolicyDecision(True, "bounded action accepted", mutating=mutating)
