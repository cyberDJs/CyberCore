from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import cast

import yaml

from cybercore.first_write import validate_first_write_readiness
from cybercore.first_write_evidence import (
    resolve_evidence_bundle_path,
    validate_first_write_evidence,
)
from cybercore.first_write_manifest import validate_first_write_manifest


EXPECTED_ARTIFACTS = {"index.html", "cybercore-version.json"}


@dataclass(frozen=True)
class FirstWritePacketResult:
    ready: bool
    errors: tuple[str, ...]

    def as_text(self) -> str:
        lines = [f"wb0034 final preflight packet: {'READY' if self.ready else 'BLOCKED'}"]
        if self.errors:
            lines.append("errors:")
            lines.extend(f"- {error}" for error in self.errors)
        return "\n".join(lines)


def _load_mapping(path: Path, label: str, errors: list[str]) -> dict[str, object] | None:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, UnicodeDecodeError, yaml.YAMLError) as exc:
        errors.append(f"cannot load {label}: {exc}")
        return None
    if not isinstance(loaded, dict):
        errors.append(f"{label} must be a YAML mapping")
        return None
    raw = cast(dict[object, object], loaded)
    if any(not isinstance(key, str) for key in raw):
        errors.append(f"{label} contains non-string top-level keys")
        return None
    return cast(dict[str, object], raw)


def _git_head(repository_root: Path, errors: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        errors.append(f"cannot resolve repository HEAD: {exc}")
        return None
    if completed.returncode != 0:
        errors.append("cannot resolve repository HEAD")
        return None
    head = completed.stdout.strip().lower()
    if len(head) != 40 or not all(character in "0123456789abcdef" for character in head):
        errors.append("repository HEAD is not an exact 40-character commit SHA")
        return None
    return head


def validate_first_write_packet(
    manifest_path: Path,
    readiness_path: Path,
    repository_root: Path,
) -> FirstWritePacketResult:
    errors: list[str] = []

    manifest_result = validate_first_write_manifest(manifest_path, final_preflight=True)
    if not manifest_result.ok:
        errors.extend(f"manifest: {error}" for error in manifest_result.errors)

    readiness_result = validate_first_write_readiness(readiness_path)
    if not readiness_result.schema_ok:
        errors.extend(f"readiness schema: {error}" for error in readiness_result.errors)
    if readiness_result.schema_ok and not readiness_result.ready:
        errors.extend(f"readiness: {blocker}" for blocker in readiness_result.blockers)

    manifest = _load_mapping(manifest_path, "manifest", errors)
    readiness = _load_mapping(readiness_path, "readiness", errors)
    head = _git_head(repository_root, errors)

    if manifest is None or readiness is None or head is None:
        return FirstWritePacketResult(False, tuple(errors))

    source_readiness_value = readiness.get("source_artifact_readiness")
    authorization_value = readiness.get("operator_authorization")
    if not isinstance(source_readiness_value, dict) or not isinstance(authorization_value, dict):
        return FirstWritePacketResult(False, tuple(errors))

    source_readiness = cast(dict[str, object], source_readiness_value)
    authorization = cast(dict[str, object], authorization_value)

    manifest_commit = manifest.get("source_commit")
    readiness_commit = source_readiness.get("source_commit_reference")
    if manifest_commit != head:
        errors.append("manifest source_commit must equal the checked-out repository HEAD")
    if readiness_commit != head:
        errors.append("readiness source_commit_reference must equal the checked-out repository HEAD")
    if manifest_commit != readiness_commit:
        errors.append("manifest and readiness must name the same source commit")

    manifest_artifacts_value = manifest.get("planned_artifacts")
    if not isinstance(manifest_artifacts_value, list) or not all(
        isinstance(item, str) for item in manifest_artifacts_value
    ):
        errors.append("manifest planned_artifacts must be a string list")
        manifest_artifacts: set[str] = set()
    else:
        manifest_artifacts = set(cast(list[str], manifest_artifacts_value))
    if manifest_artifacts != EXPECTED_ARTIFACTS:
        errors.append("final packet artifact set must be exactly the approved two files")

    manifest_auth = manifest.get("operator_authorization_reference")
    readiness_auth = authorization.get("authorization_reference")
    if manifest_auth != readiness_auth:
        errors.append("manifest and readiness must use the same operator authorization reference")

    evidence_reference = readiness.get("evidence_bundle_reference")
    evidence_sha = readiness.get("evidence_bundle_sha256")
    evidence_path = resolve_evidence_bundle_path(readiness_path, evidence_reference)
    if evidence_path is None:
        errors.append("final packet evidence bundle reference is invalid")
        return FirstWritePacketResult(False, tuple(errors))
    if not isinstance(evidence_sha, str):
        errors.append("final packet evidence bundle sha256 is missing")
        return FirstWritePacketResult(False, tuple(errors))

    evidence = validate_first_write_evidence(evidence_path, expected_sha256=evidence_sha)
    if not evidence.ok:
        errors.extend(f"evidence: {error}" for error in evidence.errors)
        return FirstWritePacketResult(False, tuple(errors))

    if evidence.source_commit != head:
        errors.append("evidence source_commit must equal the checked-out repository HEAD")
    if evidence.source_commit != manifest_commit:
        errors.append("evidence and manifest source commits must match")
    if evidence.run_id != manifest.get("run_id"):
        errors.append("evidence and manifest run_id values must match")
    if evidence.destination != manifest.get("planned_remote_destination"):
        errors.append("evidence and manifest destination values must match")
    if set(evidence.artifacts) != manifest_artifacts:
        errors.append("evidence and manifest artifact sets must match")
    if evidence.authorization_reference != manifest_auth:
        errors.append("evidence and manifest authorization references must match")

    return FirstWritePacketResult(not errors, tuple(errors))
