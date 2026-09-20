from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json


class RollbackActionType(str, Enum):
    REMOVE_MANAGED_FILE_IF_EXACT = "REMOVE_MANAGED_FILE_IF_EXACT"
    REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT = "REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT"
    VERIFY_PRIVILEGE_POLICY_REVOKED = "VERIFY_PRIVILEGE_POLICY_REVOKED"
    MASK_SYSTEMD_UNIT_RUNTIME = "MASK_SYSTEMD_UNIT_RUNTIME"
    VERIFY_SYSTEMD_UNIT_MASKED = "VERIFY_SYSTEMD_UNIT_MASKED"
    STOP_SYSTEMD_UNIT_IF_PRESENT = "STOP_SYSTEMD_UNIT_IF_PRESENT"
    VERIFY_SYSTEMD_UNIT_INACTIVE_OR_ABSENT = "VERIFY_SYSTEMD_UNIT_INACTIVE_OR_ABSENT"
    INSTALL_SYSTEMD_TOMBSTONE_DROPIN_IF_ABSENT_OR_EXACT = (
        "INSTALL_SYSTEMD_TOMBSTONE_DROPIN_IF_ABSENT_OR_EXACT"
    )
    VERIFY_SYSTEMD_TOMBSTONE_DROPIN_EXACT = "VERIFY_SYSTEMD_TOMBSTONE_DROPIN_EXACT"
    RELOAD_SYSTEMD = "RELOAD_SYSTEMD"
    VALIDATE_SSHD_CONFIG = "VALIDATE_SSHD_CONFIG"
    RELOAD_SSHD = "RELOAD_SSHD"


@dataclass(frozen=True)
class RollbackAction:
    action_id: str
    action_type: RollbackActionType
    target: str = ""
    source_of_truth: str = ""


def build_rollback_manifest() -> tuple[RollbackAction, ...]:
    actions = [
        RollbackAction(
            "remove-privilege-policy",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT,
            "/etc/polkit-1/rules.d/60-cybercore-exec.rules",
            "deploy/cybercore-exec/cybercore-exec.policy",
        ),
        RollbackAction(
            "verify-privilege-policy-revoked",
            RollbackActionType.VERIFY_PRIVILEGE_POLICY_REVOKED,
            "/etc/polkit-1/rules.d/60-cybercore-exec.rules",
        ),
        RollbackAction(
            "mask-vikunja-backup-install-unit-runtime",
            RollbackActionType.MASK_SYSTEMD_UNIT_RUNTIME,
            "cybercore-vikunja-backup-install.service",
        ),
        RollbackAction(
            "verify-vikunja-backup-install-unit-runtime-masked",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_MASKED,
            "cybercore-vikunja-backup-install.service",
        ),
        RollbackAction(
            "mask-vikunja-backup-run-unit-runtime",
            RollbackActionType.MASK_SYSTEMD_UNIT_RUNTIME,
            "cybercore-vikunja-backup-run.service",
        ),
        RollbackAction(
            "verify-vikunja-backup-run-unit-runtime-masked",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_MASKED,
            "cybercore-vikunja-backup-run.service",
        ),
        RollbackAction(
            "stop-vikunja-backup-install-unit",
            RollbackActionType.STOP_SYSTEMD_UNIT_IF_PRESENT,
            "cybercore-vikunja-backup-install.service",
        ),
        RollbackAction(
            "verify-vikunja-backup-install-unit-inactive",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_INACTIVE_OR_ABSENT,
            "cybercore-vikunja-backup-install.service",
        ),
        RollbackAction(
            "stop-vikunja-backup-run-unit",
            RollbackActionType.STOP_SYSTEMD_UNIT_IF_PRESENT,
            "cybercore-vikunja-backup-run.service",
        ),
        RollbackAction(
            "verify-vikunja-backup-run-unit-inactive",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_INACTIVE_OR_ABSENT,
            "cybercore-vikunja-backup-run.service",
        ),
        RollbackAction(
            "stop-vikunja-backup-timer",
            RollbackActionType.STOP_SYSTEMD_UNIT_IF_PRESENT,
            "vikunja-backup.timer",
        ),
        RollbackAction(
            "verify-vikunja-backup-timer-inactive",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_INACTIVE_OR_ABSENT,
            "vikunja-backup.timer",
        ),
        RollbackAction(
            "stop-vikunja-backup-service",
            RollbackActionType.STOP_SYSTEMD_UNIT_IF_PRESENT,
            "vikunja-backup.service",
        ),
        RollbackAction(
            "verify-vikunja-backup-service-inactive",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_INACTIVE_OR_ABSENT,
            "vikunja-backup.service",
        ),
        RollbackAction(
            "remove-sshd-config",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT,
            "/etc/ssh/sshd_config.d/60-cybercore-exec.conf",
            "deploy/cybercore-exec/cybercore-exec.subsystem.conf",
        ),
        RollbackAction("sshd-validate", RollbackActionType.VALIDATE_SSHD_CONFIG),
        RollbackAction("sshd-reload", RollbackActionType.RELOAD_SSHD),
        RollbackAction(
            "remove-vikunja-backup-install-unit",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT,
            "/etc/systemd/system/cybercore-vikunja-backup-install.service",
            "deploy/cybercore-exec/cybercore-vikunja-backup-install.service",
        ),
        RollbackAction(
            "remove-vikunja-backup-run-unit",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT,
            "/etc/systemd/system/cybercore-vikunja-backup-run.service",
            "deploy/cybercore-exec/cybercore-vikunja-backup-run.service",
        ),
        RollbackAction(
            "install-vikunja-backup-install-unit-tombstone",
            RollbackActionType.INSTALL_SYSTEMD_TOMBSTONE_DROPIN_IF_ABSENT_OR_EXACT,
            "/etc/systemd/system/cybercore-vikunja-backup-install.service.d/90-cybercore-rollback-tombstone.conf",
            "deploy/cybercore-exec/rollback-wrapper-tombstone.conf",
        ),
        RollbackAction(
            "verify-vikunja-backup-install-unit-tombstone",
            RollbackActionType.VERIFY_SYSTEMD_TOMBSTONE_DROPIN_EXACT,
            "/etc/systemd/system/cybercore-vikunja-backup-install.service.d/90-cybercore-rollback-tombstone.conf",
            "deploy/cybercore-exec/rollback-wrapper-tombstone.conf",
        ),
        RollbackAction(
            "install-vikunja-backup-run-unit-tombstone",
            RollbackActionType.INSTALL_SYSTEMD_TOMBSTONE_DROPIN_IF_ABSENT_OR_EXACT,
            "/etc/systemd/system/cybercore-vikunja-backup-run.service.d/90-cybercore-rollback-tombstone.conf",
            "deploy/cybercore-exec/rollback-wrapper-tombstone.conf",
        ),
        RollbackAction(
            "verify-vikunja-backup-run-unit-tombstone",
            RollbackActionType.VERIFY_SYSTEMD_TOMBSTONE_DROPIN_EXACT,
            "/etc/systemd/system/cybercore-vikunja-backup-run.service.d/90-cybercore-rollback-tombstone.conf",
            "deploy/cybercore-exec/rollback-wrapper-tombstone.conf",
        ),
        RollbackAction("systemd-reload-after-tombstones", RollbackActionType.RELOAD_SYSTEMD),
        RollbackAction(
            "verify-vikunja-backup-install-runtime-mask-after-reload",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_MASKED,
            "cybercore-vikunja-backup-install.service",
        ),
        RollbackAction(
            "verify-vikunja-backup-run-runtime-mask-after-reload",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_MASKED,
            "cybercore-vikunja-backup-run.service",
        ),
        RollbackAction(
            "remove-vikunja-backup-install",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT,
            "/usr/local/libexec/cybercore-exec/vikunja-backup-install",
            "deploy/cybercore-exec/vikunja-backup-install",
        ),
        RollbackAction(
            "remove-authorization",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT,
            "/usr/local/libexec/cybercore-exec/authorization.py",
            "src/cybercore/execution/authorization.py",
        ),
        RollbackAction(
            "remove-dispatcher",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT,
            "/usr/local/libexec/cybercore-exec/dispatcher.py",
            "src/cybercore/execution/server/dispatcher.py",
        ),
        RollbackAction(
            "remove-operations",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT,
            "/usr/local/libexec/cybercore-exec/operations.py",
            "src/cybercore/execution/server/operations.py",
        ),
        RollbackAction(
            "remove-protocol",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT,
            "/usr/local/libexec/cybercore-exec/protocol.py",
            "src/cybercore/execution/server/protocol.py",
        ),
    ]
    return tuple(actions)


def main() -> int:
    payload = {
        "status": "PROPOSED",
        "operation_id": "WB0038E-BOOTSTRAP-ROLLBACK",
        "actions": [asdict(action) for action in build_rollback_manifest()],
        "service_user_removed": False,
        "execution_required": True,
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
