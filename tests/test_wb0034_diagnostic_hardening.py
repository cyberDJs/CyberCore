from __future__ import annotations

import json
from pathlib import Path

from cybercore import first_write_packet as first_write_packet_module
from cybercore.first_write import validate_first_write_readiness
from cybercore.first_write_manifest import validate_first_write_manifest
from cybercore.first_write_packet import validate_first_write_packet


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".cybercore/deploy/manifests/interserver-staging-wb0034-plan.yaml"
READINESS = ROOT / ".cybercore/deploy/readiness/interserver-staging-readiness.wb0034.yaml"
SECRET_LITERAL = "xoxb-1234567890ABCDEF"
OPAQUE_SECRET = "npm_abcdefghijklmnopqrstuvwxyz0123456789"
PINNED_SHA = "0123456789abcdef0123456789abcdef01234567"
RUN_ID = "20260822T183500Z-a1b2c3"


def test_packet_scans_sensitive_text_before_yaml_parse(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    readiness = tmp_path / "readiness.yaml"
    manifest.write_text(f"version: [{SECRET_LITERAL}\n", encoding="utf-8")
    readiness.write_text(READINESS.read_text(encoding="utf-8"), encoding="utf-8")

    result = validate_first_write_packet(
        manifest,
        readiness,
        tmp_path / "repo",
        tmp_path / "artifacts",
    )

    rendered = result.as_text()
    assert not result.ready
    assert SECRET_LITERAL not in rendered
    assert "recognizable credential literal" in rendered


def test_version_marker_mismatch_does_not_echo_rejected_value() -> None:
    marker = {
        "repository": SECRET_LITERAL,
        "commit": PINNED_SHA,
        "branch": "main",
        "built_at": "2026-08-22T18:35:00Z",
        "environment": "interserver-shared-hosting-staging",
        "run_id": RUN_ID,
    }
    errors: list[str] = []

    first_write_packet_module._validate_version_marker(
        (json.dumps(marker, sort_keys=True) + "\n").encode("utf-8"),
        expected_commit=PINNED_SHA,
        expected_run_id=RUN_ID,
        errors=errors,
    )

    rendered = "\n".join(errors)
    assert SECRET_LITERAL not in rendered
    assert any("repository" in error for error in errors)


def test_manifest_redacts_unexpected_list_member(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        MANIFEST.read_text(encoding="utf-8").replace(
            "  - cybercore-version.json\n",
            f"  - cybercore-version.json\n  - {OPAQUE_SECRET}\n",
        ),
        encoding="utf-8",
    )

    result = validate_first_write_manifest(manifest)

    rendered = result.as_text()
    assert not result.ok
    assert OPAQUE_SECRET not in rendered
    assert "unexpected values in planned_artifacts" in rendered


def test_readiness_redacts_unexpected_list_member(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        READINESS.read_text(encoding="utf-8").replace(
            "    - INTERSERVER_STAGING_HOST\n",
            f"    - INTERSERVER_STAGING_HOST\n    - {OPAQUE_SECRET}\n",
        ),
        encoding="utf-8",
    )

    result = validate_first_write_readiness(readiness)

    rendered = result.as_text()
    assert not result.schema_ok
    assert OPAQUE_SECRET not in rendered
    assert "unexpected values in required_aliases" in rendered


def test_manifest_directory_and_invalid_utf8_are_validation_failures(tmp_path: Path) -> None:
    directory = tmp_path / "manifest-directory"
    directory.mkdir()
    directory_result = validate_first_write_manifest(directory)

    invalid_utf8 = tmp_path / "manifest-invalid-utf8.yaml"
    invalid_utf8.write_bytes(b"\xff\xfe\xfd")
    utf8_result = validate_first_write_manifest(invalid_utf8)

    assert not directory_result.ok
    assert "cannot read WB-0034 manifest" in directory_result.as_text()
    assert not utf8_result.ok
    assert "cannot read WB-0034 manifest" in utf8_result.as_text()


def test_readiness_directory_and_invalid_utf8_are_validation_failures(tmp_path: Path) -> None:
    directory = tmp_path / "readiness-directory"
    directory.mkdir()
    directory_result = validate_first_write_readiness(directory)

    invalid_utf8 = tmp_path / "readiness-invalid-utf8.yaml"
    invalid_utf8.write_bytes(b"\xff\xfe\xfd")
    utf8_result = validate_first_write_readiness(invalid_utf8)

    assert not directory_result.schema_ok
    assert "cannot read readiness artifact" in directory_result.as_text()
    assert not utf8_result.schema_ok
    assert "cannot read readiness artifact" in utf8_result.as_text()
