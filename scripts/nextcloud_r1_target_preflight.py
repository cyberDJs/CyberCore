#!/usr/bin/env python3
"""Read-only, fail-closed target preflight for CyberCore issue #113.

No privilege escalation, service activation, credential access, or writes.
Exit 0 means baseline is safe to review, NOT permission to deploy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys

APPROVED_SHA = "a2c31d12c808b730edbaaac568e4287802008e32"
EXPECTED_HOST = "vps3665015.trouble-free.net"
EXPECTED_TARGET_IP = "162.35.186.106"
EXPECTED_FILES = (
    "deploy/cybercore-exec-nextcloud-r1/README.md",
    "deploy/cybercore-exec-nextcloud-r1/cybercore-exec.policy",
    "deploy/cybercore-exec-nextcloud-r1/cybercore-exec.subsystem.conf",
    "deploy/cybercore-exec-nextcloud-r1/cybercore-nextcloud-r1-transfer.service",
    "deploy/cybercore-exec-nextcloud-r1/cybercore-nextcloud-r1-rollback.service",
    "src/cybercore/execution/server/dispatcher.py",
    "src/cybercore/execution/server/operations.py",
    "src/cybercore/execution/authorization.py",
    "src/cybercore/execution/nextcloud_r1_transfer.py",
    "src/cybercore/execution/nextcloud_r1_verify.py",
    "src/cybercore/execution/nextcloud_r1_rollback.py",
)
PROTECTED_PATHS = (
    "/etc/ssh/sshd_config.d/60-cybercore-exec.conf",
    "/etc/polkit-1/rules.d/60-cybercore-exec.rules",
    "/etc/systemd/system/cybercore-nextcloud-r1-transfer.service",
    "/etc/systemd/system/cybercore-nextcloud-r1-rollback.service",
    "/usr/local/libexec/cybercore-exec/dispatcher.py",
    "/var/lib/cybercore-exec-nextcloud-r1/credentials/source_ed25519",
    "/etc/cybercore-exec/approvals/nextcloud-r1.json",
)


def cmd(*argv: str) -> tuple[int, str]:
    try:
        p = subprocess.run(argv, check=False, capture_output=True, text=True, timeout=12)
        return p.returncode, p.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    args = ap.parse_args()
    repo = args.repo.resolve(strict=True)
    checks: dict[str, object] = {}
    rc, commit = cmd("git", "-C", str(repo), "rev-parse", "HEAD")
    checks["approved_source"] = rc == 0 and commit == APPROVED_SHA
    rc, dirty = cmd("git", "-C", str(repo), "status", "--porcelain")
    checks["source_clean"] = rc == 0 and not dirty
    checks["expected_files_present"] = all((repo / x).is_file() for x in EXPECTED_FILES)
    rc, hostname = cmd("hostname", "-f")
    checks["expected_hostname"] = rc == 0 and hostname == EXPECTED_HOST
    rc, ipv4 = cmd("hostname", "-I")
    checks["expected_ip_present"] = rc == 0 and EXPECTED_TARGET_IP in ipv4.split()
    checks["acl_tools_available"] = all(shutil.which(n) is not None for n in ("setfacl", "getfacl"))
    checks["polkit_tools_available"] = shutil.which("pkcheck") is not None
    checks["service_identity_absent"] = True
    try:
        pwd.getpwnam("cybercore-exec")
    except KeyError:
        pass
    else:
        checks["service_identity_absent"] = False

    # No symlink traversal or secret reads. Presence itself is a collision gate.
    checks["managed_paths_absent"] = all(not os.path.lexists(p) for p in PROTECTED_PATHS)
    rc, out = cmd("systemctl", "list-unit-files", "--no-legend",
                  "cybercore-nextcloud-r1-transfer.service",
                  "cybercore-nextcloud-r1-rollback.service")
    checks["units_absent"] = rc == 0 and (not out or out == "0 unit files listed.")
    rc, _ = cmd("sshd", "-t")
    # Non-root sshd -t may fail to open host private keys: UNKNOWN is not PASS.
    checks["sshd_syntax_read_only"] = "PASS" if rc == 0 else "REQUIRES_ROOT_CONSOLE_CHECK"
    checks["root_not_required_for_this_probe"] = os.geteuid() != 0

    mandatory = ("approved_source", "source_clean", "expected_files_present",
                 "expected_hostname", "expected_ip_present",
                 "acl_tools_available", "polkit_tools_available",
                 "service_identity_absent", "managed_paths_absent",
                 "units_absent", "root_not_required_for_this_probe")
    status = "PRECHECK_PASS_NOT_DEPLOYABLE" if all(checks[k] is True for k in mandatory) else "BLOCKED"
    print(json.dumps({
        "issue": 113,
        "approved_sha": APPROVED_SHA,
        "status": status,
        "checks": checks,
        "runtime_installation_performed": False,
        "source_host_trusted": False,
        "source_archive_digest_verified": False,
        "root_bootstrap_reviewed": False,
        "deployment_authorized_by_this_report": False,
    }, sort_keys=True, indent=2))
    return 0 if status == "PRECHECK_PASS_NOT_DEPLOYABLE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
