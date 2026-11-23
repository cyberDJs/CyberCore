#!/usr/bin/env python3
"""Issue #113: root-only OFFLINE sshd configuration preflight.

No changes to /etc, no service reload, no identity or secret writes. Candidate
config is assembled in a root-only /run temporary directory then removed.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

INCLUDE = "Include /etc/ssh/sshd_config.d/*.conf"
SUBSYSTEM = (
    "Subsystem cybercore-exec /usr/bin/python3 "
    "/usr/local/libexec/cybercore-exec/dispatcher.py cyberskills-vps"
)
FORCE_COMMAND = (
    "/usr/bin/python3 /usr/local/libexec/cybercore-exec/dispatcher.py cyberskills-vps"
)
REQUIRED_SERVICE = {
    "passwordauthentication": "no",
    "kbdinteractiveauthentication": "no",
    "permittty": "no",
    "x11forwarding": "no",
    "allowtcpforwarding": "no",
    "allowagentforwarding": "no",
    "permittunnel": "no",
    "gatewayports": "no",
    "permituserrc": "no",
    "forcecommand": FORCE_COMMAND,
}


def directives(data: str) -> list[str]:
    return [
        re.sub(r"\s+", " ", line.strip())
        for line in data.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def check_layout(main: str, includes: dict[str, str], subsystem: str, tail: str) -> None:
    base = directives(main)
    if base.count(INCLUDE) != 1 or any(line.startswith("Match ") for line in base):
        raise ValueError("expected one early Include and no existing primary Match block")
    if any(line.startswith("Include ") and line != INCLUDE for line in base):
        raise ValueError("unreviewed additional primary Include")
    if any(line.startswith("Subsystem cybercore-exec ") for line in base):
        raise ValueError("CyberCore subsystem already installed")
    if directives(subsystem) != [SUBSYSTEM]:
        raise ValueError("subsystem candidate is not exact or contains extra directives")
    expected_tail = ["Match User cybercore-exec", *(
        f"{name} {value}" for name, value in [
            ("PasswordAuthentication", "no"),
            ("KbdInteractiveAuthentication", "no"),
            ("PermitTTY", "no"),
            ("X11Forwarding", "no"),
            ("AllowTcpForwarding", "no"),
            ("AllowAgentForwarding", "no"),
            ("PermitTunnel", "no"),
            ("GatewayPorts", "no"),
            ("PermitUserRC", "no"),
            ("ForceCommand", FORCE_COMMAND),
        ]
    )]
    if directives(tail) != expected_tail:
        raise ValueError("end-of-file Match User candidate deviates from reviewed template")
    if not includes:
        raise ValueError("no active included SSH configuration files discovered")
    for name, data in includes.items():
        if any(line.startswith(("Include ", "Match ", "Subsystem cybercore-exec "))
               for line in directives(data)):
            raise ValueError(f"unreviewed nested Include, Match or duplicate subsystem: {name}")


def read_root_owned(path: Path) -> str:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or (info.st_mode & 0o022):
        raise ValueError(f"unsafe config owner/type/mode: {path}")
    return path.read_text(encoding="utf-8")


def effective(sshd: str, config: Path, user: str, address: str) -> dict[str, str]:
    result = subprocess.run(
        [sshd, "-T", "-f", str(config), "-C",
         f"user={user},host=localhost,addr={address}"],
        text=True, capture_output=True, check=True, timeout=20,
    )
    settings: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if line.strip():
            key, _, value = line.partition(" ")
            if not value:
                raise ValueError("sshd -T produced invalid output")
            settings[key] = value
    return settings


def preflight(main_path: Path, source_dir: Path, subsystem_path: Path,
              tail_path: Path, operator_addr: str, sshd: str) -> dict[str, object]:
    if os.geteuid() != 0:
        raise ValueError("root is required to read full root-only SSH configuration")
    ipaddress.ip_address(operator_addr)
    main = read_root_owned(main_path)
    directory = source_dir
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("unsafe SSH include directory")
    included = {
        path.name: read_root_owned(path)
        for path in sorted(directory.glob("*.conf"))
    }
    subsystem = subsystem_path.read_text(encoding="utf-8")
    tail = tail_path.read_text(encoding="utf-8")
    check_layout(main, included, subsystem, tail)
    baseline: dict[str, dict[str, str]] = {}
    for user in ("root", "cybercore-deploy"):
        baseline[user] = effective(sshd, main_path, user, operator_addr)
    with tempfile.TemporaryDirectory(prefix="cybercore-113-sshd-", dir="/run") as root:
        base = Path(root)
        include_dir = base / "sshd_config.d"
        include_dir.mkdir(mode=0o700)
        for name, data in included.items():
            destination = include_dir / name
            destination.write_text(data, encoding="utf-8")
            destination.chmod(0o600)
        candidate_include = include_dir / "99-cybercore-113-subsystem.conf"
        if candidate_include.exists():
            raise ValueError("candidate include name collides")
        candidate_include.write_text(subsystem, encoding="utf-8")
        candidate_include.chmod(0o600)
        candidate_path = base / "sshd_config"
        candidate_path.write_text(
            main.replace(INCLUDE, f"Include {include_dir}/*.conf", 1)
            + "\n" + tail + "\n",
            encoding="utf-8",
        )
        candidate_path.chmod(0o600)
        subprocess.run(
            [sshd, "-t", "-f", str(candidate_path)],
            check=True, capture_output=True, timeout=20,
        )
        for user in ("root", "cybercore-deploy"):
            candidate = effective(sshd, candidate_path, user, operator_addr)
            removed = {k: v for k, v in candidate.items() if k != "subsystem"}
            old = {k: v for k, v in baseline[user].items() if k != "subsystem"}
            if removed != old:
                raise ValueError(f"operator effective SSH config changed for {user}")
        service = effective(sshd, candidate_path, "cybercore-exec", operator_addr)
        for key, value in REQUIRED_SERVICE.items():
            if service.get(key) != value:
                raise ValueError(f"service SSH restriction mismatch: {key}")
        if SUBSYSTEM.split(" ", 1)[1] not in service.get("subsystem", ""):
            raise ValueError("CyberCore subsystem missing from effective config")
        digest = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    return {
        "status": "OFFLINE_SSHD_CANDIDATE_VERIFIED",
        "issue": 113,
        "config_sha256": digest,
        "preserved_operators": ["root", "cybercore-deploy"],
        "service_restrictions_verified": sorted(REQUIRED_SERVICE),
        "included_files": sorted(included),
        "ssh_config_modified": False,
        "sshd_reloaded": False,
        "activation_performed": False,
        "root_owned_temp_removed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operator-addr", required=True)
    parser.add_argument("--subsystem", type=Path, required=True)
    parser.add_argument("--match-tail", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = preflight(
            Path("/etc/ssh/sshd_config"),
            Path("/etc/ssh/sshd_config.d"),
            args.subsystem,
            args.match_tail,
            args.operator_addr,
            "/usr/sbin/sshd",
        )
    except (ValueError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "BLOCKED", "issue": 113, "reason": str(exc),
                          "activation_performed": False}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
