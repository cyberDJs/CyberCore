#!/usr/bin/env python3
"""Issue #113: post-code-install, read-only runtime configuration gate.

Reports evidence and blockers. NEVER mutates filesystem, SSH or services.
"""
from __future__ import annotations

import grp
import json
import os
from pathlib import Path
import pwd
import socket
import stat
import subprocess

HOST = "vps3665015.trouble-free.net"
ACCOUNT = "cybercore-exec"
DEST = Path("/usr/local/libexec")
MODULES = {
    "cybercore-exec": frozenset({
        "authorization.py", "dispatcher.py", "inventory.py", "operations.py",
        "protocol.py",
    }),
    "cybercore-exec-nextcloud-r1": frozenset({
        "transfer.py", "verify.py", "rollback.py",
    }),
}
RECEIPT = Path("/var/lib/cybercore-113-code-only.json")
JOURNAL = Path("/var/lib/cybercore-113-code-intent.json")
APPROVAL = Path("/etc/cybercore-113-activation/code-only.json")
ACTIVATION_PATHS = (
    Path("/etc/ssh/sshd_config.d/99-cybercore-113-subsystem.conf"),
    Path("/etc/systemd/system/cybercore-nextcloud-r1-transfer.service"),
    Path("/etc/systemd/system/cybercore-nextcloud-r1-rollback.service"),
    Path("/etc/polkit-1/rules.d/60-cybercore-nextcloud-r1.rules"),
    Path("/etc/cybercore-exec/approvals/nextcloud-r1.json"),
)
RUNTIME_PATHS = (
    Path("/var/lib/cybercore-exec-nextcloud-r1/credentials"),
    Path("/var/lib/cybercore-exec-nextcloud-r1/state"),
)


def issue_if_unsafe_node(path: Path, *, directory: bool, mode: int, uid: int = 0,
                         gid: int = 0) -> str | None:
    try:
        s = path.lstat()
    except FileNotFoundError:
        return f"missing:{path}"
    if (s.st_uid != uid or s.st_gid != gid
            or stat.S_IMODE(s.st_mode) != mode
            or (stat.S_ISDIR(s.st_mode) != directory)):
        return f"unexpected_metadata:{path}"
    return None


def inspect_acl(path: Path, uid: int, *, directory: bool) -> str | None:
    rights = "r-x" if directory else "r--"
    expected = {
        "user::rwx" if directory else "user::rw-",
        f"user:{uid}:{rights}", "group::---", f"mask::{rights}", "other::---",
    }
    try:
        result = subprocess.run(
            ["/usr/bin/getfacl", "-n", "-c", str(path)],
            capture_output=True, text=True, check=True, timeout=10,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return f"acl_unreadable:{path}"
    actual = {v.strip() for v in result.stdout.splitlines() if v.strip()}
    return None if actual == expected else f"acl_mismatch:{path}"


def assess() -> dict[str, object]:
    problems: list[str] = []
    hostname = socket.getfqdn()
    if hostname != HOST:
        problems.append("unexpected_hostname")
    try:
        account = pwd.getpwnam(ACCOUNT)
        group = grp.getgrnam(ACCOUNT)
        if (account.pw_uid == 0 or account.pw_gid != group.gr_gid
                or account.pw_shell not in ("/usr/sbin/nologin", "/sbin/nologin", "/bin/false")):
            problems.append("service_identity_untrusted")
        uid = account.pw_uid
    except KeyError:
        problems.append("service_identity_absent")
        uid = None
    for directory, names in MODULES.items():
        path = DEST / directory
        p = issue_if_unsafe_node(path, directory=True, mode=0o750)
        if p:
            problems.append(p)
            continue
        if uid is not None:
            error = inspect_acl(path, uid, directory=True)
            if error:
                problems.append(error)
        try:
            entries = set(p.name for p in path.iterdir())
        except PermissionError:
            problems.append(f"directory_unreadable:{path}")
            continue
        if entries != names:
            problems.append(f"unexpected_file_set:{path}")
        for name in names:
            file_path = path / name
            p = issue_if_unsafe_node(file_path, directory=False, mode=0o640)
            if p:
                problems.append(p)
            elif uid is not None:
                acl_error = inspect_acl(file_path, uid, directory=False)
                if acl_error:
                    problems.append(acl_error)
    p = issue_if_unsafe_node(RECEIPT, directory=False, mode=0o600)
    if p:
        problems.append(p)
    for path in (JOURNAL, APPROVAL):
        if path.exists() or path.is_symlink():
            problems.append(f"pending_transaction_artifact:{path}")
    installed = [str(path) for path in ACTIVATION_PATHS if path.exists() or path.is_symlink()]
    if installed:
        problems.extend(f"activation_collision:{p}" for p in installed)
    missing_runtime = [str(path) for path in RUNTIME_PATHS if not path.exists()]
    # Deliberately reports missing next-phase directories without creating them.
    return {
        "issue": 113,
        "status": "POST_CODE_READY_FOR_SEPARATE_ACTIVATION_DESIGN" if not problems else "BLOCKED",
        "hostname": hostname,
        "verified_metadata_and_acl_files": sum(MODULES.values(), frozenset()).__len__() if not problems else None,
        "problems": sorted(problems),
        "missing_runtime_directories": missing_runtime,
        "activation_paths_present": installed,
        "receipt_contents_verified": False,
        "activation_performed": False,
        "mutations_performed": False,
    }


def main() -> int:
    result = assess()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] != "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
