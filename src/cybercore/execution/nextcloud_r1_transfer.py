from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess


ISSUE_NUMBER = 113
SOURCE_HOST = "162.250.126.107"
SOURCE_USER = "eimyherr"
ARCHIVE_NAME = "nextcloud.586_28528.2026-10-07_18-30-01.tar.gz"
SOURCE_ARCHIVE = f"/home/{SOURCE_USER}/softaculous_backups/{ARCHIVE_NAME}"
EXPECTED_SIZE_BYTES = 13_259_294_576

CREDENTIAL_ROOT = Path("/var/lib/cybercore-exec-nextcloud-r1/credentials")
STATE_ROOT = Path("/var/lib/cybercore-exec-nextcloud-r1/state")
BACKUP_ROOT = Path("/var/backups/cybercore/nextcloud-r1-113/2026-10-13")
PRIVATE_KEY = CREDENTIAL_ROOT / "source_ed25519"
KNOWN_HOSTS = CREDENTIAL_ROOT / "known_hosts"
SOURCE_SHA256 = CREDENTIAL_ROOT / "source_archive.sha256"
FINAL_ARCHIVE = BACKUP_ROOT / ARCHIVE_NAME
PARTIAL_ARCHIVE = BACKUP_ROOT / f"{ARCHIVE_NAME}.partial"
RECEIPT = STATE_ROOT / "transfer-receipt.json"

SFTP = "/usr/bin/sftp"
GZIP = "/usr/bin/gzip"


def _require_private_regular(path: Path, *, mode: int) -> None:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError("required credential material is not a regular file")
    if info.st_uid != os.geteuid():
        raise RuntimeError("required credential material has unexpected owner")
    if stat.S_IMODE(info.st_mode) != mode:
        raise RuntimeError("required credential material has unexpected mode")


def _require_private_directory(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise RuntimeError("required state directory is not a directory")
    if info.st_uid != os.geteuid():
        raise RuntimeError("required state directory has unexpected owner")
    if stat.S_IMODE(info.st_mode) != 0o700:
        raise RuntimeError("required state directory must have mode 0700")


def _read_expected_sha256() -> str:
    _require_private_regular(SOURCE_SHA256, mode=0o600)
    value = SOURCE_SHA256.read_text(encoding="ascii").strip().lower()
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise RuntimeError("source archive checksum evidence is not a SHA-256 digest")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_file(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_receipt(payload: dict[str, object]) -> None:
    temporary = RECEIPT.with_suffix(".json.tmp")
    if temporary.exists():
        raise RuntimeError("temporary receipt already exists")
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(fd)
    os.replace(temporary, RECEIPT)
    _fsync_directory(STATE_ROOT)


def _sftp_argv() -> list[str]:
    return [
        SFTP,
        "-B",
        "1048576",
        "-R",
        "64",
        "-b",
        "-",
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "PasswordAuthentication=no",
        "-o",
        "KbdInteractiveAuthentication=no",
        "-o",
        "PreferredAuthentications=publickey",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        f"UserKnownHostsFile={KNOWN_HOSTS}",
        "-o",
        "ClearAllForwardings=yes",
        "-o",
        "ForwardAgent=no",
        "-o",
        "ConnectTimeout=15",
        "-i",
        str(PRIVATE_KEY),
        f"{SOURCE_USER}@{SOURCE_HOST}",
    ]


def _sftp_batch() -> bytes:
    return f"get -p {SOURCE_ARCHIVE} {PARTIAL_ARCHIVE}\n".encode("utf-8")


def main() -> int:
    _require_private_directory(CREDENTIAL_ROOT)
    _require_private_directory(STATE_ROOT)
    _require_private_directory(BACKUP_ROOT)
    _require_private_regular(PRIVATE_KEY, mode=0o600)
    _require_private_regular(KNOWN_HOSTS, mode=0o600)
    expected_sha256 = _read_expected_sha256()

    if FINAL_ARCHIVE.exists():
        raise RuntimeError("final archive already exists; run verifier instead of overwriting")
    if PARTIAL_ARCHIVE.exists():
        raise RuntimeError("partial archive already exists; explicit cleanup is required")

    completed = subprocess.run(
        _sftp_argv(),
        input=_sftp_batch(),
        shell=False,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"bounded SFTP transfer failed with exit code {completed.returncode}")

    info = PARTIAL_ARCHIVE.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError("transferred archive is not a regular file")
    if info.st_size != EXPECTED_SIZE_BYTES:
        raise RuntimeError("transferred archive size does not match the fixed recovery point")

    gzip_check = subprocess.run(
        [GZIP, "-t", str(PARTIAL_ARCHIVE)],
        shell=False,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=3600,
    )
    if gzip_check.returncode != 0:
        raise RuntimeError("transferred archive failed gzip integrity validation")

    digest = _sha256(PARTIAL_ARCHIVE)
    if digest != expected_sha256:
        raise RuntimeError("transferred archive checksum does not match source evidence")
    _fsync_file(PARTIAL_ARCHIVE)
    os.replace(PARTIAL_ARCHIVE, FINAL_ARCHIVE)
    _fsync_directory(BACKUP_ROOT)

    payload = {
        "schema_version": 1,
        "issue": ISSUE_NUMBER,
        "archive_name": ARCHIVE_NAME,
        "size_bytes": EXPECTED_SIZE_BYTES,
        "sha256": digest,
        "source_checksum_verified": True,
        "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "credential_kind": "dedicated_restricted_source_identity",
        "secret_values_recorded": False,
    }
    _write_receipt(payload)
    print(json.dumps({"status": "TRANSFERRED", **payload}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
