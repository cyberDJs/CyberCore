from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json


class RollbackActionType(str, Enum):
    REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT = "REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT"
    VERIFY_PRIVILEGE_POLICY_REVOKED = "VERIFY_PRIVILEGE_POLICY_REVOKED"
    VERIFY_SYSTEMD_UNIT_MANAGED_EXACT_OR_ABSENT = "VERIFY_SYSTEMD_UNIT_MANAGED_EXACT_OR_ABSENT"
    ENSURE_SYSTEMD_TOMBSTONE_PARENT_TRUSTED = "ENSURE_SYSTEMD_TOMBSTONE_PARENT_TRUSTED"
    INSTALL_SYSTEMD_TOMBSTONE_DROPIN_ATOMIC_DURABLE_TRUSTED_IF_ABSENT_OR_EXACT = (
        "INSTALL_SYSTEMD_TOMBSTONE_DROPIN_ATOMIC_DURABLE_TRUSTED_IF_ABSENT_OR_EXACT"
    )
    VERIFY_SYSTEMD_TOMBSTONE_TRUSTED_EXACT = "VERIFY_SYSTEMD_TOMBSTONE_TRUSTED_EXACT"
    VERIFY_SYSTEMD_TOMBSTONE_EFFECTIVE = "VERIFY_SYSTEMD_TOMBSTONE_EFFECTIVE"
    STOP_SYSTEMD_UNIT_AND_WAIT_IF_PRESENT = "STOP_SYSTEMD_UNIT_AND_WAIT_IF_PRESENT"
    DISABLE_SYSTEMD_UNIT_AND_WAIT_IF_PRESENT = "DISABLE_SYSTEMD_UNIT_AND_WAIT_IF_PRESENT"
    RELOAD_SYSTEMD = "RELOAD_SYSTEMD"
    VALIDATE_SSHD_CONFIG = "VALIDATE_SSHD_CONFIG"
    RELOAD_SSHD = "RELOAD_SSHD"


@dataclass(frozen=True)
class RollbackAction:
    action_id: str
    action_type: RollbackActionType
    target: str = ""
    source_of_truth: str = ""
    mode: str = ""
    owner: str = ""
    group: str = ""


TOMBSTONE_SOURCE = "deploy/cybercore-exec/rollback-wrapper-tombstone.conf"
INSTALL_TOMBSTONE_PARENT = (
    "/etc/systemd/system/"
    "cybercore-vikunja-backup-install.service.d"
)
RUN_TOMBSTONE_PARENT = (
    "/etc/systemd/system/"
    "cybercore-vikunja-backup-run.service.d"
)
INSTALL_TOMBSTONE = (
    "/etc/systemd/system/"
    "cybercore-vikunja-backup-install.service.d/"
    "90-cybercore-rollback-tombstone.conf"
)
RUN_TOMBSTONE = (
    "/etc/systemd/system/"
    "cybercore-vikunja-backup-run.service.d/"
    "90-cybercore-rollback-tombstone.conf"
)


def build_rollback_manifest() -> tuple[RollbackAction, ...]:
    actions = [
        RollbackAction(
            "remove-privilege-policy",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT,
            "/etc/polkit-1/rules.d/60-cybercore-exec.rules",
            "deploy/cybercore-exec/cybercore-exec.policy",
        ),
        RollbackAction(
            "verify-privilege-policy-revoked",
            RollbackActionType.VERIFY_PRIVILEGE_POLICY_REVOKED,
            "/etc/polkit-1/rules.d/60-cybercore-exec.rules",
        ),
        RollbackAction(
            "verify-vikunja-backup-install-wrapper-managed-or-absent",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_MANAGED_EXACT_OR_ABSENT,
            "cybercore-vikunja-backup-install.service",
            "deploy/cybercore-exec/cybercore-vikunja-backup-install.service",
        ),
        RollbackAction(
            "verify-vikunja-backup-run-wrapper-managed-or-absent",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_MANAGED_EXACT_OR_ABSENT,
            "cybercore-vikunja-backup-run.service",
            "deploy/cybercore-exec/cybercore-vikunja-backup-run.service",
        ),
        RollbackAction(
            "ensure-vikunja-backup-install-tombstone-parent-trusted",
            RollbackActionType.ENSURE_SYSTEMD_TOMBSTONE_PARENT_TRUSTED,
            INSTALL_TOMBSTONE_PARENT,
            "",
            "0755",
            "root",
            "root",
        ),
        RollbackAction(
            "install-vikunja-backup-install-tombstone",
            RollbackActionType.INSTALL_SYSTEMD_TOMBSTONE_DROPIN_ATOMIC_DURABLE_TRUSTED_IF_ABSENT_OR_EXACT,
            INSTALL_TOMBSTONE,
            TOMBSTONE_SOURCE,
            "0644",
            "root",
            "root",
        ),
        RollbackAction(
            "verify-vikunja-backup-install-tombstone",
            RollbackActionType.VERIFY_SYSTEMD_TOMBSTONE_TRUSTED_EXACT,
            INSTALL_TOMBSTONE,
            TOMBSTONE_SOURCE,
            "0644",
            "root",
            "root",
        ),
        RollbackAction(
            "ensure-vikunja-backup-run-tombstone-parent-trusted",
            RollbackActionType.ENSURE_SYSTEMD_TOMBSTONE_PARENT_TRUSTED,
            RUN_TOMBSTONE_PARENT,
            "",
            "0755",
            "root",
            "root",
        ),
        RollbackAction(
            "install-vikunja-backup-run-tombstone",
            RollbackActionType.INSTALL_SYSTEMD_TOMBSTONE_DROPIN_ATOMIC_DURABLE_TRUSTED_IF_ABSENT_OR_EXACT,
            RUN_TOMBSTONE,
            TOMBSTONE_SOURCE,
            "0644",
            "root",
            "root",
        ),
        RollbackAction(
            "verify-vikunja-backup-run-tombstone",
            RollbackActionType.VERIFY_SYSTEMD_TOMBSTONE_TRUSTED_EXACT,
            RUN_TOMBSTONE,
            TOMBSTONE_SOURCE,
            "0644",
            "root",
            "root",
        ),
        RollbackAction(
            "systemd-reload-after-tombstone-barrier",
            RollbackActionType.RELOAD_SYSTEMD,
        ),
        RollbackAction(
            "verify-vikunja-backup-install-tombstone-effective",
            RollbackActionType.VERIFY_SYSTEMD_TOMBSTONE_EFFECTIVE,
            "cybercore-vikunja-backup-install.service",
            TOMBSTONE_SOURCE,
        ),
        RollbackAction(
            "verify-vikunja-backup-run-tombstone-effective",
            RollbackActionType.VERIFY_SYSTEMD_TOMBSTONE_EFFECTIVE,
            "cybercore-vikunja-backup-run.service",
            TOMBSTONE_SOURCE,
        ),
        RollbackAction(
            "stop-vikunja-backup-install-wrapper",
            RollbackActionType.STOP_SYSTEMD_UNIT_AND_WAIT_IF_PRESENT,
            "cybercore-vikunja-backup-install.service",
            "deploy/cybercore-exec/cybercore-vikunja-backup-install.service",
        ),
        RollbackAction(
            "verify-vikunja-backup-timer-managed-or-absent",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_MANAGED_EXACT_OR_ABSENT,
            "vikunja-backup.timer",
            "deploy/cybercore-exec/vikunja-backup.timer",
        ),
        RollbackAction(
            "verify-vikunja-backup-service-managed-or-absent",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_MANAGED_EXACT_OR_ABSENT,
            "vikunja-backup.service",
            "deploy/cybercore-exec/vikunja-backup.service",
        ),
        RollbackAction(
            "disable-vikunja-backup-timer",
            RollbackActionType.DISABLE_SYSTEMD_UNIT_AND_WAIT_IF_PRESENT,
            "vikunja-backup.timer",
            "deploy/cybercore-exec/vikunja-backup.timer",
        ),
        RollbackAction(
            "stop-vikunja-backup-run-wrapper",
            RollbackActionType.STOP_SYSTEMD_UNIT_AND_WAIT_IF_PRESENT,
            "cybercore-vikunja-backup-run.service",
            "deploy/cybercore-exec/cybercore-vikunja-backup-run.service",
        ),
        RollbackAction(
            "stop-vikunja-backup-service",
            RollbackActionType.STOP_SYSTEMD_UNIT_AND_WAIT_IF_PRESENT,
            "vikunja-backup.service",
            "deploy/cybercore-exec/vikunja-backup.service",
        ),
        RollbackAction(
            "remove-sshd-config",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT,
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
            "systemd-reload-after-wrapper-removal",
            RollbackActionType.RELOAD_SYSTEMD,
        ),
        RollbackAction(
            "verify-vikunja-backup-install-tombstone-effective-after-removal",
            RollbackActionType.VERIFY_SYSTEMD_TOMBSTONE_EFFECTIVE,
            "cybercore-vikunja-backup-install.service",
            TOMBSTONE_SOURCE,
        ),
        RollbackAction(
            "verify-vikunja-backup-run-tombstone-effective-after-removal",
            RollbackActionType.VERIFY_SYSTEMD_TOMBSTONE_EFFECTIVE,
            "cybercore-vikunja-backup-run.service",
            TOMBSTONE_SOURCE,
        ),
        RollbackAction(
            "remove-vikunja-backup-service-template",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT,
            "/usr/local/libexec/cybercore-exec/vikunja-backup.service.template",
            "deploy/cybercore-exec/vikunja-backup.service",
        ),
        RollbackAction(
            "remove-vikunja-backup-timer-template",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT,
            "/usr/local/libexec/cybercore-exec/vikunja-backup.timer.template",
            "deploy/cybercore-exec/vikunja-backup.timer",
        ),
        RollbackAction(
            "remove-vikunja-backup-install",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT,
            "/usr/local/libexec/cybercore-exec/vikunja-backup-install",
            "deploy/cybercore-exec/vikunja-backup-install",
        ),
        RollbackAction(
            "remove-authorization",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT,
            "/usr/local/libexec/cybercore-exec/authorization.py",
            "src/cybercore/execution/authorization.py",
        ),
        RollbackAction(
            "remove-dispatcher",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT,
            "/usr/local/libexec/cybercore-exec/dispatcher.py",
            "src/cybercore/execution/server/dispatcher.py",
        ),
        RollbackAction(
            "remove-inventory",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT,
            "/usr/local/libexec/cybercore-exec/inventory.py",
            "src/cybercore/execution/server/inventory.py",
        ),
        RollbackAction(
            "remove-operations",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT,
            "/usr/local/libexec/cybercore-exec/operations.py",
            "src/cybercore/execution/server/operations.py",
        ),
        RollbackAction(
            "remove-protocol",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT,
            "/usr/local/libexec/cybercore-exec/protocol.py",
            "src/cybercore/execution/server/protocol.py",
        ),
    ]
    return tuple(actions)


def main() -> int:
    payload = {
        "status": "PROPOSED",
        "operation_id": "WB0038H-CANONICAL-ROLLBACK-HARDENING",
        "actions": [asdict(action) for action in build_rollback_manifest()],
        "service_user_removed": False,
        "execution_required": True,
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
