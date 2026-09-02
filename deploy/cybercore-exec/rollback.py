from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json


class RollbackActionType(str, Enum):
    REMOVE_MANAGED_FILE_IF_EXACT = "REMOVE_MANAGED_FILE_IF_EXACT"
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
            "remove-sshd-config",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT,
            "/etc/ssh/sshd_config.d/60-cybercore-exec.conf",
            "deploy/cybercore-exec/cybercore-exec.subsystem.conf",
        ),
        RollbackAction("sshd-validate", RollbackActionType.VALIDATE_SSHD_CONFIG),
        RollbackAction("sshd-reload", RollbackActionType.RELOAD_SSHD),
        RollbackAction(
            "remove-privilege-policy",
            RollbackActionType.REMOVE_MANAGED_FILE_IF_EXACT,
            "/etc/sudoers.d/cybercore-exec",
            "deploy/cybercore-exec/cybercore-exec.policy",
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
        "operation_id": "WB0038B-BOOTSTRAP-ROLLBACK",
        "actions": [asdict(action) for action in build_rollback_manifest()],
        "service_user_removed": False,
        "execution_required": True,
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
