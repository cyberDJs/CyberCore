from __future__ import annotations

from pathlib import Path

from cybercore.first_write_manifest import validate_first_write_manifest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".cybercore/deploy/manifests/interserver-staging-wb0034-plan.yaml"


def _mutated_manifest(tmp_path: Path, old: str, new: str) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(MANIFEST.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
    return path


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


def test_manifest_accepts_exact_source_commit(tmp_path: Path) -> None:
    exact_sha = "0123456789abcdef0123456789abcdef01234567"
    manifest = _mutated_manifest(tmp_path, "source_commit: TBD", f"source_commit: {exact_sha}")

    result = validate_first_write_manifest(manifest)

    assert result.ok, result.as_text()


def test_manifest_rejects_plaintext_secret_literals(tmp_path: Path) -> None:
    path = tmp_path / "manifest.yaml"
    path.write_text(
        MANIFEST.read_text(encoding="utf-8") + "\npassword: bad\n",
        encoding="utf-8",
    )

    result = validate_first_write_manifest(path)

    assert not result.ok
    assert any("denied literal" in error for error in result.errors)
