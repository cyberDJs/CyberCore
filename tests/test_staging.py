from __future__ import annotations

from pathlib import Path

from cybercore.staging import validate_manifest, validate_staging_plan, validate_target_contract


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / ".cybercore/deploy/staging-targets/interserver-shared-hosting-staging.yaml"
MANIFEST = ROOT / ".cybercore/deploy/manifests/interserver-staging-plan-only.example.yaml"


def test_target_contract_is_fail_closed_and_non_secret() -> None:
    result = validate_target_contract(TARGET)

    assert result.ok, result.as_text()


def test_plan_only_manifest_is_valid_without_remote_authorization() -> None:
    result = validate_manifest(MANIFEST)

    assert result.ok, result.as_text()
    assert result.warnings == ("manifest source_commit is not pinned yet",)


def test_staging_plan_validates_target_and_manifest_together() -> None:
    result = validate_staging_plan(TARGET, MANIFEST)

    assert result.ok, result.as_text()


def test_manifest_blocks_staging_apply_without_remote_write_authorization(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        "\n".join(
            [
                "run_id: bad",
                "repository: cyberDJs/CyberCore",
                "source_branch: main",
                "source_commit: abc123",
                "target_id: interserver-shared-hosting-staging",
                "deploy_mode: staging_apply",
                "rollback_mode: none",
                "effect_verifier: none",
                "operator_authorization_reference: APPROVED",
            ]
        ),
        encoding="utf-8",
    )

    result = validate_manifest(manifest)

    assert not result.ok
    assert any("deploy_mode" in error for error in result.errors)
    assert any("must not claim remote-write authorization" in error for error in result.errors)


def test_target_contract_blocks_plaintext_secret_literals(tmp_path: Path) -> None:
    target = tmp_path / "target.yaml"
    target.write_text(TARGET.read_text(encoding="utf-8") + "\npassword=bad\n", encoding="utf-8")

    result = validate_target_contract(target)

    assert not result.ok
    assert any("denied literal" in error for error in result.errors)
