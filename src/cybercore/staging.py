from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yaml.tokens import AliasToken, AnchorToken, DirectiveToken


DENIED_LITERAL_PATTERNS = (
    "BEGIN OPENSSH PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "BEGIN PRIVATE KEY",
    "password=",
    "password:",
    "api_key=",
    "api_key:",
    "api-token",
    "api_token:",
    "private_key:",
    "secret_value:",
    "token:",
    "totp",
    "totp_seed:",
    "recovery_code",
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
    "verify_deployment_protocol_and_target_capability",
    "verify_no_production_credentials_are_reused",
    "verify_rollback_method",
    "verify_effect_verifier",
    "verify_operator_authorization_for_first_remote_write",
    "live_staging_deploy: blocked",
)

REQUIRED_TARGET_PREFLIGHT_CHECKS = {
    "verify_target_is_non_production",
    "verify_target_path_is_not_production_document_root",
    "verify_deployment_protocol_and_target_capability",
    "verify_no_production_credentials_are_reused",
    "verify_rollback_method",
    "verify_effect_verifier",
    "verify_operator_authorization_for_first_remote_write",
}

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
ALLOWED_DEPLOYMENT_PROTOCOLS = {"SFTP", "SSH"}
REQUIRED_STAGING_SECRET_ALIASES = {
    "INTERSERVER_STAGING_HOST",
    "INTERSERVER_STAGING_USER",
    "INTERSERVER_STAGING_PORT",
    "INTERSERVER_STAGING_SSH_KEY_OR_SFTP_PASSWORD",
}
REQUIRED_EFFECT_CHECKS = {
    "staging_url_returns_success",
    "deployed_version_marker_matches_source_commit",
    "production_url_is_unchanged",
    "no_denied_path_is_touched",
    "receipt_is_stored_without_secrets",
}
READINESS_TOP_LEVEL_KEYS = {
    "version",
    "target_id",
    "readiness_class",
    "remote_write_requested",
    "remote_write_allowed",
    "production_write_allowed",
    "plaintext_secret_values_present",
    "safe_secret_aliases_only",
    "fresh_operator_authorization_required",
    "staging_target_identity",
    "deployment_capability_readiness",
    "secret_alias_readiness",
    "rollback_readiness",
    "effect_verifier_readiness",
    "operator_authorization",
    "blocked_until",
}
READINESS_IDENTITY_KEYS = {
    "staging_url_status",
    "staging_url_safe_reference",
    "staging_path_status",
    "staging_path_safe_reference",
    "production_document_root_excluded",
}
READINESS_DEPLOYMENT_CAPABILITY_KEYS = {
    "deployment_protocol_status",
    "deployment_protocol",
    "target_capability_status",
    "target_capability_reference",
    "capability_evidence_secret_values_recorded",
    "capability_evidence_remote_write_performed",
}
READINESS_SECRET_ALIAS_KEYS = {
    "secret_alias_status",
    "required_aliases",
    "secret_values_recorded",
    "secret_values_read",
}
READINESS_ROLLBACK_KEYS = {
    "rollback_status",
    "rollback_method",
    "rollback_tested",
}
READINESS_EFFECT_VERIFIER_KEYS = {
    "effect_verifier_status",
    "required_checks",
}
READINESS_AUTHORIZATION_KEYS = {
    "operator_authorization_status",
    "authorization_reference",
}
EXPECTED_BLOCKED_UNTIL = {
    "staging_url_status": "VERIFIED",
    "staging_path_status": "VERIFIED",
    "deployment_protocol_status": "VERIFIED",
    "target_capability_status": "VERIFIED",
    "secret_alias_status": "VERIFIED",
    "rollback_status": "VERIFIED",
    "effect_verifier_status": "VERIFIED",
    "operator_authorization_status": "APPROVED",
}
YAML_MERGE_TAG = "tag:yaml.org,2002:merge"
STAGING_URL_SAFE_REFERENCE = "INTERSERVER_STAGING_URL_REFERENCE"
STAGING_PATH_SAFE_REFERENCE = "INTERSERVER_STAGING_PATH_REFERENCE"
TARGET_CAPABILITY_REFERENCE = "INTERSERVER_STAGING_TARGET_CAPABILITY_REFERENCE"
ROLLBACK_METHOD = "immutable_release_directory_with_current_symlink_or_timestamped_backup"
OPERATOR_AUTHORIZATION_REFERENCE = "OPERATOR_AUTHORIZATION_REFERENCE"


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


def _reject_yaml_metadata(text: str, errors: list[str]) -> None:
    try:
        for token in yaml.scan(text, Loader=yaml.SafeLoader):
            if isinstance(token, AnchorToken):
                errors.append("readiness evidence forbids YAML anchors")
            elif isinstance(token, AliasToken):
                errors.append("readiness evidence forbids YAML aliases")
            elif isinstance(token, DirectiveToken):
                errors.append("readiness evidence forbids YAML directives")
    except yaml.YAMLError as exc:
        errors.append(f"readiness evidence is invalid YAML: {exc}")


def _collect_duplicate_yaml_keys(node: Node, errors: list[str]) -> None:
    if isinstance(node, MappingNode):
        seen: set[str] = set()
        for key_node, value_node in node.value:
            if not isinstance(key_node, ScalarNode):
                errors.append("readiness evidence mapping keys must be scalar values")
            else:
                key = key_node.value
                if key == "<<":
                    errors.append("readiness evidence forbids YAML merge key: <<")
                elif key_node.tag == YAML_MERGE_TAG:
                    errors.append("readiness evidence forbids YAML merge tag")
                if key in seen:
                    errors.append(f"readiness evidence contains duplicate YAML key: {key}")
                seen.add(key)
            _collect_duplicate_yaml_keys(value_node, errors)
    elif isinstance(node, SequenceNode):
        for item in node.value:
            _collect_duplicate_yaml_keys(item, errors)


def _reject_unknown_keys(
    mapping: dict[str, object], allowed: set[str], context: str, errors: list[str]
) -> None:
    non_string = [repr(key) for key in mapping if not isinstance(key, str)]
    if non_string:
        errors.append(f"{context} contains non-string keys: {', '.join(non_string)}")

    unexpected = sorted(key for key in mapping if isinstance(key, str) and key not in allowed)
    if unexpected:
        errors.append(f"{context} contains unexpected keys: {', '.join(unexpected)}")


def _require_mapping(
    document: dict[str, object], key: str, errors: list[str]
) -> dict[str, object] | None:
    value = document.get(key)
    if not isinstance(value, dict):
        errors.append(f"readiness evidence requires mapping: {key}")
        return None
    return value


def _require_value(
    mapping: dict[str, object], key: str, expected: object, errors: list[str]
) -> None:
    value = mapping.get(key)
    if type(value) is not type(expected) or value != expected:
        errors.append(
            f"readiness evidence requires {key}: {expected}; got {value!r} "
            f"({type(value).__name__}, expected {type(expected).__name__})"
        )


def _require_allowed_string(
    mapping: dict[str, object], key: str, allowed: set[str], errors: list[str]
) -> None:
    value = mapping.get(key)
    if not isinstance(value, str) or value not in allowed:
        expected = ", ".join(sorted(allowed))
        errors.append(f"readiness evidence requires {key} to be one of: {expected}; got {value!r}")


def _require_string_set(
    mapping: dict[str, object], key: str, required: set[str], errors: list[str]
) -> None:
    value = mapping.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"readiness evidence requires string list: {key}")
        return

    actual = set(value)
    missing = sorted(required - actual)
    unexpected = sorted(actual - required)
    if missing:
        errors.append(f"readiness evidence missing {key}: {', '.join(missing)}")
    if unexpected:
        errors.append(f"readiness evidence contains unexpected {key}: {', '.join(unexpected)}")
    if len(value) != len(actual):
        errors.append(f"readiness evidence contains duplicate values in {key}")


def _validate_target_required_preflight(document: dict[str, object], errors: list[str]) -> None:
    value = document.get("required_preflight")
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append("target contract requires string list: required_preflight")
        return

    actual = set(value)
    missing = sorted(REQUIRED_TARGET_PREFLIGHT_CHECKS - actual)
    unexpected = sorted(actual - REQUIRED_TARGET_PREFLIGHT_CHECKS)
    if missing:
        errors.append(f"target contract required_preflight missing checks: {', '.join(missing)}")
    if unexpected:
        errors.append(f"target contract required_preflight contains unexpected checks: {', '.join(unexpected)}")
    if len(value) != len(actual):
        errors.append("target contract required_preflight contains duplicate checks")


def _validate_blocked_until(document: dict[str, object], errors: list[str]) -> None:
    value = document.get("blocked_until")
    if not isinstance(value, list):
        errors.append("readiness evidence requires list: blocked_until")
        return

    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict) or len(item) != 1:
            errors.append(
                f"readiness evidence blocked_until item {index} must have exactly one key"
            )
            continue

        key, status = next(iter(item.items()))
        if not isinstance(key, str):
            errors.append(f"readiness evidence blocked_until item {index} key must be a string")
            continue
        if key not in EXPECTED_BLOCKED_UNTIL:
            errors.append(f"readiness evidence blocked_until contains unexpected key: {key}")
            continue
        if key in seen:
            errors.append(f"readiness evidence blocked_until contains duplicate key: {key}")
            continue
        seen.add(key)

        expected = EXPECTED_BLOCKED_UNTIL[key]
        if type(status) is not type(expected) or status != expected:
            errors.append(
                f"readiness evidence blocked_until requires {key}: {expected}; got {status!r}"
            )

    missing = sorted(set(EXPECTED_BLOCKED_UNTIL) - seen)
    if missing:
        errors.append(f"readiness evidence blocked_until missing keys: {', '.join(missing)}")


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

    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        errors.append(f"target contract is invalid YAML: {exc}")
        loaded = None

    if not isinstance(loaded, dict):
        errors.append("target contract must be a mapping")
    else:
        _validate_target_required_preflight(loaded, errors)

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


def validate_remote_write_readiness(path: Path) -> ValidationResult:
    text = _read(path)
    errors: list[str] = []
    warnings: list[str] = []
    if not text:
        errors.append(f"missing remote-write readiness evidence: {path}")
        return ValidationResult(False, tuple(errors))

    if "#" in text:
        errors.append("readiness evidence forbids YAML comments")

    for literal in _find_denied_literals(text):
        errors.append(f"readiness evidence contains denied literal pattern: {literal}")

    _reject_yaml_metadata(text, errors)
    if errors:
        warnings.append("live staging remote write remains blocked")
        return ValidationResult(False, tuple(errors), tuple(warnings))

    try:
        node = yaml.compose(text, Loader=yaml.SafeLoader)
    except yaml.YAMLError as exc:
        errors.append(f"readiness evidence is invalid YAML: {exc}")
        return ValidationResult(False, tuple(errors))

    if node is None:
        errors.append("readiness evidence must not be empty")
        return ValidationResult(False, tuple(errors))

    _collect_duplicate_yaml_keys(node, errors)
    if errors:
        warnings.append("live staging remote write remains blocked")
        return ValidationResult(False, tuple(errors), tuple(warnings))

    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        errors.append(f"readiness evidence is invalid YAML: {exc}")
        return ValidationResult(False, tuple(errors))

    if not isinstance(loaded, dict):
        errors.append("readiness evidence must be a mapping")
        return ValidationResult(False, tuple(errors))
    document: dict[str, object] = loaded

    _reject_unknown_keys(document, READINESS_TOP_LEVEL_KEYS, "readiness evidence", errors)
    for key, expected in (
        ("version", 1),
        ("target_id", "interserver-shared-hosting-staging"),
        ("readiness_class", "pre_remote_write_gate"),
        ("remote_write_requested", False),
        ("remote_write_allowed", False),
        ("production_write_allowed", False),
        ("plaintext_secret_values_present", False),
        ("safe_secret_aliases_only", True),
        ("fresh_operator_authorization_required", True),
    ):
        _require_value(document, key, expected, errors)

    identity = _require_mapping(document, "staging_target_identity", errors)
    if identity is not None:
        _reject_unknown_keys(identity, READINESS_IDENTITY_KEYS, "staging_target_identity", errors)
        _require_value(identity, "staging_url_status", "VERIFIED", errors)
        _require_value(
            identity,
            "staging_url_safe_reference",
            STAGING_URL_SAFE_REFERENCE,
            errors,
        )
        _require_value(identity, "staging_path_status", "VERIFIED", errors)
        _require_value(
            identity,
            "staging_path_safe_reference",
            STAGING_PATH_SAFE_REFERENCE,
            errors,
        )
        _require_value(identity, "production_document_root_excluded", "VERIFIED", errors)

    capability = _require_mapping(document, "deployment_capability_readiness", errors)
    if capability is not None:
        _reject_unknown_keys(
            capability,
            READINESS_DEPLOYMENT_CAPABILITY_KEYS,
            "deployment_capability_readiness",
            errors,
        )
        _require_value(capability, "deployment_protocol_status", "VERIFIED", errors)
        _require_allowed_string(
            capability,
            "deployment_protocol",
            ALLOWED_DEPLOYMENT_PROTOCOLS,
            errors,
        )
        _require_value(capability, "target_capability_status", "VERIFIED", errors)
        _require_value(
            capability,
            "target_capability_reference",
            TARGET_CAPABILITY_REFERENCE,
            errors,
        )
        _require_value(
            capability,
            "capability_evidence_secret_values_recorded",
            False,
            errors,
        )
        _require_value(
            capability,
            "capability_evidence_remote_write_performed",
            False,
            errors,
        )

    secret_aliases = _require_mapping(document, "secret_alias_readiness", errors)
    if secret_aliases is not None:
        _reject_unknown_keys(
            secret_aliases, READINESS_SECRET_ALIAS_KEYS, "secret_alias_readiness", errors
        )
        _require_value(secret_aliases, "secret_alias_status", "VERIFIED", errors)
        _require_string_set(
            secret_aliases, "required_aliases", REQUIRED_STAGING_SECRET_ALIASES, errors
        )
        _require_value(secret_aliases, "secret_values_recorded", False, errors)
        _require_value(secret_aliases, "secret_values_read", False, errors)

    rollback = _require_mapping(document, "rollback_readiness", errors)
    if rollback is not None:
        _reject_unknown_keys(rollback, READINESS_ROLLBACK_KEYS, "rollback_readiness", errors)
        _require_value(rollback, "rollback_status", "VERIFIED", errors)
        _require_value(rollback, "rollback_method", ROLLBACK_METHOD, errors)
        _require_value(rollback, "rollback_tested", True, errors)

    verifier = _require_mapping(document, "effect_verifier_readiness", errors)
    if verifier is not None:
        _reject_unknown_keys(
            verifier,
            READINESS_EFFECT_VERIFIER_KEYS,
            "effect_verifier_readiness",
            errors,
        )
        _require_value(verifier, "effect_verifier_status", "VERIFIED", errors)
        _require_string_set(verifier, "required_checks", REQUIRED_EFFECT_CHECKS, errors)

    authorization = _require_mapping(document, "operator_authorization", errors)
    if authorization is not None:
        _reject_unknown_keys(
            authorization,
            READINESS_AUTHORIZATION_KEYS,
            "operator_authorization",
            errors,
        )
        _require_value(authorization, "operator_authorization_status", "APPROVED", errors)
        _require_value(
            authorization,
            "authorization_reference",
            OPERATOR_AUTHORIZATION_REFERENCE,
            errors,
        )

    _validate_blocked_until(document, errors)

    if errors:
        warnings.append("live staging remote write remains blocked")

    return ValidationResult(not errors, tuple(errors), tuple(warnings))


def validate_staging_plan(target_path: Path, manifest_path: Path) -> ValidationResult:
    target = validate_target_contract(target_path)
    manifest = validate_manifest(manifest_path)
    errors = (*target.errors, *manifest.errors)
    warnings = (*target.warnings, *manifest.warnings)
    return ValidationResult(not errors, errors, warnings)
