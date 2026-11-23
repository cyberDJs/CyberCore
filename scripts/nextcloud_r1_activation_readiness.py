#!/usr/bin/env python3
"""CyberCore #113 Phase-B read-only activation readiness gate.

Does not install, chmod, reload, create users, provision secrets or start units.
Checks the immutable Stage-A release and detects collisions before a separately
authorized activation plan is written.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any

SOURCE_SHA = "1cbe25ffd941738c4cc0b157914daa74a95885a6"
RELEASE = Path("/opt/cybercore-113/releases") / SOURCE_SHA
EXPECTED_FILES = frozenset(
    {
        "libexec/authorization.py",
        "libexec/dispatcher.py",
        "libexec/inventory.py",
        "libexec/operations.py",
        "libexec/protocol.py",
        "nextcloud/transfer.py",
        "nextcloud/verify.py",
        "nextcloud/rollback.py",
        "candidate/polkit.rules",
        "candidate/sshd.conf",
        "candidate/transfer.service",
        "candidate/rollback.service",
    }
)
ACTIVE_PATHS = (
    Path("/usr/local/libexec/cybercore-exec"),
    Path("/usr/local/libexec/cybercore-exec-nextcloud-r1"),
    Path("/etc/ssh/sshd_config.d/99-cybercore-113-subsystem.conf"),
    Path("/etc/systemd/system/cybercore-nextcloud-r1-transfer.service"),
    Path("/etc/systemd/system/cybercore-nextcloud-r1-rollback.service"),
    Path("/etc/polkit-1/rules.d/60-cybercore-nextcloud-r1.rules"),
    Path("/etc/cybercore-exec/approvals/nextcloud-r1.json"),
)


def regular_root_private(path: Path) -> bool:
    info = path.lstat()
    return (
        stat.S_ISREG(info.st_mode)
        and info.st_uid == 0
        and stat.S_IMODE(info.st_mode) == 0o600
    )


def safe_release(root: Path) -> tuple[int, str]:
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0:
        raise ValueError("release directory is not root-owned directory")
    if stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("release directory mode is not 0700")
    receipt = root / "stage-manifest.json"
    if not regular_root_private(receipt):
        raise ValueError("unsafe manifest metadata")
    raw = receipt.read_bytes()
    manifest: Any = json.loads(raw)
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version", "issue", "target", "source_commit",
        "activation_performed", "files",
    }:
        raise ValueError("unexpected manifest schema")
    if (
        manifest["schema_version"] != 1
        or manifest["issue"] != 113
        or manifest["target"] != "cyberskills-vps"
        or manifest["source_commit"] != SOURCE_SHA
        or manifest["activation_performed"] is not False
    ):
        raise ValueError("manifest identity mismatch")
    digests = manifest["files"]
    if not isinstance(digests, dict) or set(digests) != EXPECTED_FILES:
        raise ValueError("unexpected release file set")
    for rel in EXPECTED_FILES:
        dest = root / rel
        if not regular_root_private(dest):
            raise ValueError(f"unsafe staged file metadata: {rel}")
        content = dest.read_bytes()
        if hashlib.sha256(content).hexdigest() != digests[rel]:
            raise ValueError(f"staged file hash mismatch: {rel}")
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
    if actual != EXPECTED_FILES | {"stage-manifest.json"}:
        raise ValueError("unrecognized files in staged release")
    return len(EXPECTED_FILES), hashlib.sha256(raw).hexdigest()


def assess(
    release: Path = RELEASE,
    active_paths: tuple[Path, ...] = ACTIVE_PATHS,
    *,
    root_uid: int | None = None,
) -> dict[str, object]:
    uid = os.geteuid() if root_uid is None else root_uid
    if uid != 0:
        raise ValueError("root console required for independent release inspection")
    file_count, receipt_digest = safe_release(release)
    collisions = [
        str(path) for path in active_paths if path.is_symlink() or path.exists()
    ]
    return {
        "status": "READY_FOR_SEPARATE_ACTIVATION_DESIGN" if not collisions else "BLOCKED",
        "issue": 113,
        "source_commit": SOURCE_SHA,
        "release_files_verified": file_count,
        "manifest_sha256": receipt_digest,
        "live_collisions": collisions,
        "active_configuration_modified": False,
        "identity_created": False,
        "service_started": False,
        "activation_performed": False,
        "approval_granted": False,
    }


def main() -> int:
    try:
        data = assess()
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        data = {"status": "BLOCKED", "issue": 113, "reason": str(exc),
                "activation_performed": False, "approval_granted": False}
    print(json.dumps(data, sort_keys=True))
    return 0 if data["status"] == "READY_FOR_SEPARATE_ACTIVATION_DESIGN" else 2


if __name__ == "__main__":
    sys.exit(main())
