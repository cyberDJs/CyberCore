#!/usr/bin/env python3
"""#113 phase-A root bootstrap: install inert, content-pinned artifacts only.

This bootstrap deliberately does NOT create identities, configure SSH/Polkit,
install/enable systemd units, provision secrets, run transfers, or restore data.
The installed release is inert until a separately reviewed activation plan.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

TARGET = "cyberskills-vps"
SOURCE_SHA = "1cbe25ffd941738c4cc0b157914daa74a95885a6"
PREFIX = Path("/opt/cybercore-113/releases")
RELEASE = PREFIX / SOURCE_SHA
FILES = {
    "src/cybercore/execution/authorization.py": "libexec/authorization.py",
    "src/cybercore/execution/server/dispatcher.py": "libexec/dispatcher.py",
    "src/cybercore/execution/server/inventory.py": "libexec/inventory.py",
    "src/cybercore/execution/server/operations.py": "libexec/operations.py",
    "src/cybercore/execution/server/protocol.py": "libexec/protocol.py",
    "src/cybercore/execution/nextcloud_r1_transfer.py": "nextcloud/transfer.py",
    "src/cybercore/execution/nextcloud_r1_verify.py": "nextcloud/verify.py",
    "src/cybercore/execution/nextcloud_r1_rollback.py": "nextcloud/rollback.py",
    "deploy/cybercore-exec-nextcloud-r1/cybercore-exec.policy": "candidate/polkit.rules",
    "deploy/cybercore-exec-nextcloud-r1/cybercore-exec.subsystem.conf": "candidate/sshd.conf",
    "deploy/cybercore-exec-nextcloud-r1/cybercore-nextcloud-r1-transfer.service": "candidate/transfer.service",
    "deploy/cybercore-exec-nextcloud-r1/cybercore-nextcloud-r1-rollback.service": "candidate/rollback.service",
}
MANIFEST = "stage-manifest.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(message: str) -> None:
    raise RuntimeError(message)


def git_sha(root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=10, check=True
    )
    return completed.stdout.strip()


def snapshot(root: Path) -> dict[str, bytes]:
    if git_sha(root) != SOURCE_SHA:
        fail("source tree SHA differs from the fixed approved staging baseline")
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        capture_output=True, text=True, timeout=10, check=True
    )
    if status.stdout.strip():
        fail("source tree is dirty")
    found = {}
    for source, relative in FILES.items():
        p = root / source
        info = p.lstat()
        if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
            fail(f"nonregular source: {source}")
        found[relative] = p.read_bytes()
    return found


def expected_manifest(files: dict[str, bytes]) -> dict[str, object]:
    return {
        "schema_version": 1, "issue": 113, "target": TARGET,
        "source_commit": SOURCE_SHA,
        "activation_performed": False,
        "files": {name: digest(data) for name, data in sorted(files.items())},
    }


def safe_parent() -> None:
    for path in (Path("/opt"), Path("/opt/cybercore-113"), PREFIX):
        if path.is_symlink():
            fail(f"symlink parent blocked: {path}")
        if path.exists():
            mode = path.lstat()
            if not stat.S_ISDIR(mode.st_mode) or mode.st_uid != 0:
                fail(f"unsafe parent: {path}")
            if stat.S_IMODE(mode.st_mode) & 0o022:
                fail(f"writable parent: {path}")


def atomic_stage(files: dict[str, bytes], manifest: dict[str, object]) -> None:
    if os.geteuid() != 0:
        fail("apply requires root via an independent administrator-controlled console")
    safe_parent()
    if RELEASE.exists() or RELEASE.is_symlink():
        fail("release already exists; do not overwrite")
    Path("/opt/cybercore-113").mkdir(mode=0o700, exist_ok=True)
    PREFIX.mkdir(mode=0o700, exist_ok=True)
    safe_parent()
    with tempfile.TemporaryDirectory(prefix=".candidate-", dir=PREFIX) as temp:
        tmp = Path(temp)
        os.chmod(tmp, 0o700)
        for relative, data in files.items():
            dest = tmp / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            os.chmod(dest, 0o600)
            if digest(dest.read_bytes()) != manifest["files"][relative]:
                fail("staged file digest changed")
        receipt = tmp / MANIFEST
        receipt.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        os.chmod(receipt, 0o600)
        # No service/SSH/Polkit file is installed at its active path.
        os.rename(tmp, RELEASE)
    print(json.dumps({"status": "INERT_STAGED", "release": str(RELEASE),
                      "activation_performed": False}, sort_keys=True))


def inspect_release(manifest: dict[str, object]) -> None:
    safe_parent()
    info = RELEASE.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0:
        fail("managed release directory identity mismatch")
    for rel, expected in manifest["files"].items():
        path = RELEASE / rel
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
            fail(f"unsafe managed file: {rel}")
        if info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
            fail(f"owner or mode drift: {rel}")
        if digest(path.read_bytes()) != expected:
            fail(f"managed file contents drift: {rel}")
    recorded = json.loads((RELEASE / MANIFEST).read_text())
    if recorded != manifest:
        fail("release manifest drift")


def rollback(manifest: dict[str, object]) -> None:
    if os.geteuid() != 0:
        fail("rollback requires root")
    inspect_release(manifest)
    # Only this isolated release. No backup, credential or live configuration.
    for relative in manifest["files"]:
        (RELEASE / relative).unlink()
    (RELEASE / MANIFEST).unlink()
    for directory in sorted(
        (p for p in RELEASE.rglob("*") if p.is_dir()),
        key=lambda p: len(p.parts), reverse=True,
    ):
        directory.rmdir()  # fail closed on unexpected extra objects
    RELEASE.rmdir()
    print(json.dumps({"status": "INERT_STAGE_REMOVED",
                      "preserved_live_services": True,
                      "preserved_backups": True}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["plan", "apply", "verify", "rollback"])
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    files = snapshot(args.source_root.resolve(strict=True))
    manifest = expected_manifest(files)
    if args.action == "plan":
        print(json.dumps({"status": "PLAN_ONLY", **manifest,
                          "destination": str(RELEASE)}, sort_keys=True, indent=2))
    elif args.action == "apply":
        atomic_stage(files, manifest)
    elif args.action == "verify":
        inspect_release(manifest)
        print(json.dumps({"status": "INERT_STAGE_VERIFIED",
                          "activation_performed": False}, sort_keys=True))
    else:
        rollback(manifest)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(2)
