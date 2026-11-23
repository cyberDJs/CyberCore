#!/usr/bin/env python3
"""Read-only, fail-closed identity readiness for CyberCore #113.

This tool NEVER creates identities, modifies permissions, or grants approval.
"""
from __future__ import annotations

import argparse
import grp
import json
import os
import pwd
import socket
import stat
from pathlib import Path

HOST = "vps3665015.trouble-free.net"
ACCOUNT = "cybercore-exec"
SAFE_SHELLS = frozenset({"/usr/sbin/nologin", "/sbin/nologin", "/bin/false"})
FORBIDDEN_GROUPS = frozenset({"sudo", "wheel", "adm", "docker", "lxd", "shadow", "root"})
ROOT_PATHS = (
    Path("/usr/local/libexec"),
    Path("/etc/ssh"),
    Path("/etc/systemd/system"),
    Path("/etc/polkit-1/rules.d"),
)
ACTIVE_PATHS = (
    Path("/usr/local/libexec/cybercore-exec"),
    Path("/usr/local/libexec/cybercore-exec-nextcloud-r1"),
    Path("/etc/cybercore-113-activation"),
    Path("/var/lib/cybercore-113-code-only.json"),
    Path("/var/lib/cybercore-113-code-intent.json"),
)
UNITS = (
    Path("/etc/systemd/system/cybercore-nextcloud-r1-transfer.service"),
    Path("/etc/systemd/system/cybercore-nextcloud-r1-rollback.service"),
)


def find_user(name: str):
    try:
        return pwd.getpwnam(name)
    except KeyError:
        return None


def find_group(name: str):
    try:
        return grp.getgrnam(name)
    except KeyError:
        return None


def evaluate_identity(user, group, memberships: dict[str, set[str]]) -> tuple[str, list[str]]:
    """Pure logic: return state and named violations."""
    violations: list[str] = []
    if user is None and group is None:
        return "IDENTITY_ABSENT_READY_FOR_SEPARATE_ROOT_PROVISIONING", []
    if user is None or group is None:
        return "BLOCKED", ["partial user/group collision"]
    if user.pw_uid == 0 or user.pw_uid < 100:
        violations.append("unexpected service UID")
    if user.pw_gid != group.gr_gid:
        violations.append("primary group mismatch")
    if group.gr_gid == 0:
        violations.append("privileged primary group")
    if user.pw_shell not in SAFE_SHELLS:
        violations.append("service shell is interactive or untrusted")
    if user.pw_passwd not in ("x", "*", "!", "!!"):
        violations.append("unexpected shadow passwd marker")
    if not user.pw_dir.startswith("/nonexistent"):
        violations.append("unexpected service home path")
    for group_name, member_names in memberships.items():
        if ACCOUNT in member_names and group_name in FORBIDDEN_GROUPS:
            violations.append(f"service has privileged supplementary group: {group_name}")
    return ("IDENTITY_PRESENT_RESTRICTED", []) if not violations else ("BLOCKED", violations)


def check_directory(path: Path) -> str | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return f"required parent absent: {path}"
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        return f"untrusted required parent: {path}"
    return None


def preflight(*, expected_hostname: str = HOST) -> dict[str, object]:
    violations = []
    observed = socket.getfqdn()
    if observed != expected_hostname:
        violations.append("target hostname mismatch")
    for path in ROOT_PATHS:
        failure = check_directory(path)
        if failure:
            violations.append(failure)
    for path in (*ACTIVE_PATHS, *UNITS):
        if path.exists() or path.is_symlink():
            violations.append(f"active or colliding path requires review: {path}")
    user = find_user(ACCOUNT)
    group = find_group(ACCOUNT)
    memberships = {g.gr_name: set(g.gr_mem) for g in grp.getgrall()}
    state, identity_violations = evaluate_identity(user, group, memberships)
    violations.extend(identity_violations)
    return {
        "issue": 113,
        "hostname": observed,
        "state": "BLOCKED" if violations else state,
        "violations": sorted(violations),
        "identity_present": user is not None,
        "group_present": group is not None,
        "commands_executed": False,
        "identity_created": False,
        "activation_performed": False,
        "preflight_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-hostname", default=HOST)
    args = parser.parse_args()
    receipt = preflight(expected_hostname=args.expected_hostname)
    print(json.dumps(receipt, sort_keys=True))
    return 2 if receipt["state"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
