from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from typing import cast

import yaml
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

from cybercore.first_write_security import scan_first_write_yaml_text


EXPECTED_ARTIFACTS = {"index.html", "cybercore-version.json"}
EXPECTED_ROLLBACK_METHOD = "no_overwrite_unique_directory_scoped_delete_if_authorized"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{7,63}$")
HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")
HEX40_RE = re.compile(r"^[0-9a-fA-F]{40}$")
PLACEHOLDER_MARKERS = ("TBD", "UNKNOWN", "UNVERIFIED", "REQUIRED", "PLACEHOLDER")
MAX_YAML_NESTING_DEPTH = 64
YAML_NESTING_START_TOKENS = (
    BlockMappingStartToken,
    BlockSequenceStartToken,
    FlowMappingStartToken,
    FlowSequenceStartToken,
)
YAML_NESTING_END_TOKENS = (BlockEndToken, FlowMappingEndToken, FlowSequenceEndToken)


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: UniqueKeyLoader, node: yaml.nodes.MappingNode, deep: bool = False
) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


@dataclass(frozen=True)
class FirstWriteEvidenceResult:
    ok: bool
    errors: tuple[str, ...]
    sha256: str | None = None
    source_commit: str | None = None
    run_id: str | None = None
    destination: str | None = None
    artifacts: tuple[str, ...] = ()
    protocol: str | None = None
    target_capability_reference: str | None = None
    deploy_identity_scope_reference: str | None = None
    effect_verifier_reference: str | None = None
    authorization_reference: str | None = None
    artifact_hashes: tuple[tuple[str, str], ...] = ()

    def as_text(self) -> str:
        lines = [f"wb0034 evidence bundle: {'PASS' if self.ok else 'FAIL'}"]
        if self.errors:
            lines.append("errors:")
            lines.extend(f"- {error}" for error in self.errors)
        return "\n".join(lines)


def resolve_evidence_bundle_path(readiness_path: Path, reference: object) -> Path | None:
    if not isinstance(reference, str) or not reference.strip():
        return None

    raw = Path(reference)
    if raw.is_absolute():
        return None

    readiness_dir = readiness_path.resolve().parent
    deploy_root = readiness_dir.parent
    candidate = (readiness_dir / raw).resolve()

    try:
        candidate.relative_to(deploy_root)
    except ValueError:
        return None

    if candidate.suffix not in {".yaml", ".yml"}:
        return None
    return candidate


def _require_mapping(
    document: dict[str, object], key: str, errors: list[str]
) -> dict[str, object] | None:
    value = document.get(key)
    if not isinstance(value, dict):
        errors.append(f"evidence requires mapping: {key}")
        return None
    raw = cast(dict[object, object], value)
    if any(not isinstance(item, str) for item in raw):
        errors.append(f"evidence mapping {key} contains non-string keys")
        return None
    return cast(dict[str, object], raw)


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
        errors.append(f"evidence requires {key}: {expected}; got {value!r}")


def _non_placeholder_reference(value: object) -> bool:
    if not isinstance(value, str) or len(value.strip()) < 8:
        return False
    upper = value.upper()
    return not any(marker in upper for marker in PLACEHOLDER_MARKERS)


def _string_set(value: object, errors: list[str], context: str) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"evidence requires string list: {context}")
        return set()
    items = cast(list[str], value)
    result = set(items)
    if len(items) != len(result):
        errors.append(f"evidence contains duplicate values in {context}")
    return result


def _scan_safe_yaml_structure(text: str, errors: list[str]) -> bool:
    depth = 0
    try:
        for token in yaml.scan(text, Loader=yaml.SafeLoader):
            if isinstance(token, YAML_NESTING_START_TOKENS):
                depth += 1
                if depth > MAX_YAML_NESTING_DEPTH:
                    errors.append(
                        f"evidence bundle exceeds safe YAML nesting depth ({MAX_YAML_NESTING_DEPTH})"
                    )
                    return False
            elif isinstance(token, YAML_NESTING_END_TOKENS):
                depth = max(0, depth - 1)
            elif isinstance(token, AnchorToken):
                errors.append("evidence bundle forbids YAML anchors")
            elif isinstance(token, AliasToken):
                errors.append("evidence bundle forbids YAML aliases")
            elif isinstance(token, DirectiveToken):
                errors.append("evidence bundle forbids YAML directives")
    except (RecursionError, yaml.YAMLError) as exc:
        errors.append(f"evidence bundle is invalid YAML: {exc}")
        return False
    return True


def validate_first_write_evidence(
    path: Path,
    *,
    expected_sha256: str | None = None,
) -> FirstWriteEvidenceResult:
    errors: list[str] = []
    try:
        raw_bytes = path.read_bytes()
    except FileNotFoundError:
        return FirstWriteEvidenceResult(False, (f"missing evidence bundle: {path}",))

    digest = hashlib.sha256(raw_bytes).hexdigest()
    if expected_sha256 is not None:
        if not HEX64_RE.fullmatch(expected_sha256):
            errors.append("readiness evidence_bundle_sha256 must be 64 hexadecimal characters")
        elif digest.lower() != expected_sha256.lower():
            errors.append("evidence bundle sha256 does not match readiness binding")

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return FirstWriteEvidenceResult(False, ("evidence bundle must be UTF-8",), digest)

    errors.extend(scan_first_write_yaml_text(text, "evidence bundle"))

    if not _scan_safe_yaml_structure(text, errors):
        return FirstWriteEvidenceResult(False, tuple(errors), digest)

    try:
        loaded = yaml.load(text, Loader=UniqueKeyLoader)
    except (RecursionError, yaml.YAMLError) as exc:
        errors.append(f"evidence bundle is invalid YAML: {exc}")
        return FirstWriteEvidenceResult(False, tuple(errors), digest)

    if not isinstance(loaded, dict):
        errors.append("evidence bundle must be a YAML mapping")
        return FirstWriteEvidenceResult(False, tuple(errors), digest)

    raw_document = cast(dict[object, object], loaded)
    if any(not isinstance(key, str) for key in raw_document):
        errors.append("evidence bundle contains non-string top-level keys")
        return FirstWriteEvidenceResult(False, tuple(errors), digest)
    document = cast(dict[str, object], raw_document)

    _reject_unknown_keys(
        document,
        {
            "version",
            "evidence_class",
            "target_id",
            "source_commit",
            "run_id",
            "destination",
            "artifacts",
            "deployment",
            "rollback",
            "effect_verifier",
            "authorization",
            "secret_values_present",
        },
        "evidence bundle",
        errors,
    )
    _require_value(document, "version", 1, errors)
    _require_value(document, "evidence_class", "wb0034_first_write", errors)
    _require_value(document, "target_id", "interserver-shared-hosting-staging", errors)
    _require_value(document, "secret_values_present", False, errors)

    source_commit = document.get("source_commit")
    if not isinstance(source_commit, str) or not HEX40_RE.fullmatch(source_commit):
        errors.append("evidence source_commit must be an exact 40-character commit SHA")
        source_commit_value: str | None = None
    else:
        source_commit_value = source_commit.lower()

    run_id = document.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        errors.append("evidence run_id must be a non-placeholder safe identifier")
        run_id_value: str | None = None
    else:
        run_id_value = run_id

    destination = document.get("destination")
    expected_destination = f"cybercore-canary-{run_id_value}/" if run_id_value else None
    if not isinstance(destination, str) or destination != expected_destination:
        errors.append(
            "evidence destination must be the direct-child canary directory bound to run_id"
        )
        destination_value: str | None = None
    else:
        destination_value = destination

    artifacts_value = document.get("artifacts")
    artifacts: set[str] = set()
    artifact_hashes: dict[str, str] = {}
    if not isinstance(artifacts_value, dict):
        errors.append("evidence requires mapping: artifacts")
    else:
        raw_artifacts = cast(dict[object, object], artifacts_value)
        if any(not isinstance(key, str) for key in raw_artifacts):
            errors.append("evidence artifacts contains non-string keys")
        else:
            artifact_map = cast(dict[str, object], raw_artifacts)
            artifacts = set(artifact_map)
            if artifacts != EXPECTED_ARTIFACTS:
                errors.append(
                    "evidence artifacts must be exactly index.html and cybercore-version.json"
                )
            for name, value in artifact_map.items():
                if not isinstance(value, str) or not HEX64_RE.fullmatch(value):
                    errors.append(f"evidence artifact hash for {name} must be sha256 hex")
                else:
                    artifact_hashes[name] = value.lower()

    deployment = _require_mapping(document, "deployment", errors)
    protocol_value: str | None = None
    target_capability_reference: str | None = None
    deploy_identity_scope_reference: str | None = None
    if deployment is not None:
        _reject_unknown_keys(
            deployment,
            {
                "protocol",
                "target_capability_reference",
                "deploy_identity_scope_reference",
                "production_write_excluded",
                "secret_values_recorded",
                "remote_write_performed",
            },
            "deployment evidence",
            errors,
        )
        protocol = deployment.get("protocol")
        if protocol not in {"SFTP", "SSH"}:
            errors.append("evidence deployment protocol must be SFTP or SSH")
        else:
            protocol_value = cast(str, protocol)
        capability_ref = deployment.get("target_capability_reference")
        if not _non_placeholder_reference(capability_ref):
            errors.append("evidence requires a non-placeholder target capability reference")
        else:
            target_capability_reference = cast(str, capability_ref)
        scope_ref = deployment.get("deploy_identity_scope_reference")
        if not _non_placeholder_reference(scope_ref):
            errors.append("evidence requires a non-placeholder deploy identity scope reference")
        else:
            deploy_identity_scope_reference = cast(str, scope_ref)
        _require_value(deployment, "production_write_excluded", True, errors)
        _require_value(deployment, "secret_values_recorded", False, errors)
        _require_value(deployment, "remote_write_performed", False, errors)

    rollback = _require_mapping(document, "rollback", errors)
    if rollback is not None:
        _reject_unknown_keys(
            rollback,
            {"method", "tested"},
            "rollback evidence",
            errors,
        )
        _require_value(rollback, "method", EXPECTED_ROLLBACK_METHOD, errors)
        _require_value(rollback, "tested", True, errors)

    effect_verifier = _require_mapping(document, "effect_verifier", errors)
    effect_verifier_reference: str | None = None
    if effect_verifier is not None:
        _reject_unknown_keys(
            effect_verifier,
            {"verified", "reference"},
            "effect verifier evidence",
            errors,
        )
        _require_value(effect_verifier, "verified", True, errors)
        verifier_ref = effect_verifier.get("reference")
        if not _non_placeholder_reference(verifier_ref):
            errors.append("evidence requires a non-placeholder effect verifier reference")
        else:
            effect_verifier_reference = cast(str, verifier_ref)

    authorization = _require_mapping(document, "authorization", errors)
    authorization_reference: str | None = None
    if authorization is not None:
        _reject_unknown_keys(
            authorization,
            {
                "status",
                "reference",
                "source_commit",
                "run_id",
                "destination",
                "artifacts",
                "protocol",
                "deploy_identity_scope_reference",
                "rollback_permitted",
            },
            "authorization evidence",
            errors,
        )
        _require_value(authorization, "status", "APPROVED", errors)
        auth_ref = authorization.get("reference")
        if not _non_placeholder_reference(auth_ref):
            errors.append("evidence requires a fresh non-placeholder authorization reference")
        else:
            authorization_reference = cast(str, auth_ref)
        if authorization.get("source_commit") != source_commit_value:
            errors.append("authorization source_commit must equal evidence source_commit")
        if authorization.get("run_id") != run_id_value:
            errors.append("authorization run_id must equal evidence run_id")
        if authorization.get("destination") != destination_value:
            errors.append("authorization destination must equal evidence destination")
        auth_artifacts = _string_set(
            authorization.get("artifacts"), errors, "authorization.artifacts"
        )
        if auth_artifacts != EXPECTED_ARTIFACTS:
            errors.append("authorization artifacts must equal the approved two-file artifact set")

        auth_protocol = authorization.get("protocol")
        if auth_protocol not in {"SFTP", "SSH"}:
            errors.append("authorization protocol must be SFTP or SSH")
        elif auth_protocol != protocol_value:
            errors.append("authorization protocol must equal deployment evidence protocol")

        auth_scope_ref = authorization.get("deploy_identity_scope_reference")
        if not _non_placeholder_reference(auth_scope_ref):
            errors.append(
                "authorization requires a non-placeholder deploy identity scope reference"
            )
        elif auth_scope_ref != deploy_identity_scope_reference:
            errors.append(
                "authorization deploy identity scope must equal deployment evidence scope"
            )

        _require_value(authorization, "rollback_permitted", True, errors)

    return FirstWriteEvidenceResult(
        not errors,
        tuple(errors),
        digest,
        source_commit_value,
        run_id_value,
        destination_value,
        tuple(sorted(artifacts)),
        protocol_value,
        target_capability_reference,
        deploy_identity_scope_reference,
        effect_verifier_reference,
        authorization_reference,
        tuple(sorted(artifact_hashes.items())),
    )
