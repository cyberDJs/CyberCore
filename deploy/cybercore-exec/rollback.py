from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json


class RollbackActionType(str, Enum):
    REMOVE_MANAGED_FILE_IF_EXACT = "REMOVE_MANAGED_FILE_IF_EXACT"
    VERIFY_PRIVILEGE_POLICY_REVOKED = "VERIFY_PRIVILEGE_POLICY_REVOKED"
    VERIFY_SYSTEMD_UNIT_MANAGED_EXACT = "VERIFY_SYSTEMD_UNIT_MANAGED_EXACT"
    VERIFY_SYSTEMD_UNIT_MANAGED_EXACT_OR_ABSENT = "VERIFY_SYSTEMD_UNIT_MANAGED_EXACT_OR_ABSENT"
    MASK_SYSTEMD_UNIT_RUNTIME = "MASK_SYSTEMD_UNIT_RUNTIME"
    VERIFY_SYSTEMD_UNIT_MASKED_RUNTIME = "VERIFY_SYSTEMD_UNIT_MASKED_RUNTIME"
    STOP_SYSTEMD_UNIT_AND_WAIT = "STOP_SYSTEMD_UNIT_AND_WAIT"
    DISABLE_SYSTEMD_UNIT_AND_WAIT_IF_PRESENT = "DISABLE_SYSTEMD_UNIT_AND_WAIT_IF_PRESENT"
    STOP_SYSTEMD_UNIT_AND_WAIT_IF_PRESENT = "STOP_SYSTEMD_UNIT_AND_WAIT_IF_PRESENT"
    MASK_SYSTEMD_UNIT_PERSISTENT = "MASK_SYSTEMD_UNIT_PERSISTENT"
    VERIFY_SYSTEMD_UNIT_MASKED_PERSISTENT = "VERIFY_SYSTEMD_UNIT_MASKED_PERSISTENT"
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
            "verify-vikunja-backup-install-wrapper-managed",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_MANAGED_EXACT,
            "cybercore-vikunja-backup-install.service",
            "deploy/cybercore-exec/cybercore-vikunja-backup-install.service",
        ),
        RollbackAction(
            "verify-vikunja-backup-run-wrapper-managed",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_MANAGED_EXACT,
            "cybercore-vikunja-backup-run.service",
            "deploy/cybercore-exec/cybercore-vikunja-backup-run.service",
        ),
        RollbackAction(
            "runtime-mask-vikunja-backup-install-wrapper",
            RollbackActionType.MASK_SYSTEMD_UNIT_RUNTIME,
            "cybercore-vikunja-backup-install.service",
        ),
        RollbackAction(
            "verify-vikunja-backup-install-wrapper-runtime-masked",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_MASKED_RUNTIME,
            "cybercore-vikunja-backup-install.service",
        ),
        RollbackAction(
            "runtime-mask-vikunja-backup-run-wrapper",
            RollbackActionType.MASK_SYSTEMD_UNIT_RUNTIME,
            "cybercore-vikunja-backup-run.service",
        ),
        RollbackAction(
            "verify-vikunja-backup-run-wrapper-runtime-masked",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_MASKED_RUNTIME,
            "cybercore-vikunja-backup-run.service",
        ),
        RollbackAction(
            "stop-vikunja-backup-install-wrapper",
            RollbackActionType.STOP_SYSTEMD_UNIT_AND_WAIT,
            "cybercore-vikunja-backup-install.service",
            "deploy/cybercore-exec/cybercore-vikunja-backup-install.service",
        ),
        RollbackAction(
            "stop-vikunja-backup-run-wrapper",
            RollbackActionType.STOP_SYSTEMD_UNIT_AND_WAIT,
            "cybercore-vikunja-backup-run.service",
            "deploy/cybercore-exec/cybercore-vikunja-backup-run.service",
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
            "stop-vikunja-backup-service",
            RollbackActionType.STOP_SYSTEMD_UNIT_AND_WAIT_IF_PRESENT,
            "vikunja-backup.service",
            "deploy/cybercore-exec/vikunja-backup.service",
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
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT,
            "/etc/systemd/system/cybercore-vikunja-backup-install.service",
            "deploy/cybercore-exec/cybercore-vikunja-backup-install.service",
        ),
        RollbackAction(
            "remove-vikunja-backup-run-unit",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT,
            "/etc/systemd/system/cybercore-vikunja-backup-run.service",
            "deploy/cybercore-exec/cybercore-vikunja-backup-run.service",
        ),
        RollbackAction("systemd-reload-after-wrapper-removal", RollbackActionType.RELOAD_SYSTEMD),
        RollbackAction(
            "persistent-mask-vikunja-backup-install-wrapper",
            RollbackActionType.MASK_SYSTEMD_UNIT_PERSISTENT,
            "cybercore-vikunja-backup-install.service",
        ),
        RollbackAction(
            "persistent-mask-vikunja-backup-run-wrapper",
            RollbackActionType.MASK_SYSTEMD_UNIT_PERSISTENT,
            "cybercore-vikunja-backup-run.service",
        ),
        RollbackAction("systemd-reload-after-persistent-mask", RollbackActionType.RELOAD_SYSTEMD),
        RollbackAction(
            "verify-vikunja-backup-install-wrapper-persistent-masked",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_MASKED_PERSISTENT,
            "cybercore-vikunja-backup-install.service",
        ),
        RollbackAction(
            "verify-vikunja-backup-run-wrapper-persistent-masked",
            RollbackActionType.VERIFY_SYSTEMD_UNIT_MASKED_PERSISTENT,
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
        "operation_id": "WB0038G-CONSOLIDATED-ROLLBACK",
        "actions": [asdict(action) for action in build_rollback_manifest()],
        "service_user_removed": False,
        "execution_required": True,
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
