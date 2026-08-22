from __future__ import annotations

from pathlib import Path

from cybercore.first_write_manifest import validate_first_write_manifest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".cybercore/deploy/manifests/interserver-staging-wb0034-plan.yaml"
PINNED_SHA = "0123456789abcdef0123456789abcdef01234567"
RUN_ID = "20260822T183500Z-a1b2c3"
AUTH_REF = "approval:wb0034:20260822T183500Z"


def _mutated_manifest(tmp_path: Path, old: str, new: str) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(MANIFEST.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
    return path


def _final_manifest_text() -> str:
    return (
        MANIFEST.read_text(encoding="utf-8")
        .replace("run_id: WB0034-FIRST-STAGING-WRITE-PLAN", f"run_id: {RUN_ID}")
        .replace("source_commit: TBD", f"source_commit: {PINNED_SHA}")
        .replace(
            "operator_authorization_reference: NOT_REQUIRED_FOR_PLAN_ONLY",
            f"operator_authorization_reference: {AUTH_REF}",
        )
        .replace(
            "planned_remote_destination: cybercore-canary-<run_id>/",
            f"planned_remote_destination: cybercore-canary-{RUN_ID}/",
        )
    )


def test_current_wb0034_manifest_passes_strict_validator() -> None:
    result = validate_first_write_manifest(MANIFEST)

    assert result.ok, result.as_text()


def test_manifest_rejects_remote_write_authority(tmp_path: Path) -> None:
    manifest = _mutated_manifest(
        tmp_path,
        "remote_write_allowed: false",
        "remote_write_allowed: true",
    )

    result = validate_first_write_manifest(manifest)

    assert not result.ok
    assert any("remote_write_allowed" in error for error in result.errors)


def test_manifest_rejects_production_write_authority(tmp_path: Path) -> None:
    manifest = _mutated_manifest(
        tmp_path,
        "production_write_allowed: false",
        "production_write_allowed: true",
    )

    result = validate_first_write_manifest(manifest)

    assert not result.ok
    assert any("production_write_allowed" in error for error in result.errors)


def test_manifest_rejects_production_destination(tmp_path: Path) -> None:
    manifest = _mutated_manifest(
        tmp_path,
        "planned_remote_destination: cybercore-canary-<run_id>/",
        "planned_remote_destination: /home/eimyherr/domains/eimyherrer.com/public_html/",
    )

    result = validate_first_write_manifest(manifest)

    assert not result.ok
    assert any("planned_remote_destination" in error for error in result.errors)


def test_manifest_rejects_extra_artifact(tmp_path: Path) -> None:
    manifest = _mutated_manifest(
        tmp_path,
        "  - cybercore-version.json\n",
        "  - cybercore-version.json\n  - unexpected.php\n",
    )

    result = validate_first_write_manifest(manifest)

    assert not result.ok
    assert any("planned_artifacts" in error for error in result.errors)


def test_manifest_rejects_non_exact_source_commit(tmp_path: Path) -> None:
    manifest = _mutated_manifest(tmp_path, "source_commit: TBD", "source_commit: deadbeef")

    result = validate_first_write_manifest(manifest)

    assert not result.ok
    assert any("40-character commit SHA" in error for error in result.errors)


def test_manifest_accepts_exact_source_commit_in_plan_mode(tmp_path: Path) -> None:
    manifest = _mutated_manifest(tmp_path, "source_commit: TBD", f"source_commit: {PINNED_SHA}")

    result = validate_first_write_manifest(manifest)

    assert result.ok, result.as_text()


def test_final_preflight_rejects_plan_placeholders() -> None:
    result = validate_first_write_manifest(MANIFEST, final_preflight=True)

    assert not result.ok
    assert any("plan placeholder" in error for error in result.errors)
    assert any("final manifest source_commit" in error for error in result.errors)


def test_final_preflight_accepts_bound_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(_final_manifest_text(), encoding="utf-8")

    result = validate_first_write_manifest(manifest, final_preflight=True)

    assert result.ok, result.as_text()


def test_final_preflight_rejects_destination_not_bound_to_run_id(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        _final_manifest_text().replace(
            f"planned_remote_destination: cybercore-canary-{RUN_ID}/",
            "planned_remote_destination: cybercore-canary-other-run/",
        ),
        encoding="utf-8",
    )

    result = validate_first_write_manifest(manifest, final_preflight=True)

    assert not result.ok
    assert any("destination" in error for error in result.errors)


def test_manifest_rejects_plaintext_secret_assignment(tmp_path: Path) -> None:
    path = tmp_path / "manifest.yaml"
    path.write_text(
        MANIFEST.read_text(encoding="utf-8") + "\npassword: bad\n",
        encoding="utf-8",
    )

    result = validate_first_write_manifest(path)

    assert not result.ok
    assert any("credential-like assignment" in error for error in result.errors)


def test_manifest_rejects_secret_bearing_yaml_comment(tmp_path: Path) -> None:
    path = tmp_path / "manifest.yaml"
    path.write_text(
        MANIFEST.read_text(encoding="utf-8") + "\n# credential https://alice:hunter2@example.com\n",
        encoding="utf-8",
    )

    result = validate_first_write_manifest(path)

    assert not result.ok
    assert any("forbids YAML comments" in error for error in result.errors)


def test_manifest_rejects_credential_url_scalar(tmp_path: Path) -> None:
    path = tmp_path / "manifest.yaml"
    path.write_text(
        MANIFEST.read_text(encoding="utf-8").replace(
            "operator_authorization_reference: NOT_REQUIRED_FOR_PLAN_ONLY",
            "operator_authorization_reference: https://alice:hunter2@example.com/approval",
        ),
        encoding="utf-8",
    )

    result = validate_first_write_manifest(path)

    assert not result.ok
    assert any("credential-bearing URL" in error for error in result.errors)
