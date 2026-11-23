#!/usr/bin/env python3
"""Issue #113: code-only root transaction; NEVER activates SSH/systemd/Polkit.

This program stages exact pinned Stage-A code into immutable, root-owned
service-readable paths. No identities, approvals or credentials are created.
Activation is a separate change with separate authorization and review.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

SOURCE_SHA = "1cbe25ffd941738c4cc0b157914daa74a95885a6"
SOURCE = Path("/opt/cybercore-113/releases") / SOURCE_SHA
DEST_PARENT = Path("/usr/local/libexec")
APPROVAL = Path("/etc/cybercore-exec/approvals/code-only-113.json")
RECEIPT = Path("/var/lib/cybercore-113-code-only.json")
TARGETS = {
    "libexec/authorization.py": "cybercore-exec/authorization.py",
    "libexec/dispatcher.py": "cybercore-exec/dispatcher.py",
    "libexec/inventory.py": "cybercore-exec/inventory.py",
    "libexec/operations.py": "cybercore-exec/operations.py",
    "libexec/protocol.py": "cybercore-exec/protocol.py",
    "nextcloud/transfer.py": "cybercore-exec-nextcloud-r1/transfer.py",
    "nextcloud/verify.py": "cybercore-exec-nextcloud-r1/verify.py",
    "nextcloud/rollback.py": "cybercore-exec-nextcloud-r1/rollback.py",
}
DIRECTORIES = ("cybercore-exec", "cybercore-exec-nextcloud-r1")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_node(path: Path, *, directory: bool, mode: int) -> None:
    info = path.lstat()
    if info.st_uid != 0 or stat.S_IMODE(info.st_mode) != mode:
        raise ValueError(f"unsafe owner or mode: {path}")
    if directory != stat.S_ISDIR(info.st_mode):
        raise ValueError(f"unsafe file type: {path}")


def safe_root_parent(path: Path) -> None:
    for parent in (Path("/"), Path("/usr"), Path("/usr/local"), path):
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError(f"untrusted installation parent: {parent}")


def snapshot(source: Path = SOURCE) -> dict[str, bytes]:
    safe_node(source, directory=True, mode=0o700)
    safe_node(source / "stage-manifest.json", directory=False, mode=0o600)
    manifest = json.loads((source / "stage-manifest.json").read_text())
    if not isinstance(manifest, dict) or (
        manifest.get("issue") != 113
        or manifest.get("source_commit") != SOURCE_SHA
        or manifest.get("target") != "cyberskills-vps"
        or manifest.get("activation_performed") is not False
    ):
        raise ValueError("inert Stage-A manifest identity mismatch")
    files = manifest.get("files")
    if not isinstance(files, dict) or set(TARGETS) - set(files):
        raise ValueError("required manifest files missing")
    result = {}
    for original in TARGETS:
        path = source / original
        safe_node(path, directory=False, mode=0o600)
        raw = path.read_bytes()
        if sha(raw) != files[original]:
            raise ValueError(f"stage content hash mismatch: {original}")
        result[original] = raw
    return result


def exact_approval(path: Path = APPROVAL) -> str:
    safe_node(path.parent, directory=True, mode=0o700)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
            raise ValueError("approval file owner/mode/type mismatch")
        if info.st_size < 1 or info.st_size > 4096:
            raise ValueError("approval file size invalid")
        raw = os.read(fd, 4097)
    finally:
        os.close(fd)
    data = json.loads(raw)
    expected = {"issue", "source_commit", "action", "approval_id", "issued_at", "expires_at"}
    if not isinstance(data, dict) or set(data) != expected or (
        data["issue"] != 113 or data["source_commit"] != SOURCE_SHA
        or data["action"] != "code-only-install"
    ):
        raise ValueError("approval fields or exact binding mismatch")
    if not isinstance(data["approval_id"], str) or not data["approval_id"].strip():
        raise ValueError("missing approval ID")
    values = []
    for key in ("issued_at", "expires_at"):
        value = data[key]
        if not isinstance(value, str) or not value.endswith("Z"):
            raise ValueError("non UTC approval timestamp")
        values.append(datetime.fromisoformat(value[:-1] + "+00:00"))
    issued, expires = values
    now = datetime.now(timezone.utc)
    if not (issued <= now < expires and 0 < (expires - issued).total_seconds() <= 3600):
        raise ValueError("approval expired, future dated or excessive TTL")
    return data["approval_id"]


def make_layout(raw: dict[str, bytes], destination_parent: Path) -> dict[str, str]:
    paths: dict[str, str] = {}
    for directory in DIRECTORIES:
        directory_path = destination_parent / directory
        if directory_path.exists() or directory_path.is_symlink():
            raise ValueError(f"destination collision: {directory}")
    for original, relative in TARGETS.items():
        paths[relative] = sha(raw[original])
    return paths


def verify_layout(parent: Path, hashes: dict[str, str]) -> None:
    if set(hashes) != set(TARGETS.values()):
        raise ValueError("receipt file map differs from reviewed paths")
    for directory in DIRECTORIES:
        path = parent / directory
        safe_node(path, directory=True, mode=0o755)
        allowed = {Path(name).name for name in hashes if Path(name).parent.name == directory}
        if {p.name for p in path.iterdir()} != allowed:
            raise ValueError("active directory has unreviewed contents")
    for name, digest in hashes.items():
        path = parent / name
        safe_node(path, directory=False, mode=0o644)
        if sha(path.read_bytes()) != digest:
            raise ValueError("active file differs from recorded SHA")


def receipt_read(path: Path) -> dict[str, object]:
    safe_node(path, directory=False, mode=0o600)
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or set(data) != {
        "issue", "source_commit", "status", "file_sha256", "approval_id"
    } or data["issue"] != 113 or data["source_commit"] != SOURCE_SHA:
        raise ValueError("transaction receipt identity mismatch")
    if data["status"] != "CODE_ONLY_INSTALLED" or not isinstance(data["file_sha256"], dict):
        raise ValueError("unexpected receipt status/map")
    return data


def apply(source: Path = SOURCE, parent: Path = DEST_PARENT, approval: Path = APPROVAL,
          receipt: Path = RECEIPT) -> dict[str, object]:
    if os.geteuid() != 0:
        raise ValueError("root console required")
    safe_root_parent(parent)
    if receipt.exists() or receipt.is_symlink():
        raise ValueError("transaction already recorded; refuse overwrite")
    raw = snapshot(source)
    hashes = make_layout(raw, parent)
    approval_id = exact_approval(approval)
    installed: list[Path] = []
    try:
        for directory in DIRECTORIES:
            tmp = Path(tempfile.mkdtemp(prefix=".cybercore-113-", dir=parent))
            try:
                os.chmod(tmp, 0o700)
                for original, relative in TARGETS.items():
                    rel = Path(relative)
                    if rel.parent.name != directory:
                        continue
                    dest = tmp / rel.name
                    fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                                 getattr(os, "O_NOFOLLOW", 0), 0o600)
                    with os.fdopen(fd, "wb") as handle:
                        handle.write(raw[original])
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.chmod(dest, 0o644)
                os.chmod(tmp, 0o755)
                final = parent / directory
                if final.exists() or final.is_symlink():
                    raise ValueError("destination appeared during transaction")
                os.rename(tmp, final)
                installed.append(final)
            finally:
                if tmp.exists():
                    shutil.rmtree(tmp)
        verify_layout(parent, hashes)
        payload = {"issue": 113, "source_commit": SOURCE_SHA,
                   "status": "CODE_ONLY_INSTALLED", "file_sha256": hashes,
                   "approval_id": approval_id}
        fd = os.open(receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "w") as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        return {"status": "CODE_ONLY_INSTALLED", "activation_performed": False,
                "file_count": len(hashes)}
    except Exception:
        # Compensation only removes paths created by this exact invocation.
        for created in reversed(installed):
            if created.exists():
                shutil.rmtree(created)
        raise


def verify(parent: Path = DEST_PARENT, receipt: Path = RECEIPT) -> dict[str, object]:
    if os.geteuid() != 0:
        raise ValueError("root required")
    data = receipt_read(receipt)
    hashes = data["file_sha256"]
    assert isinstance(hashes, dict)
    verify_layout(parent, hashes)
    return {"status": "CODE_ONLY_VERIFIED", "activation_performed": False,
            "file_count": len(hashes)}


def rollback(parent: Path = DEST_PARENT, receipt: Path = RECEIPT,
             approval: Path = APPROVAL) -> dict[str, object]:
    if os.geteuid() != 0:
        raise ValueError("root required")
    exact_approval(approval)  # same short-lived approval; never anonymous deletion
    data = receipt_read(receipt)
    hashes = data["file_sha256"]
    assert isinstance(hashes, dict)
    verify_layout(parent, hashes)
    for directory in DIRECTORIES:
        path = parent / directory
        for item in path.iterdir():
            item.unlink()
        path.rmdir()
    receipt.unlink()
    return {"status": "CODE_ONLY_ROLLED_BACK", "activation_performed": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("plan", "apply", "verify", "rollback"))
    args = parser.parse_args()
    try:
        if args.action == "plan":
            data = {"status": "CODE_ONLY_PLAN", "issue": 113,
                    "files": sorted(TARGETS.values()), "activation_performed": False}
        elif args.action == "apply":
            data = apply()
        elif args.action == "verify":
            data = verify()
        else:
            data = rollback()
    except (ValueError, OSError, RuntimeError, TypeError, json.JSONDecodeError) as exc:
        data = {"status": "BLOCKED", "reason": str(exc), "activation_performed": False}
    print(json.dumps(data, sort_keys=True))
    return 2 if data["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
