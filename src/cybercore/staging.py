from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DENIED_LITERAL_PATTERNS = (
    "BEGIN OPENSSH PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "BEGIN PRIVATE KEY",
    "password=",
    "api_key=",
    "api-token",
    "totp",
    "recovery_code",
    "secret_value:",
)

REQUIRED_TARGET_TOKENS = (
    "target_id: interserver-shared-hosting-staging",
    "environment_class: staging",
    "production_mutation_allowed: false",
    "production_credentials_allowed: false",
    "plaintext_secrets_in_repository: denied",
    "plaintext_secrets_in_chat: denied",
    "plaintext_secrets_in_drive_or_caser_docs: denied",
    "INTERSERVER_STAGING_HOST",
    "INTERSERVER_STAGING_USER",
    "INTERSERVER_STAGING_PORT",
    "INTERSERVER_STAGING_SSH_KEY_OR_SFTP_PASSWORD",
    "verify_target_is_non_production",
    "verify_target_path_is_not_production_document_root",
    "verify_no_production_credentials_are_reused",
    "verify_rollback_method",
    "verify_effect_verifier",
    "verify_operator_authorization_for_first_remote_write",
    "live_staging_deploy: blocked",
)

REQUIRED_MANIFEST_TOKENS = (
    "run_id:",
    "repository:",
    "source_branch:",
    "source_commit:",
    "target_id: interserver-shared-hosting-staging",
    "deploy_mode:",
    "rollback_mode:",
    "effect_verifier:",
    "operator_authorization_reference:",
)

ALLOWED_DEPLOY_MODES = ("plan_only", "dry_run")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def as_text(self) -> str:
        status = "PASS" if self.ok else "FAIL"
        lines = [f"staging validation: {status}"]
        if self.errors:
            lines.append("errors:")
            lines.extend(f"- {error}" for error in self.errors)
        if self.warnings:
            lines.append("warnings:")
            lines.extend(f"- {warning}" for warning in self.warnings)
        return "\n".join(lines)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _missing_tokens(text: str, required: Iterable[str]) -> tuple[str, ...]:
    return tuple(token for token in required if token not in text)


def _find_denied_literals(text: str) -> tuple[str, ...]:
    lowered = text.lower()
    found: list[str] = []
    for pattern in DENIED_LITERAL_PATTERNS:
        if pattern.lower() in lowered:
            found.append(pattern)
    return tuple(found)


def _extract_scalar(text: str, key: str) -> str | None:
    prefix = f"{key}:"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip().strip('"').strip("'")
    return None


def validate_target_contract(path: Path) -> ValidationResult:
    text = _read(path)
    errors: list[str] = []
    if not text:
        errors.append(f"missing target contract: {path}")
        return ValidationResult(False, tuple(errors))

    for token in _missing_tokens(text, REQUIRED_TARGET_TOKENS):
        errors.append(f"target contract missing required token: {token}")

    for literal in _find_denied_literals(text):
        errors.append(f"target contract contains denied literal pattern: {literal}")

    if "eimyherrer.com" not in text:
        errors.append("target contract must explicitly name production domain boundary")

    if "github_environment_secret_interserver_staging" in text and (
        "proposed_secret_locations_requiring_governance_acceptance" not in text
    ):
        errors.append("GitHub Environment secret storage must remain proposed, not active")

    return ValidationResult(not errors, tuple(errors))


def validate_manifest(path: Path) -> ValidationResult:
    text = _read(path)
    errors: list[str] = []
    warnings: list[str] = []
    if not text:
        errors.append(f"missing deployment manifest: {path}")
        return ValidationResult(False, tuple(errors))

    for token in _missing_tokens(text, REQUIRED_MANIFEST_TOKENS):
        errors.append(f"manifest missing required token: {token}")

    for literal in _find_denied_literals(text):
        errors.append(f"manifest contains denied literal pattern: {literal}")

    mode = _extract_scalar(text, "deploy_mode")
    if mode not in ALLOWED_DEPLOY_MODES:
        errors.append(
            "manifest deploy_mode must be plan_only or dry_run for WB-0029; "
            f"got {mode or 'MISSING'}"
        )

    source_commit = _extract_scalar(text, "source_commit")
    if source_commit in {None, "TBD", "UNKNOWN"}:
        warnings.append("manifest source_commit is not pinned yet")

    auth_ref = _extract_scalar(text, "operator_authorization_reference")
    if auth_ref not in {"NOT_REQUIRED_FOR_PLAN_ONLY", "NOT_REQUIRED_FOR_DRY_RUN"}:
        errors.append("manifest must not claim remote-write authorization in WB-0029")

    return ValidationResult(not errors, tuple(errors), tuple(warnings))


def validate_staging_plan(target_path: Path, manifest_path: Path) -> ValidationResult:
    target = validate_target_contract(target_path)
    manifest = validate_manifest(manifest_path)
    errors = (*target.errors, *manifest.errors)
    warnings = (*target.warnings, *manifest.warnings)
    return ValidationResult(not errors, errors, warnings)
