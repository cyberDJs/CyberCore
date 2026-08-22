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
    "run_id",
    "repository",
    "source_branch",
    "source_commit",
    "target_id",
    "deploy_mode",
    "rollback_mode",
    "effect_verifier",
    "operator_authorization_reference",
    "planned_remote_destination",
    "planned_rollback_mode_after_authorization",
    "planned_artifacts",
    "secret_aliases_required",
    "secret_values_allowed",
    "remote_write_requested",
    "remote_write_allowed",
    "production_write_allowed",
}

EXPECTED_ARTIFACTS = {"index.html", "cybercore-version.json"}
EXPECTED_SECRET_ALIASES = {
    "INTERSERVER_STAGING_HOST",
    "INTERSERVER_STAGING_USER",
    "INTERSERVER_STAGING_PORT",
    "INTERSERVER_STAGING_SSH_KEY_OR_SFTP_PASSWORD",
}
EXPECTED_EFFECT_CHECKS = {
    "staging_url_returns_success",
    "deployed_version_marker_matches_source_commit",
    "write_scope_matches_approved_staging_destination",
    "no_denied_path_is_touched",
    "receipt_is_stored_without_secrets",
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


@dataclass(frozen=True)
class FirstWriteManifestResult:
    ok: bool
    errors: tuple[str, ...]

    def as_text(self) -> str:
        lines = [f"wb0034 manifest: {'PASS' if self.ok else 'FAIL'}"]
        if self.errors:
            lines.append("errors:")
            lines.extend(f"- {error}" for error in self.errors)
        return "\n".join(lines)


def _collect_duplicate_keys(node: Node, errors: list[str]) -> None:
    if isinstance(node, MappingNode):
        seen: set[str] = set()
        for key_node, value_node in node.value:
            if not isinstance(key_node, ScalarNode):
                errors.append("manifest mapping keys must be scalar values")
            else:
                key = key_node.value
                if key == "<<" or key_node.tag == YAML_MERGE_TAG:
                    errors.append("manifest forbids YAML merge keys")
                if key in seen:
                    errors.append(f"manifest contains duplicate YAML key: {key}")
                seen.add(key)
            _collect_duplicate_keys(value_node, errors)
    elif isinstance(node, SequenceNode):
        for item in node.value:
            _collect_duplicate_keys(item, errors)


def _load_document(path: Path, errors: list[str]) -> dict[str, object] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"missing WB-0034 manifest: {path}")
        return None

    lowered = text.lower()
    for pattern in DENIED_LITERAL_PATTERNS:
        if pattern.lower() in lowered:
            errors.append(f"manifest contains denied literal pattern: {pattern}")

    depth = 0
    try:
        for token in yaml.scan(text, Loader=yaml.SafeLoader):
            if isinstance(token, YAML_NESTING_START_TOKENS):
                depth += 1
                if depth > MAX_YAML_NESTING_DEPTH:
                    errors.append(
                        f"manifest exceeds safe YAML nesting depth ({MAX_YAML_NESTING_DEPTH})"
                    )
                    return None
            elif isinstance(token, YAML_NESTING_END_TOKENS):
                depth = max(0, depth - 1)
            elif isinstance(token, AnchorToken):
                errors.append("manifest forbids YAML anchors")
            elif isinstance(token, AliasToken):
                errors.append("manifest forbids YAML aliases")
            elif isinstance(token, DirectiveToken):
                errors.append("manifest forbids YAML directives")
    except (RecursionError, yaml.YAMLError) as exc:
        errors.append(f"manifest is invalid YAML: {exc}")
        return None

    try:
        node = yaml.compose(text, Loader=yaml.SafeLoader)
    except (RecursionError, yaml.YAMLError) as exc:
        errors.append(f"manifest is invalid YAML: {exc}")
        return None

    if node is not None:
        try:
            _collect_duplicate_keys(node, errors)
        except RecursionError:
            errors.append("manifest exceeds safe YAML nesting depth")
            return None

    try:
        loaded = yaml.safe_load(text)
    except (RecursionError, yaml.YAMLError) as exc:
        errors.append(f"manifest is invalid YAML: {exc}")
        return None

    if not isinstance(loaded, dict):
        errors.append("manifest must be a YAML mapping")
        return None

    mapping = cast(dict[object, object], loaded)
    if any(not isinstance(key, str) for key in mapping):
        errors.append("manifest contains non-string top-level keys")
        return None
    return cast(dict[str, object], mapping)


def _reject_unknown_keys(
    mapping: dict[str, object], allowed: set[str], context: str, errors: list[str]
) -> None:
    unexpected = sorted(key for key in mapping if key not in allowed)
    if unexpected:
        errors.append(f"{context} contains unexpected keys: {', '.join(unexpected)}")


def _require_value(
    mapping: dict[str, object], key: str, expected: object, errors: list[str]
) -> None:
    value = mapping.get(key)
    if type(value) is not type(expected) or value != expected:
        errors.append(f"manifest requires {key}: {expected}; got {value!r}")


def _require_string_set(
    mapping: dict[str, object], key: str, expected: set[str], errors: list[str]
) -> None:
    value = mapping.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"manifest requires string list: {key}")
        return
    actual = cast(list[str], value)
    actual_set = set(actual)
    missing = sorted(expected - actual_set)
    unexpected = sorted(actual_set - expected)
    if missing:
        errors.append(f"manifest missing {key}: {', '.join(missing)}")
    if unexpected:
        errors.append(f"manifest contains unexpected {key}: {', '.join(unexpected)}")
    if len(actual) != len(actual_set):
        errors.append(f"manifest contains duplicate values in {key}")


def _is_full_commit_sha(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 40:
        return False
    return all(character in "0123456789abcdef" for character in value.lower())


def validate_first_write_manifest(path: Path) -> FirstWriteManifestResult:
    errors: list[str] = []
    document = _load_document(path, errors)
    if document is None:
        return FirstWriteManifestResult(False, tuple(errors))

    _reject_unknown_keys(document, EXPECTED_TOP_LEVEL_KEYS, "manifest", errors)
    _require_value(document, "version", 1, errors)
    _require_value(document, "run_id", "WB0034-FIRST-STAGING-WRITE-PLAN", errors)
    _require_value(document, "repository", "cyberDJs/CyberCore", errors)
    _require_value(document, "source_branch", "main", errors)

    source_commit = document.get("source_commit")
    if source_commit != "TBD" and not _is_full_commit_sha(source_commit):
        errors.append("manifest source_commit must be TBD or an exact 40-character commit SHA")

    _require_value(document, "target_id", "interserver-shared-hosting-staging", errors)
    _require_value(document, "deploy_mode", "plan_only", errors)
    _require_value(document, "rollback_mode", "no_remote_write", errors)
    _require_value(
        document,
        "operator_authorization_reference",
        "NOT_REQUIRED_FOR_PLAN_ONLY",
        errors,
    )
    _require_value(document, "planned_remote_destination", "cybercore-canary-<run_id>/", errors)
    _require_value(
        document,
        "planned_rollback_mode_after_authorization",
        "no_overwrite_unique_directory_scoped_delete_if_authorized",
        errors,
    )
    _require_string_set(document, "planned_artifacts", EXPECTED_ARTIFACTS, errors)
    _require_string_set(document, "secret_aliases_required", EXPECTED_SECRET_ALIASES, errors)
    _require_value(document, "secret_values_allowed", False, errors)
    _require_value(document, "remote_write_requested", False, errors)
    _require_value(document, "remote_write_allowed", False, errors)
    _require_value(document, "production_write_allowed", False, errors)

    verifier_value = document.get("effect_verifier")
    if not isinstance(verifier_value, dict):
        errors.append("manifest requires mapping: effect_verifier")
    else:
        raw_verifier = cast(dict[object, object], verifier_value)
        if any(not isinstance(key, str) for key in raw_verifier):
            errors.append("effect_verifier contains non-string keys")
        else:
            verifier = cast(dict[str, object], raw_verifier)
            _reject_unknown_keys(
                verifier,
                {"mode", "required_before_remote_write", "checks"},
                "effect_verifier",
                errors,
            )
            _require_value(verifier, "mode", "planned", errors)
            _require_value(verifier, "required_before_remote_write", True, errors)
            _require_string_set(verifier, "checks", EXPECTED_EFFECT_CHECKS, errors)

    return FirstWriteManifestResult(not errors, tuple(errors))
