from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
import subprocess
import tarfile


ISSUE_NUMBER = 113
ARCHIVE_NAME = "nextcloud.586_28528.2026-10-07_18-30-01.tar.gz"
EXPECTED_SIZE_BYTES = 13_259_294_576
STATE_ROOT = Path("/var/lib/cybercore-exec-nextcloud-r1/state")
BACKUP_ROOT = Path("/var/backups/cybercore/nextcloud-r1-113/2026-10-13")
FINAL_ARCHIVE = BACKUP_ROOT / ARCHIVE_NAME
RECEIPT = STATE_ROOT / "transfer-receipt.json"
GZIP = "/usr/bin/gzip"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_receipt() -> dict[str, object]:
    raw = json.loads(RECEIPT.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError("transfer receipt is not an object")
    expected_keys = {
        "schema_version",
        "issue",
        "archive_name",
        "size_bytes",
        "sha256",
        "completed_at",
        "credential_kind",
        "secret_values_recorded",
    }
    if set(raw) != expected_keys:
        raise RuntimeError("transfer receipt fields do not match the exact schema")
    if raw["schema_version"] != 1 or raw["issue"] != ISSUE_NUMBER:
        raise RuntimeError("transfer receipt identity does not match issue #113")
    if raw["archive_name"] != ARCHIVE_NAME or raw["size_bytes"] != EXPECTED_SIZE_BYTES:
        raise RuntimeError("transfer receipt does not match the fixed archive")
    if raw["secret_values_recorded"] is not False:
        raise RuntimeError("transfer receipt unexpectedly records secret material")
    return raw


def _component_markers(path: Path) -> dict[str, bool]:
    markers = {
        "config": False,
        "data": False,
        "database": False,
        "occ": False,
        "themes": False,
    }
    with tarfile.open(path, mode="r:gz") as archive:
        for member in archive:
            name = member.name.lstrip("/")
            lower = name.lower()
            if lower.endswith("/config/config.php") or lower == "config/config.php":
                markers["config"] = True
            if "nextclouddata/" in lower or "/data/" in lower:
                markers["data"] = True
            if "softsql" in lower or lower.endswith(".sql") or lower.endswith(".sql.gz"):
                markers["database"] = True
            if lower.endswith("/occ") or lower == "occ":
                markers["occ"] = True
            if "/themes/" in lower or lower.startswith("themes/"):
                markers["themes"] = True
            if all(markers.values()):
                break
    return markers


def verify_archive() -> dict[str, object]:
    info = FINAL_ARCHIVE.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError("off-host archive is not a regular file")
    if info.st_size != EXPECTED_SIZE_BYTES:
        raise RuntimeError("off-host archive size does not match the fixed recovery point")

    receipt = _load_receipt()
    digest = _sha256(FINAL_ARCHIVE)
    if digest != receipt["sha256"]:
        raise RuntimeError("off-host archive checksum does not match transfer receipt")

    gzip_check = subprocess.run(
        [GZIP, "-t", str(FINAL_ARCHIVE)],
        shell=False,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=3600,
    )
    if gzip_check.returncode != 0:
        raise RuntimeError("off-host archive failed gzip integrity validation")

    markers = _component_markers(FINAL_ARCHIVE)
    if not all(markers.values()):
        raise RuntimeError("off-host archive is missing one or more required recovery components")

    return {
        "schema_version": 1,
        "issue": ISSUE_NUMBER,
        "archive_name": ARCHIVE_NAME,
        "size_bytes": EXPECTED_SIZE_BYTES,
        "sha256": digest,
        "gzip_ok": True,
        "component_markers": markers,
        "secret_values_recorded": False,
    }


def main() -> int:
    print(json.dumps(verify_archive(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
