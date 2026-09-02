from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json


SERVICE_USER = "cybercore-exec"


class BootstrapActionType(str, Enum):
    INSTALL_SERVER_FILE = "INSTALL_SERVER_FILE"
    INSTALL_SSHD_CONFIG = "INSTALL_SSHD_CONFIG"
    INSTALL_PRIVILEGE_POLICY = "INSTALL_PRIVILEGE_POLICY"
    ENSURE_SERVICE_IDENTITY = "ENSURE_SERVICE_IDENTITY"
    VALIDATE_PRIVILEGE_POLICY = "VALIDATE_PRIVILEGE_POLICY"
    VALIDATE_SSHD_CONFIG = "VALIDATE_SSHD_CONFIG"
    RELOAD_SSHD = "RELOAD_SSHD"


@dataclass(frozen=True)
class BootstrapAction:
    action_id: str
    action_type: BootstrapActionType
    source: str = ""
    destination: str = ""
    mode: str = ""


def build_install_manifest() -> tuple[BootstrapAction, ...]:
    actions = [
        BootstrapAction(
            "server-dispatcher",
            BootstrapActionType.INSTALL_SERVER_FILE,
            "src/cybercore/execution/server/dispatcher.py",
            "/usr/local/libexec/cybercore-exec/dispatcher.py",
            "0755",
        ),
        BootstrapAction(
            "server-operations",
            BootstrapActionType.INSTALL_SERVER_FILE,
            "src/cybercore/execution/server/operations.py",
            "/usr/local/libexec/cybercore-exec/operations.py",
            "0644",
        ),
        BootstrapAction(
            "server-protocol",
            BootstrapActionType.INSTALL_SERVER_FILE,
            "src/cybercore/execution/server/protocol.py",
            "/usr/local/libexec/cybercore-exec/protocol.py",
            "0644",
        ),
        BootstrapAction(
            "vikunja-backup-install",
            BootstrapActionType.INSTALL_SERVER_FILE,
            "deploy/cybercore-exec/vikunja-backup-install",
            "/usr/local/libexec/cybercore-exec/vikunja-backup-install",
            "0755",
        ),
        BootstrapAction(
            "sshd-config",
            BootstrapActionType.INSTALL_SSHD_CONFIG,
            "deploy/cybercore-exec/cybercore-exec.subsystem.conf",
            "/etc/ssh/sshd_config.d/60-cybercore-exec.conf",
            "0644",
        ),
        BootstrapAction(
            "privilege-policy",
            BootstrapActionType.INSTALL_PRIVILEGE_POLICY,
            "deploy/cybercore-exec/cybercore-exec.policy",
            "/etc/polkit-1/rules.d/60-cybercore-exec.rules",
            "0644",
        ),
        BootstrapAction("service-identity", BootstrapActionType.ENSURE_SERVICE_IDENTITY),
        BootstrapAction("policy-validate", BootstrapActionType.VALIDATE_PRIVILEGE_POLICY),
        BootstrapAction("sshd-validate", BootstrapActionType.VALIDATE_SSHD_CONFIG),
        BootstrapAction("sshd-reload", BootstrapActionType.RELOAD_SSHD),
    ]
    return tuple(actions)


def main() -> int:
    payload = {
        "status": "PROPOSED",
        "operation_id": "WB0038B-BOOTSTRAP-INSTALLER",
        "service_user": SERVICE_USER,
        "actions": [asdict(action) for action in build_install_manifest()],
        "a6_executed": False,
        "execution_required": True,
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
