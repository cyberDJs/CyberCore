from __future__ import annotations

from dataclasses import dataclass

from cybercore.execution.models import ExecutionTarget, GovernedAction


VIKUNJA_TARGET = ExecutionTarget(
    id="tasks.cyberdjs.org",
    hostname="162.35.117.219",
    ssh_user="cybercore-exec",
)

NEXTCLOUD_R1_TARGET = ExecutionTarget(
    id="cyberskills-vps",
    hostname="162.35.186.106",
    ssh_user="cybercore-exec",
)

_CANONICAL_TARGETS = {
    VIKUNJA_TARGET.id: VIKUNJA_TARGET,
    NEXTCLOUD_R1_TARGET.id: NEXTCLOUD_R1_TARGET,
}

_OPERATION_TARGET_IDS: dict[str, frozenset[str]] = {
    "system.inventory": frozenset(_CANONICAL_TARGETS),
    "vikunja.backup.install": frozenset({VIKUNJA_TARGET.id}),
    "vikunja.backup.run": frozenset({VIKUNJA_TARGET.id}),
    "vikunja.backup.status": frozenset({VIKUNJA_TARGET.id}),
    "vikunja.health.verify": frozenset({VIKUNJA_TARGET.id}),
    "nextcloud.r1.offhost.transfer": frozenset({NEXTCLOUD_R1_TARGET.id}),
    "nextcloud.r1.offhost.status": frozenset({NEXTCLOUD_R1_TARGET.id}),
    "nextcloud.r1.offhost.verify": frozenset({NEXTCLOUD_R1_TARGET.id}),
}

SUPPORTED_OPERATIONS = frozenset(_OPERATION_TARGET_IDS)

_MUTATING_OPERATIONS = frozenset(
    {
        "vikunja.backup.install",
        "vikunja.backup.run",
        "nextcloud.r1.offhost.transfer",
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


def canonical_target(target_id: str) -> ExecutionTarget | None:
    return _CANONICAL_TARGETS.get(target_id)


def evaluate_action(action: GovernedAction, target: ExecutionTarget) -> PolicyDecision:
    canonical = canonical_target(target.id)
    if canonical is None or target != canonical:
        return PolicyDecision(False, "execution target is not a canonical governed target")
    if action.target_id != target.id:
        return PolicyDecision(False, "action target does not match execution target")
    if action.operation not in SUPPORTED_OPERATIONS:
        return PolicyDecision(False, "operation is not supported by governed execution")
    if target.id not in _OPERATION_TARGET_IDS[action.operation]:
        return PolicyDecision(False, "operation is not allowed for the selected target")
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
