from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yaml.tokens import (
    AliasToken,
    AnchorToken,
    BlockEndToken,
    BlockMappingStartToken,
    BlockSequenceStartToken,
    DirectiveToken,
    FlowMappingEndToken,
    FlowMappingStartToken,
    FlowSequenceEndToken,
    FlowSequenceStartToken,
)


MAX_YAML_NESTING_DEPTH = 64
YAML_MERGE_TAG = "tag:yaml.org,2002:merge"
YAML_NESTING_START_TOKENS = (
    BlockMappingStartToken,
    BlockSequenceStartToken,
    FlowMappingStartToken,
    FlowSequenceStartToken,
)
YAML_NESTING_END_TOKENS = (BlockEndToken, FlowMappingEndToken, FlowSequenceEndToken)

EXPECTED_TOP_LEVEL_KEYS = {
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
    "source_artifact_readiness",
    "secret_alias_readiness",
    "rollback_readiness",
    "effect_verifier_readiness",
    "operator_authorization",
    "blocked_until",
}

REQUIRED_SECRET_ALIASES = {
    "INTERSERVER_STAGING_HOST",
    "INTERSERVER_STAGING_USER",
    "INTERSERVER_STAGING_PORT",
    "INTERSERVER_STAGING_SSH_KEY_OR_SFTP_PASSWORD",
}

REQUIRED_EFFECT_CHECKS = {
    "staging_url_returns_success",
    "deployed_version_marker_matches_source_commit",
    "write_scope_matches_approved_staging_destination",
    "no_denied_path_is_touched",
    "receipt_is_stored_without_secrets",
}

EXPECTED_BLOCKED_UNTIL = {
    "deployment_protocol_status": "VERIFIED",
    "target_capability_status": "VERIFIED",
    "deploy_identity_scope_status": "VERIFIED",
    "source_commit_status": "PINNED",
    "artifact_hashes_status": "VERIFIED",
    "secret_alias_status": "VERIFIED",
    "rollback_status": "VERIFIED",
    "effect_verifier_status": "VERIFIED",
    "operator_authorization_status": "APPROVED",
}

DENIED_LITERAL_PATTERNS = (
    "BEGIN OPENSSH PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "BEGIN PRIVATE KEY",
    "password=",
    "password:",
    "api_key=",
    "api_key:",
    "api_token:",
    "private_key:",
    "secret_value:",
    "totp_seed:",
    "recovery_code:",
)

PLACEHOLDER_REFERENCES = {
    "TBD",
    "UNKNOWN",
    "UNVERIFIED",
    "REQUIRED_BEFORE_REMOTE_WRITE",
    "OPERATOR_AUTHORIZATION_REFERENCE",
    "WB0034_DEPLOYMENT_PROTOCOL_READ_ONLY_VERIFICATION_REQUIRED",
    "WB0034_DEPLOY_IDENTITY_SCOPE_VERIFICATION_REQUIRED",
    "WB0034_ARTIFACT_HASHES_REQUIRED",
    "WB0034_EFFECT_VERIFIER_IMPLEMENTATION_REQUIRED",
}


@dataclass(frozen=True)
class FirstWriteReadinessResult:
    schema_ok: bool
    ready: bool
    errors: tuple[str, ...]
    blockers: tuple[str, ...]

    def as_text(self) -> str:
        schema = "PASS" if self.schema_ok else "FAIL"
        readiness = "READY" if self.ready else "BLOCKED"
        lines = [f"wb0034 readiness schema: {schema}", f"first remote write: {readiness}"]
        if self.errors:
            lines.append("errors:")
            lines.extend(f"- {error}" for error in self.errors)
        if self.blockers:
            lines.append("blockers:")
            lines.extend(f"- {blocker}" for blocker in self.blockers)
        return "\n".join(lines)


def _collect_duplicate_keys(node: Node, errors: list[str]) -> None:
    if isinstance(node, MappingNode):
        seen: set[str] = set()
        for key_node, value_node in node.value:
            if not isinstance(key_node, ScalarNode):
                errors.append("readiness mapping keys must be scalar values")
            else:
                key = key_node.value
                if key == "<<" or key_node.tag == YAML_MERGE_TAG:
                    errors.append("readiness forbids YAML merge keys")
                if key in seen:
                    errors.append(f"readiness contains duplicate YAML key: {key}")
                seen.add(key)
            _collect_duplicate_keys(value_node, errors)
    elif isinstance(node, SequenceNode):
        for item in node.value:
            _collect_duplicate_keys(item, errors)


def _load_document(path: Path, errors: list[str]) -> dict[str, object] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"missing readiness artifact: {path}")
        return None

    lowered = text.lower()
    for pattern in DENIED_LITERAL_PATTERNS:
        if pattern.lower() in lowered:
            errors.append(f"readiness contains denied literal pattern: {pattern}")

    depth = 0
    try:
        for token in yaml.scan(text, Loader=yaml.SafeLoader):
            if isinstance(token, YAML_NESTING_START_TOKENS):
                depth += 1
                if depth > MAX_YAML_NESTING_DEPTH:
                    errors.append(
                        f"readiness exceeds safe YAML nesting depth ({MAX_YAML_NESTING_DEPTH})"
                    )
                    return None
            elif isinstance(token, YAML_NESTING_END_TOKENS):
                depth = max(0, depth - 1)
            elif isinstance(token, AnchorToken):
                errors.append("readiness forbids YAML anchors")
            elif isinstance(token, AliasToken):
                errors.append("readiness forbids YAML aliases")
            elif isinstance(token, DirectiveToken):
                errors.append("readiness forbids YAML directives")
    except (RecursionError, yaml.YAMLError) as exc:
        errors.append(f"readiness is invalid YAML: {exc}")
        return None

    try:
        node = yaml.compose(text, Loader=yaml.SafeLoader)
    except (RecursionError, yaml.YAMLError) as exc:
        errors.append(f"readiness is invalid YAML: {exc}")
        return None

    if node is not None:
        try:
            _collect_duplicate_keys(node, errors)
        except RecursionError:
            errors.append("readiness exceeds safe YAML nesting depth")
            return None

    try:
        loaded = yaml.safe_load(text)
    except (RecursionError, yaml.YAMLError) as exc:
        errors.append(f"readiness is invalid YAML: {exc}")
        return None

    if not isinstance(loaded, dict):
        errors.append("readiness must be a YAML mapping")
        return None

    document = cast(dict[object, object], loaded)
    non_string = [repr(key) for key in document if not isinstance(key, str)]
    if non_string:
        errors.append(f"readiness contains non-string top-level keys: {', '.join(non_string)}")
        return None

    return cast(dict[str, object], document)


def _reject_unknown_keys(
    mapping: dict[str, object], allowed: set[str], context: str, errors: list[str]
) -> None:
    unexpected = sorted(key for key in mapping if key not in allowed)
    if unexpected:
        errors.append(f"{context} contains unexpected keys: {', '.join(unexpected)}")


def _require_mapping(
    document: dict[str, object], key: str, errors: list[str]
) -> dict[str, object] | None:
    value = document.get(key)
    if not isinstance(value, dict):
        errors.append(f"readiness requires mapping: {key}")
        return None
    mapping = cast(dict[object, object], value)
    if any(not isinstance(item, str) for item in mapping):
        errors.append(f"readiness mapping {key} contains non-string keys")
        return None
    return cast(dict[str, object], mapping)


def _require_value(
    mapping: dict[str, object], key: str, expected: object, errors: list[str]
) -> None:
    value = mapping.get(key)
    if type(value) is not type(expected) or value != expected:
        errors.append(f"readiness requires {key}: {expected}; got {value!r}")


def _require_string_set(
    mapping: dict[str, object], key: str, required: set[str], errors: list[str]
) -> None:
    value = mapping.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"readiness requires string list: {key}")
        return
    actual = cast(list[str], value)
    actual_set = set(actual)
    missing = sorted(required - actual_set)
    unexpected = sorted(actual_set - required)
    if missing:
        errors.append(f"readiness missing {key}: {', '.join(missing)}")
    if unexpected:
        errors.append(f"readiness contains unexpected {key}: {', '.join(unexpected)}")
    if len(actual) != len(actual_set):
        errors.append(f"readiness contains duplicate values in {key}")


def _validate_blocked_until(document: dict[str, object], errors: list[str]) -> None:
    value = document.get("blocked_until")
    if not isinstance(value, list):
        errors.append("readiness requires list: blocked_until")
        return

    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict) or len(item) != 1:
            errors.append(f"blocked_until item {index} must contain exactly one key")
            continue
        mapping = cast(dict[object, object], item)
        key, status = next(iter(mapping.items()))
        if not isinstance(key, str):
            errors.append(f"blocked_until item {index} key must be a string")
            continue
        if key not in EXPECTED_BLOCKED_UNTIL:
            errors.append(f"blocked_until contains unexpected key: {key}")
            continue
        if key in seen:
            errors.append(f"blocked_until contains duplicate key: {key}")
            continue
        seen.add(key)
        expected = EXPECTED_BLOCKED_UNTIL[key]
        if status != expected:
            errors.append(f"blocked_until requires {key}: {expected}; got {status!r}")

    missing = sorted(set(EXPECTED_BLOCKED_UNTIL) - seen)
    if missing:
        errors.append(f"blocked_until missing keys: {', '.join(missing)}")


def _is_full_commit_sha(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 40:
        return False
    return all(character in "0123456789abcdef" for character in value.lower())


def _has_evidence_reference(value: object) -> bool:
    if not isinstance(value, str):
        return False
    reference = value.strip()
    if len(reference) < 8:
        return False
    upper = reference.upper()
    if upper in PLACEHOLDER_REFERENCES:
        return False
    return not any(marker in upper for marker in ("TBD", "UNKNOWN", "UNVERIFIED", "REQUIRED"))


def _append_supporting_evidence_blockers(
    capability: dict[str, object] | None,
    source: dict[str, object] | None,
    rollback: dict[str, object] | None,
    verifier: dict[str, object] | None,
    authorization: dict[str, object] | None,
    blockers: list[str],
) -> None:
    if capability is not None:
        if capability.get("deployment_protocol_status") == "VERIFIED":
            if capability.get("deployment_protocol") not in {"SFTP", "SSH"}:
                blockers.append(
                    "deployment_protocol_status VERIFIED requires deployment_protocol SFTP or SSH"
                )
        if capability.get("target_capability_status") == "VERIFIED" and not _has_evidence_reference(
            capability.get("target_capability_reference")
        ):
            blockers.append(
                "target_capability_status VERIFIED requires non-placeholder capability evidence"
            )
        if capability.get("deploy_identity_scope_status") == "VERIFIED" and not _has_evidence_reference(
            capability.get("deploy_identity_scope_reference")
        ):
            blockers.append(
                "deploy_identity_scope_status VERIFIED requires non-placeholder scope evidence"
            )

    if source is not None:
        if source.get("source_commit_status") == "PINNED" and not _is_full_commit_sha(
            source.get("source_commit_reference")
        ):
            blockers.append("source_commit_status PINNED requires an exact 40-character commit SHA")
        if source.get("artifact_hashes_status") == "VERIFIED" and not _has_evidence_reference(
            source.get("artifact_hashes_reference")
        ):
            blockers.append(
                "artifact_hashes_status VERIFIED requires non-placeholder artifact hash evidence"
            )

    if rollback is not None:
        if rollback.get("rollback_status") == "VERIFIED" and rollback.get("rollback_tested") is not True:
            blockers.append("rollback_status VERIFIED requires rollback_tested: true")

    if verifier is not None:
        if verifier.get("effect_verifier_status") == "VERIFIED" and not _has_evidence_reference(
            verifier.get("effect_verifier_reference")
        ):
            blockers.append(
                "effect_verifier_status VERIFIED requires non-placeholder verifier evidence"
            )

    if authorization is not None:
        if authorization.get("operator_authorization_status") == "APPROVED" and not _has_evidence_reference(
            authorization.get("authorization_reference")
        ):
            blockers.append(
                "operator_authorization_status APPROVED requires a fresh non-placeholder authorization reference"
            )


def validate_first_write_readiness(path: Path) -> FirstWriteReadinessResult:
    errors: list[str] = []
    blockers: list[str] = []
    document = _load_document(path, errors)
    if document is None:
        return FirstWriteReadinessResult(False, False, tuple(errors), ())

    _reject_unknown_keys(document, EXPECTED_TOP_LEVEL_KEYS, "readiness", errors)
    _require_value(document, "version", 1, errors)
    _require_value(document, "target_id", "interserver-shared-hosting-staging", errors)
    _require_value(document, "readiness_class", "first_remote_write_preflight", errors)
    _require_value(document, "remote_write_requested", False, errors)
    _require_value(document, "remote_write_allowed", False, errors)
    _require_value(document, "production_write_allowed", False, errors)
    _require_value(document, "plaintext_secret_values_present", False, errors)
    _require_value(document, "safe_secret_aliases_only", True, errors)
    _require_value(document, "fresh_operator_authorization_required", True, errors)

    identity = _require_mapping(document, "staging_target_identity", errors)
    if identity is not None:
        _reject_unknown_keys(
            identity,
            {
                "staging_url_status",
                "staging_url_safe_reference",
                "staging_path_status",
                "staging_path_safe_reference",
                "production_document_root_excluded",
            },
            "staging_target_identity",
            errors,
        )
        _require_value(identity, "staging_url_status", "VERIFIED", errors)
        _require_value(
            identity, "staging_url_safe_reference", "INTERSERVER_STAGING_URL_REFERENCE", errors
        )
        _require_value(identity, "staging_path_status", "VERIFIED", errors)
        _require_value(
            identity,
            "staging_path_safe_reference",
            "INTERSERVER_STAGING_PATH_REFERENCE",
            errors,
        )
        _require_value(identity, "production_document_root_excluded", "VERIFIED", errors)

    capability = _require_mapping(document, "deployment_capability_readiness", errors)
    if capability is not None:
        _reject_unknown_keys(
            capability,
            {
                "deployment_protocol_status",
                "deployment_protocol",
                "target_capability_status",
                "deploy_identity_scope_status",
                "target_capability_reference",
                "deploy_identity_scope_reference",
                "capability_evidence_secret_values_recorded",
                "capability_evidence_remote_write_performed",
            },
            "deployment_capability_readiness",
            errors,
        )
        protocol = capability.get("deployment_protocol")
        if protocol not in {"UNVERIFIED", "SFTP", "SSH"}:
            errors.append(f"unsupported deployment_protocol: {protocol!r}")
        _require_value(capability, "capability_evidence_secret_values_recorded", False, errors)
        _require_value(capability, "capability_evidence_remote_write_performed", False, errors)

    source = _require_mapping(document, "source_artifact_readiness", errors)
    if source is not None:
        _reject_unknown_keys(
            source,
            {
                "source_commit_status",
                "source_commit_reference",
                "artifact_hashes_status",
                "artifact_hashes_reference",
            },
            "source_artifact_readiness",
            errors,
        )

    secrets = _require_mapping(document, "secret_alias_readiness", errors)
    if secrets is not None:
        _reject_unknown_keys(
            secrets,
            {
                "secret_alias_status",
                "required_aliases",
                "secret_values_recorded",
                "secret_values_read",
            },
            "secret_alias_readiness",
            errors,
        )
        _require_string_set(secrets, "required_aliases", REQUIRED_SECRET_ALIASES, errors)
        _require_value(secrets, "secret_values_recorded", False, errors)
        _require_value(secrets, "secret_values_read", False, errors)

    rollback = _require_mapping(document, "rollback_readiness", errors)
    if rollback is not None:
        _reject_unknown_keys(
            rollback,
            {"rollback_status", "rollback_method", "rollback_tested"},
            "rollback_readiness",
            errors,
        )
        _require_value(
            rollback,
            "rollback_method",
            "no_overwrite_unique_directory_scoped_delete_if_authorized",
            errors,
        )

    verifier = _require_mapping(document, "effect_verifier_readiness", errors)
    if verifier is not None:
        _reject_unknown_keys(
            verifier,
            {"effect_verifier_status", "effect_verifier_reference", "required_checks"},
            "effect_verifier_readiness",
            errors,
        )
        _require_string_set(verifier, "required_checks", REQUIRED_EFFECT_CHECKS, errors)

    authorization = _require_mapping(document, "operator_authorization", errors)
    if authorization is not None:
        _reject_unknown_keys(
            authorization,
            {"operator_authorization_status", "authorization_reference"},
            "operator_authorization",
            errors,
        )

    _validate_blocked_until(document, errors)

    if not errors:
        status_sources = {
            "deployment_protocol_status": capability,
            "target_capability_status": capability,
            "deploy_identity_scope_status": capability,
            "source_commit_status": source,
            "artifact_hashes_status": source,
            "secret_alias_status": secrets,
            "rollback_status": rollback,
            "effect_verifier_status": verifier,
            "operator_authorization_status": authorization,
        }
        for key, expected in EXPECTED_BLOCKED_UNTIL.items():
            mapping = status_sources[key]
            actual = mapping.get(key) if mapping is not None else None
            if actual != expected:
                blockers.append(f"{key} must become {expected}; current={actual!r}")

        _append_supporting_evidence_blockers(
            capability,
            source,
            rollback,
            verifier,
            authorization,
            blockers,
        )

    schema_ok = not errors
    ready = schema_ok and not blockers
    return FirstWriteReadinessResult(schema_ok, ready, tuple(errors), tuple(blockers))
