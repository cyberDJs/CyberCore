from __future__ import annotations

from dataclasses import dataclass

from cybercore.execution.models import ExecutionTarget, GovernedAction


VIKUNJA_TARGET = ExecutionTarget(
    id="tasks.cyberdjs.org",
    hostname="162.35.117.219",
    ssh_user="cybercore-exec",
)
NEXTCLOUD_R1_TARGET = ExecutionTarget(
    id="cyberskills-vps-nextcloud-r1",
    hostname="162.35.186.106",
    ssh_user="cybercore-exec",
)

_OPERATION_TARGETS = {
    "system.inventory": VIKUNJA_TARGET,
    "vikunja.backup.install": VIKUNJA_TARGET,
    "vikunja.backup.run": VIKUNJA_TARGET,
    "vikunja.backup.status": VIKUNJA_TARGET,
    "vikunja.health.verify": VIKUNJA_TARGET,
    "nextcloud.r1.offhost.transfer": NEXTCLOUD_R1_TARGET,
    "nextcloud.r1.offhost.rollback": NEXTCLOUD_R1_TARGET,
}
SUPPORTED_OPERATIONS = frozenset(_OPERATION_TARGETS)

_MUTATING_OPERATIONS = frozenset(
    {
        "vikunja.backup.install",
        "vikunja.backup.run",
        "nextcloud.r1.offhost.transfer",
        "nextcloud.r1.offhost.rollback",
    }
)
_ALLOWED_ARGUMENTS: dict[str, frozenset[str]] = {
    operation: frozenset() for operation in SUPPORTED_OPERATIONS
}


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    mutating: bool = False


def evaluate_action(action: GovernedAction, target: ExecutionTarget) -> PolicyDecision:
    expected_target = _OPERATION_TARGETS.get(action.operation)
    if expected_target is None:
        return PolicyDecision(False, "operation is not supported by governed execution policy")
    if target != expected_target:
        return PolicyDecision(False, "execution target is not canonical for this operation")
    if action.target_id != expected_target.id:
        return PolicyDecision(False, "action target does not match execution target")
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
