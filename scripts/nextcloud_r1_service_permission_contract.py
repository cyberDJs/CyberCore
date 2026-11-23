#!/usr/bin/env python3
"""Issue #113: fail-closed proposed service-identity permission contract.

This validates a *proposed* filesystem permission model. No filesystem access,
identity creation, privilege escalation or production activation occurs.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import stat
from typing import Final

ROOT_UID: Final = 0
SERVICE_UID: Final = 996  # synthetic model identity; NEVER assign this UID on VPS
SERVICE_GID: Final = 996  # synthetic model group; resolve real gid at activation
OTHER_UID: Final = 2000
OTHER_GID: Final = 2000


@dataclass(frozen=True)
class Node:
    name: str
    mode: int
    uid: int
    gid: int
    directory: bool


# Fixed topology is a design contract, not a declaration of live filesystem state.
PLAN: Final = (
    Node("/etc/cybercore-exec", 0o755, ROOT_UID, ROOT_UID, True),
    Node("/etc/cybercore-exec/approvals", 0o750, ROOT_UID, SERVICE_GID, True),
    Node(
        "/etc/cybercore-exec/approvals/nextcloud-r1.json",
        0o640,
        ROOT_UID,
        SERVICE_GID,
        False,
    ),
    Node("/usr/local/libexec", 0o755, ROOT_UID, ROOT_UID, True),
    Node("/usr/local/libexec/cybercore-exec", 0o750, ROOT_UID, SERVICE_GID, True),
    Node("/usr/local/libexec/cybercore-exec/dispatcher.py", 0o640, ROOT_UID, SERVICE_GID, False),
    Node(
        "/usr/local/libexec/cybercore-exec/authorization.py",
        0o640,
        ROOT_UID,
        SERVICE_GID,
        False,
    ),
    Node("/usr/local/libexec/cybercore-exec-nextcloud-r1", 0o750, ROOT_UID, SERVICE_GID, True),
    Node(
        "/usr/local/libexec/cybercore-exec-nextcloud-r1/transfer.py",
        0o640,
        ROOT_UID,
        SERVICE_GID,
        False,
    ),
)


def can(node: Node, uid: int, gids: frozenset[int], permission: int) -> bool:
    if uid == ROOT_UID:
        return True
    shift = 6 if node.uid == uid else 3 if node.gid in gids else 0
    return bool((node.mode >> shift) & permission)


def validate(nodes: tuple[Node, ...] = PLAN) -> dict[str, object]:
    expected = {node.name: node for node in PLAN}
    present = {node.name: node for node in nodes}
    if len(present) != len(nodes) or set(present) != set(expected):
        raise ValueError("unexpected, missing, or duplicate permission path")
    for path, expected_node in expected.items():
        node = present[path]
        if (node.uid, node.gid, node.mode, node.directory) != (
            expected_node.uid,
            expected_node.gid,
            expected_node.mode,
            expected_node.directory,
        ):
            raise ValueError(f"permission contract drift: {path}")
        if node.mode & 0o022:
            raise ValueError(f"untrusted write permission: {path}")
        if node.directory and not (node.mode & stat.S_IXUSR):
            raise ValueError(f"root cannot traverse directory: {path}")

    service_groups = frozenset({SERVICE_GID})
    outsiders = frozenset({OTHER_GID})
    approvals = present["/etc/cybercore-exec/approvals"]
    manifest = present["/etc/cybercore-exec/approvals/nextcloud-r1.json"]
    if not can(approvals, SERVICE_UID, service_groups, stat.S_IXOTH):
        raise ValueError("service cannot traverse approval directory")
    if not can(manifest, SERVICE_UID, service_groups, stat.S_IROTH):
        raise ValueError("service cannot read approval manifest")
    if can(approvals, OTHER_UID, outsiders, stat.S_IXOTH):
        raise ValueError("outsider can traverse approval directory")
    if can(manifest, OTHER_UID, outsiders, stat.S_IROTH):
        raise ValueError("outsider can read approval manifest")
    if can(manifest, SERVICE_UID, service_groups, stat.S_IWOTH):
        raise ValueError("service can modify root-owned approval manifest")
    for name in (
        "/usr/local/libexec/cybercore-exec/dispatcher.py",
        "/usr/local/libexec/cybercore-exec/authorization.py",
        "/usr/local/libexec/cybercore-exec-nextcloud-r1/transfer.py",
    ):
        node = present[name]
        if not can(node, SERVICE_UID, service_groups, stat.S_IROTH):
            raise ValueError(f"service cannot import code: {name}")
        if can(node, SERVICE_UID, service_groups, stat.S_IWOTH):
            raise ValueError(f"service can modify code: {name}")
    for name in (
        "/usr/local/libexec/cybercore-exec",
        "/usr/local/libexec/cybercore-exec-nextcloud-r1",
    ):
        if can(present[name], OTHER_UID, outsiders, stat.S_IXOTH):
            raise ValueError(f"outsider can traverse code directory: {name}")
    return {
        "status": "PROPOSED_PERMISSION_CONTRACT_VERIFIED",
        "issue": 113,
        "synthetic_uid_gid_only": True,
        "production_paths_inspected": False,
        "service_can_read_manifest": True,
        "outsider_cannot_read_manifest": True,
        "service_cannot_modify_manifest_or_code": True,
        "identity_created": False,
        "activation_performed": False,
    }


def main() -> int:
    try:
        receipt = validate()
    except ValueError as exc:
        receipt = {
            "status": "BLOCKED",
            "issue": 113,
            "reason": str(exc),
            "activation_performed": False,
        }
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "PROPOSED_PERMISSION_CONTRACT_VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
