from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cybercore.workblock import WorkBlockError, verify_workblock


def write_package(root: Path) -> Path:
    package = root / "WB-0099-test"
    (package / "actions").mkdir(parents=True)

    manifest = {
        "schema": "cxp/v1",
        "id": "WB-0099-test",
        "title": "Test Work Block",
        "risk": "low",
        "target_branch": None,
    }
    (package / "manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    (package / "README.md").write_text("# Test\n", encoding="utf-8")
    (package / "actions/verify.sh").write_text(
        "#!/usr/bin/env bash\nexit 0\n",
        encoding="utf-8",
    )
    (package / "actions/apply.sh").write_text(
        "#!/usr/bin/env bash\nexit 0\n",
        encoding="utf-8",
    )

    entries = []
    for relative in (
        "manifest.json",
        "README.md",
        "actions/verify.sh",
        "actions/apply.sh",
    ):
        data = (package / relative).read_bytes()
        entries.append(
            f"{hashlib.sha256(data).hexdigest()}  {relative}"
        )

    (package / "checksums.sha256").write_text(
        "\n".join(entries) + "\n",
        encoding="utf-8",
    )
    return package


def test_verify_workblock(tmp_path: Path) -> None:
    package = write_package(tmp_path)
    report = verify_workblock(package)
    assert report.manifest.identifier == "WB-0099-test"
    assert len(report.verified_files) == 4


def test_rejects_checksum_mismatch(tmp_path: Path) -> None:
    package = write_package(tmp_path)
    (package / "README.md").write_text("tampered\n", encoding="utf-8")

    with pytest.raises(WorkBlockError, match="checksum mismatch"):
        verify_workblock(package)


def test_rejects_path_traversal(tmp_path: Path) -> None:
    package = write_package(tmp_path)
    checksum = hashlib.sha256(b"x").hexdigest()

    (package / "checksums.sha256").write_text(
        f"{checksum}  ../outside\n",
        encoding="utf-8",
    )

    with pytest.raises(WorkBlockError, match="unsafe checksum path"):
        verify_workblock(package)
