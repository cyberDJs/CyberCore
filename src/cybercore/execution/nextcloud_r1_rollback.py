from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat

from cybercore.execution.nextcloud_r1_transfer import (
    BACKUP_ROOT,
    CREDENTIAL_ROOT,
    FINAL_ARCHIVE,
    KNOWN_HOSTS,
    PARTIAL_ARCHIVE,
    PRIVATE_KEY,
    SOURCE_SHA256,
    STATE_ROOT,
    _fsync_directory,
    _require_private_directory,
)


PUBLIC_KEY = CREDENTIAL_ROOT / "source_ed25519.pub"
ROLLBACK_RECEIPT = STATE_ROOT / "rollback-receipt.json"


def _regular_owned_or_absent(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise RuntimeError("rollback target is not a regular file")
    if info.st_uid != os.geteuid():
        raise RuntimeError("rollback target has unexpected owner")
    return True


def _unlink_if_present(path: Path, present: bool) -> bool:
    if not present:
        return False
    path.unlink()
    _fsync_directory(path.parent)
    return True


def _write_rollback_receipt(payload: dict[str, object]) -> None:
    temporary = ROLLBACK_RECEIPT.with_suffix(".json.tmp")
    if temporary.exists():
        raise RuntimeError("temporary rollback receipt already exists")
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
    os.replace(temporary, ROLLBACK_RECEIPT)
    _fsync_directory(STATE_ROOT)


def rollback_local() -> dict[str, object]:
    _require_private_directory(CREDENTIAL_ROOT)
    _require_private_directory(STATE_ROOT)
    _require_private_directory(BACKUP_ROOT)

    final_present = _regular_owned_or_absent(FINAL_ARCHIVE)
    partial_present = _regular_owned_or_absent(PARTIAL_ARCHIVE)
    private_present = _regular_owned_or_absent(PRIVATE_KEY)
    public_present = _regular_owned_or_absent(PUBLIC_KEY)
    known_hosts_present = _regular_owned_or_absent(KNOWN_HOSTS)
    source_hash_present = _regular_owned_or_absent(SOURCE_SHA256)

    removed = {
        "partial_removed": _unlink_if_present(PARTIAL_ARCHIVE, partial_present),
        "private_key_removed": _unlink_if_present(PRIVATE_KEY, private_present),
        "public_key_removed": _unlink_if_present(PUBLIC_KEY, public_present),
        "known_hosts_removed": _unlink_if_present(KNOWN_HOSTS, known_hosts_present),
        "source_checksum_evidence_removed": _unlink_if_present(
            SOURCE_SHA256,
            source_hash_present,
        ),
    }
    payload: dict[str, object] = {
        "schema_version": 1,
        "status": "LOCAL_CONTAINMENT_COMPLETE_REMOTE_REVOKE_REQUIRED",
        "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "final_archive_preserved": final_present,
        "transfer_receipt_preserved": True,
        "remote_authorized_key_cleanup_required": True,
        "secret_values_recorded": False,
        **removed,
    }
    _write_rollback_receipt(payload)
    return payload


def main() -> int:
    print(json.dumps(rollback_local(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
