#!/usr/bin/env python3
"""Read-only Phase-B SSH preflight for CyberCore issue #113.

Analyzes candidate SSH layouts and staged source evidence, but never installs,
reloads or starts sshd, polkit, systemd, a transfer, or a restore.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

EXPECTED_SHA = "1cbe25ffd941738c4cc0b157914daa74a95885a6"
EXPECTED_TARGET = "cyberskills-vps"
RELEASE = Path("/opt/cybercore-113/releases") / EXPECTED_SHA
SSHD_INCLUDE = "/etc/ssh/sshd_config.d/*.conf"
SUBSYSTEM = "Subsystem cybercore-exec /usr/bin/python3 /usr/local/libexec/cybercore-exec/dispatcher.py cyberskills-vps"
COMMAND = "ForceCommand /usr/bin/python3 /usr/local/libexec/cybercore-exec/dispatcher.py cyberskills-vps"
RESTRICTIONS = {
    "PasswordAuthentication no",
    "KbdInteractiveAuthentication no",
    "PermitTTY no",
    "X11Forwarding no",
    "AllowTcpForwarding no",
    "AllowAgentForwarding no",
    "PermitTunnel no",
    "GatewayPorts no",
    "PermitUserRC no",
    COMMAND,
}


def lines(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", line.strip()) for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def evaluate(primary: str, subsystem: str, tail: str) -> list[str]:
    failures: list[str] = []
    main = lines(primary)
    inc = lines(subsystem)
    match = lines(tail)
    if not any(line == f"Include {SSHD_INCLUDE}" for line in main):
        failures.append("expected SSH include not found")
    if any(line.startswith("Match ") for line in main):
        failures.append("main sshd_config already contains Match; tail location not proven")
    if inc != [SUBSYSTEM]:
        failures.append("early included snippet must contain only exact Subsystem")
    if len(match) != 1 + len(RESTRICTIONS) or match[0] != "Match User cybercore-exec":
        failures.append("tail must contain exactly one scoped Match User block")
    elif set(match[1:]) != RESTRICTIONS:
        failures.append("tail restriction set is incomplete or changed")
    if any(line.startswith("Subsystem cybercore-exec ") for line in main):
        failures.append("CyberCore Subsystem already present in main config")
    if (main.index(f"Include {SSHD_INCLUDE}") > main.index("Subsystem sftp /usr/lib/openssh/sftp-server")
            if f"Include {SSHD_INCLUDE}" in main and "Subsystem sftp /usr/lib/openssh/sftp-server" in main
            else False):
        failures.append("early Include order changed")
    if any("Match all" in line for line in inc + match):
        failures.append("Match all is forbidden in phase-B activation candidate")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sshd-main", type=Path, required=True)
    parser.add_argument("--subsystem-candidate", type=Path, required=True)
    parser.add_argument("--match-tail", type=Path, required=True)
    args = parser.parse_args()
    issues = evaluate(
        args.sshd_main.read_text(),
        args.subsystem_candidate.read_text(),
        args.match_tail.read_text(),
    )
    print(json.dumps({
        "status": "SSH_SPLIT_LAYOUT_CANDIDATE" if not issues else "BLOCKED",
        "issue": 113,
        "expected_release": str(RELEASE),
        "target": EXPECTED_TARGET,
        "source_sha": EXPECTED_SHA,
        "issues": issues,
        "full_sshd_t_and_T_required_under_root": True,
        "activation_performed": False,
        "source_sftp_trust_complete": False,
    }, sort_keys=True))
    return 0 if not issues else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(2)
