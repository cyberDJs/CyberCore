from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

import yaml

EXPECTED_TARGET_ID = "interserver-shared-hosting-staging"
EXPECTED_PROVIDER = "InterServer"
CANONICAL_REPOSITORY = "cyberDJs/CyberCore"
ALLOWED_LOCAL_MODES = ("plan_only", "dry_run")
REMOTE_MODES = {"staging_apply", "staging_apply_after_explicit_operator_approval"}
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SENSITIVE_VALUE_KEYS = {
    "api_key",
    "api_token",
    "credential",
    "credentials",
    "password",
    "private_key",
    "recovery_code",
    "secret",
    "secret_value",
    "session_cookie",
    "token",
    "totp_seed",
}
APPROVED_SECRET_LOCATIONS = {"os_backed_secret_store", "approved_external_vault"}
REQUIRED_PREFLIGHT = frozenset(
    {
        "verify_target_is_non_production",
        "verify_target_path_is_not_production_document_root",
        "verify_no_production_credentials_are_reused",
        "verify_rollback_method",
        "verify_effect_verifier",
        "verify_operator_authorization_for_first_remote_write",
    }
)
REQUIRED_EVIDENCE_FIELDS = frozenset(
    {
        "run_id",
        "timestamp",
        "repository",
        "source_branch",
        "source_commit",
        "target_id",
        "deploy_mode",
        "verifier_result",
        "rollback_mode",
        "operator_authorization_reference",
    }
)


class StagingValidationError(ValueError):
    """Raised when a staging plan violates a fail-closed safety contract."""


@dataclass(frozen=True)
class TargetAssessment:
    target_id: str
    mode: str
    ready: bool
    plan_status: str
    remote_write_allowed: bool
    unresolved_gates: tuple[str, ...]


@dataclass(frozen=True)
class DeploymentManifest:
    run_id: str
    repository: str
    source_branch: str
    source_commit: str
    artifact_identity: str
    target_id: str
    deploy_mode: str
    plan_status: str
    evidence_destination: str
    remote_write_allowed: bool
    unresolved_gates: tuple[str, ...]


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise StagingValidationError(f"{name} must be a mapping")
    return value


def _string_list(value: object, name: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        raise StagingValidationError(f"{name} must contain non-empty strings")
    return value


def load_target(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise StagingValidationError("target document must be a mapping")
    _reject_sensitive_value_keys(loaded)
    return loaded


def _reject_sensitive_value_keys(value: object, path: str = "target") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).strip().lower()
            if key_text in SENSITIVE_VALUE_KEYS:
                raise StagingValidationError(
                    f"sensitive value field is forbidden in target metadata: {path}.{key}"
                )
            _reject_sensitive_value_keys(child, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _reject_sensitive_value_keys(child, f"{path}[{index}]")


def _is_unresolved(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        normalized = value.strip().upper()
        return not normalized or normalized.startswith("TBD_") or "UNKNOWN" in normalized
    return False


def _host(value: str) -> str:
    candidate = value if "://" in value else f"https://{value}"
    return (urlparse(candidate).hostname or "").lower().rstrip(".")


def _validate_secret_policy(target: Mapping[str, Any]) -> tuple[str, ...]:
    secret_policy = _mapping(target.get("secret_policy"), "secret_policy")
    for field in (
        "plaintext_secrets_in_repository",
        "plaintext_secrets_in_chat",
        "plaintext_secrets_in_drive_or_caser_docs",
    ):
        if secret_policy.get(field) != "denied":
            raise StagingValidationError(f"{field} must remain denied")

    approved_locations = set(
        _string_list(secret_policy.get("approved_secret_locations"), "approved_secret_locations")
    )
    if not approved_locations <= APPROVED_SECRET_LOCATIONS:
        raise StagingValidationError("approved_secret_locations contains an unauthorized store")

    _string_list(secret_policy.get("required_secret_aliases"), "required_secret_aliases")
    unresolved: list[str] = []
    if secret_policy.get("alias_verification_status") != "verified":
        unresolved.append("secret_policy.alias_verification_status")
    return tuple(unresolved)


def _require_contract_members(
    target: Mapping[str, Any],
    *,
    field: str,
    required: frozenset[str],
) -> None:
    actual = set(_string_list(target.get(field), field))
    missing = sorted(required - actual)
    if missing:
        raise StagingValidationError(f"{field} is missing required entries: {', '.join(missing)}")


def assess_target(target: Mapping[str, Any], *, mode: str) -> TargetAssessment:
    if mode in REMOTE_MODES or mode not in ALLOWED_LOCAL_MODES:
        raise StagingValidationError(
            f"deploy mode {mode!r} is not authorized; this slice supports plan_only/dry_run only"
        )

    target_id = target.get("target_id")
    if target_id != EXPECTED_TARGET_ID:
        raise StagingValidationError(f"target_id must be {EXPECTED_TARGET_ID}")
    if target.get("provider") != EXPECTED_PROVIDER:
        raise StagingValidationError(f"provider must be {EXPECTED_PROVIDER}")
    if target.get("environment_class") != "staging":
        raise StagingValidationError("environment_class must be staging")

    production = _mapping(target.get("production_boundary"), "production_boundary")
    production_domains = _string_list(production.get("production_domains"), "production_domains")
    if production.get("production_mutation_allowed") is not False:
        raise StagingValidationError("production mutation must remain denied")
    if production.get("production_credentials_allowed") is not False:
        raise StagingValidationError("production credentials must remain denied")
    if production.get("provider_mutation_allowed_without_explicit_approval") is not False:
        raise StagingValidationError(
            "provider mutation without explicit approval must remain denied"
        )

    _require_contract_members(target, field="required_preflight", required=REQUIRED_PREFLIGHT)

    gate_state = _mapping(target.get("current_gate_state"), "current_gate_state")
    if gate_state.get("live_staging_deploy") != "blocked":
        raise StagingValidationError("live_staging_deploy must remain blocked in this slice")

    allowed_modes = _string_list(target.get("allowed_modes"), "allowed_modes")
    if mode not in allowed_modes:
        raise StagingValidationError(f"target does not allow local mode {mode!r}")

    identity = _mapping(target.get("staging_identity"), "staging_identity")
    if identity.get("deployment_user_scope") != "staging_path_only":
        raise StagingValidationError("deployment_user_scope must remain staging_path_only")

    unresolved: list[str] = []
    for field in ("domain_or_url", "document_root", "capability_status"):
        if _is_unresolved(identity.get(field)):
            unresolved.append(f"staging_identity.{field}")

    domain_or_url = identity.get("domain_or_url")
    if isinstance(domain_or_url, str) and not _is_unresolved(domain_or_url):
        denied_hosts = {_host(domain) for domain in production_domains}
        if _host(domain_or_url) in denied_hosts:
            raise StagingValidationError("staging domain resolves to a denied production domain")

    rollback = _mapping(target.get("rollback"), "rollback")
    if rollback.get("block_if_no_rollback_for_nontrivial_change") is not True:
        raise StagingValidationError(
            "rollback must block nontrivial changes when no rollback exists"
        )
    if _is_unresolved(rollback.get("verified_mode")):
        unresolved.append("rollback.verified_mode")

    evidence = _mapping(target.get("evidence"), "evidence")
    if evidence.get("receipt_class") != "staging_deploy_receipt":
        raise StagingValidationError("evidence receipt_class must remain staging_deploy_receipt")
    if evidence.get("secret_values_allowed") is not False:
        raise StagingValidationError("evidence must deny secret values")
    _require_contract_members(
        evidence,
        field="required_fields",
        required=REQUIRED_EVIDENCE_FIELDS,
    )

    verifier = target.get("effect_verifier")
    if not isinstance(verifier, Mapping) or verifier.get("status") != "verified":
        unresolved.append("effect_verifier.status")

    unresolved.extend(_validate_secret_policy(target))
    unresolved_tuple = tuple(sorted(set(unresolved)))

    if mode == "dry_run" and unresolved_tuple:
        raise StagingValidationError(
            "dry_run target gates unresolved: " + ", ".join(unresolved_tuple)
        )

    if mode == "dry_run":
        plan_status = "DRY_RUN_READY"
    elif unresolved_tuple:
        plan_status = "BLOCKED"
    else:
        plan_status = "PLANNED"

    return TargetAssessment(
        target_id=target_id,
        mode=mode,
        ready=not unresolved_tuple,
        plan_status=plan_status,
        remote_write_allowed=False,
        unresolved_gates=unresolved_tuple,
    )


def _safe_relative_path(value: str, name: str) -> str:
    if not value.strip():
        raise StagingValidationError(f"{name} must be non-empty")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise StagingValidationError(f"{name} must be a safe relative path")
    return value


def _validate_output_destination(output: Path, evidence_destination: str) -> None:
    output_text = _safe_relative_path(output.as_posix(), "output")
    evidence_text = _safe_relative_path(evidence_destination, "evidence_destination")
    if PurePosixPath(output_text) != PurePosixPath(evidence_text):
        raise StagingValidationError("output must match evidence_destination")


def build_manifest(
    assessment: TargetAssessment,
    *,
    run_id: str,
    repository: str,
    source_branch: str,
    source_commit: str,
    artifact_identity: str,
    evidence_destination: str,
) -> DeploymentManifest:
    if repository != CANONICAL_REPOSITORY:
        raise StagingValidationError(f"repository must be {CANONICAL_REPOSITORY}")
    if not source_branch.strip():
        raise StagingValidationError("source_branch must be non-empty")
    if SHA40.fullmatch(source_commit) is None:
        raise StagingValidationError("source_commit must be a lowercase 40-character git SHA")
    if not run_id.strip():
        raise StagingValidationError("run_id must be non-empty")
    if not artifact_identity.strip():
        raise StagingValidationError("artifact_identity must be non-empty")
    _safe_relative_path(evidence_destination, "evidence_destination")

    return DeploymentManifest(
        run_id=run_id,
        repository=repository,
        source_branch=source_branch,
        source_commit=source_commit,
        artifact_identity=artifact_identity,
        target_id=assessment.target_id,
        deploy_mode=assessment.mode,
        plan_status=assessment.plan_status,
        evidence_destination=evidence_destination,
        remote_write_allowed=False,
        unresolved_gates=assessment.unresolved_gates,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a local CyberCore staging plan")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--mode", choices=ALLOWED_LOCAL_MODES, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repository", default=CANONICAL_REPOSITORY)
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--artifact-identity", required=True)
    parser.add_argument("--evidence-destination", default="staging-manifest.json")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        target = load_target(args.target)
        assessment = assess_target(target, mode=args.mode)
        manifest = build_manifest(
            assessment,
            run_id=args.run_id,
            repository=args.repository,
            source_branch=args.source_branch,
            source_commit=args.source_commit,
            artifact_identity=args.artifact_identity,
            evidence_destination=args.evidence_destination,
        )
        _validate_output_destination(args.output, args.evidence_destination)
    except (OSError, yaml.YAMLError, StagingValidationError) as exc:
        print(f"BLOCKED: {exc}")
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(asdict(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"PLAN_CREATED: status={manifest.plan_status} mode={manifest.deploy_mode} "
        f"target={manifest.target_id} remote_write=false"
    )
    if manifest.unresolved_gates:
        print("UNRESOLVED: " + ", ".join(manifest.unresolved_gates))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
