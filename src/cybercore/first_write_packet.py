from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import stat
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
EXPECTED_VERSION_KEYS = {
    "repository",
    "commit",
    "branch",
    "built_at",
    "environment",
    "run_id",
}
MAX_CANARY_ARTIFACT_BYTES = 1024 * 1024


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


def _is_commit_sha(value: str) -> bool:
    return len(value) == 40 and all(character in "0123456789abcdef" for character in value)


def _git_rev_parse(repository_root: Path, ref: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--verify", ref],
            cwd=repository_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    commit = completed.stdout.strip().lower()
    if not _is_commit_sha(commit):
        return None
    return commit


def _git_head(repository_root: Path, errors: list[str]) -> str | None:
    head = _git_rev_parse(repository_root, "HEAD^{commit}")
    if head is None:
        errors.append("cannot resolve repository HEAD to an exact commit")
    return head


def _git_main_commit(repository_root: Path, errors: list[str]) -> str | None:
    # Prefer the fetched remote-tracking ref when available. A local-only
    # repository (including unit-test fixtures) may fall back to refs/heads/main.
    for ref in ("refs/remotes/origin/main^{commit}", "refs/heads/main^{commit}"):
        commit = _git_rev_parse(repository_root, ref)
        if commit is not None:
            return commit
    errors.append("cannot resolve trusted main commit from origin/main or local main")
    return None


def _open_artifact_directory_no_follow(artifact_dir: Path, errors: list[str]) -> int | None:
    if os.name != "posix" or not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        errors.append("secure artifact path validation requires POSIX O_DIRECTORY and O_NOFOLLOW")
        return None

    absolute = Path(os.path.abspath(os.fspath(artifact_dir)))
    if not absolute.is_absolute() or absolute.anchor != "/":
        errors.append("deployment artifact directory must resolve to an absolute POSIX path")
        return None

    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    current_fd: int | None = None
    try:
        current_fd = os.open("/", directory_flags)
        for component in absolute.parts[1:]:
            next_fd = os.open(component, directory_flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
    except OSError as exc:
        if current_fd is not None:
            os.close(current_fd)
        errors.append(
            "deployment artifact directory contains a symlink, missing path, or invalid "
            f"directory component: {exc}"
        )
        return None
    return current_fd


def _read_artifact_no_follow(
    directory_fd: int,
    name: str,
    errors: list[str],
) -> tuple[str, bytes] | None:
    file_fd: int | None = None
    try:
        file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
        metadata = os.fstat(file_fd)
        if not stat.S_ISREG(metadata.st_mode):
            errors.append(f"deployment artifact is not a regular file: {name}")
            return None
        if metadata.st_size > MAX_CANARY_ARTIFACT_BYTES:
            errors.append(f"deployment artifact exceeds size limit: {name}")
            return None

        digest = hashlib.sha256()
        data = bytearray()
        while True:
            chunk = os.read(file_fd, 64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            data.extend(chunk)
            if len(data) > MAX_CANARY_ARTIFACT_BYTES:
                errors.append(f"deployment artifact exceeds size limit while reading: {name}")
                return None
        return digest.hexdigest(), bytes(data)
    except OSError as exc:
        errors.append(f"cannot open deployment artifact without following links {name}: {exc}")
        return None
    finally:
        if file_fd is not None:
            os.close(file_fd)


def _local_artifacts(
    artifact_dir: Path,
    errors: list[str],
) -> tuple[dict[str, str], bytes | None]:
    directory_fd = _open_artifact_directory_no_follow(artifact_dir, errors)
    if directory_fd is None:
        return {}, None

    hashes: dict[str, str] = {}
    version_bytes: bytes | None = None
    try:
        try:
            entries = set(os.listdir(directory_fd))
        except OSError as exc:
            errors.append(f"cannot list deployment artifact directory: {exc}")
            return {}, None

        missing = sorted(EXPECTED_ARTIFACTS - entries)
        unexpected = sorted(entries - EXPECTED_ARTIFACTS)
        if missing:
            errors.append(f"deployment artifact directory is missing: {', '.join(missing)}")
        if unexpected:
            errors.append(
                "deployment artifact directory contains unexpected entries: "
                + ", ".join(unexpected)
            )

        for name in sorted(EXPECTED_ARTIFACTS):
            result = _read_artifact_no_follow(directory_fd, name, errors)
            if result is None:
                continue
            digest, data = result
            hashes[name] = digest
            if name == "cybercore-version.json":
                version_bytes = data
    finally:
        os.close(directory_fd)

    return hashes, version_bytes


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _validate_version_marker(
    raw_bytes: bytes,
    *,
    expected_commit: str,
    expected_run_id: str,
    errors: list[str],
) -> None:
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        errors.append("cybercore-version.json must be UTF-8")
        return

    try:
        loaded = json.loads(text, object_pairs_hook=_unique_json_object)
    except (json.JSONDecodeError, ValueError) as exc:
        errors.append(f"cybercore-version.json is invalid or ambiguous JSON: {exc}")
        return

    if not isinstance(loaded, dict):
        errors.append("cybercore-version.json must contain one JSON object")
        return
    marker = cast(dict[object, object], loaded)
    if any(not isinstance(key, str) for key in marker):
        errors.append("cybercore-version.json contains non-string keys")
        return
    document = cast(dict[str, object], marker)

    actual_keys = set(document)
    if actual_keys != EXPECTED_VERSION_KEYS:
        missing = sorted(EXPECTED_VERSION_KEYS - actual_keys)
        unexpected = sorted(actual_keys - EXPECTED_VERSION_KEYS)
        if missing:
            errors.append(f"cybercore-version.json is missing keys: {', '.join(missing)}")
        if unexpected:
            errors.append(f"cybercore-version.json contains unexpected keys: {', '.join(unexpected)}")

    expected_values = {
        "repository": "cyberDJs/CyberCore",
        "commit": expected_commit,
        "branch": "main",
        "environment": "interserver-shared-hosting-staging",
        "run_id": expected_run_id,
    }
    for key, expected in expected_values.items():
        actual = document.get(key)
        if actual != expected:
            errors.append(f"cybercore-version.json {key} must equal {expected!r}; got {actual!r}")

    built_at = document.get("built_at")
    if not isinstance(built_at, str) or not built_at.strip():
        errors.append("cybercore-version.json built_at must be a UTC timestamp string")
        return
    try:
        timestamp = datetime.fromisoformat(built_at.replace("Z", "+00:00"))
    except ValueError:
        errors.append("cybercore-version.json built_at must be a valid ISO-8601 timestamp")
        return
    if timestamp.tzinfo is None or timestamp.utcoffset() != timedelta(0):
        errors.append("cybercore-version.json built_at must use UTC")


def validate_first_write_packet(
    manifest_path: Path,
    readiness_path: Path,
    repository_root: Path,
    artifact_dir: Path,
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
    main_commit = _git_main_commit(repository_root, errors)

    if manifest is None or readiness is None or head is None or main_commit is None:
        return FirstWritePacketResult(False, tuple(errors))

    if head != main_commit:
        errors.append("repository HEAD must equal the trusted main commit before final preflight")

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
        errors.append(
            "readiness source_commit_reference must equal the checked-out repository HEAD"
        )
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

    evidence_hashes = dict(evidence.artifact_hashes)
    local_hashes, version_bytes = _local_artifacts(artifact_dir, errors)
    for name in sorted(EXPECTED_ARTIFACTS):
        expected_digest = evidence_hashes.get(name)
        actual_digest = local_hashes.get(name)
        if expected_digest is None:
            errors.append(f"evidence is missing deployment artifact digest: {name}")
        elif actual_digest is not None and actual_digest != expected_digest:
            errors.append(f"deployment artifact digest mismatch: {name}")

    if version_bytes is not None:
        if evidence.run_id is None:
            errors.append("evidence run_id is unavailable for version-marker validation")
        else:
            _validate_version_marker(
                version_bytes,
                expected_commit=head,
                expected_run_id=evidence.run_id,
                errors=errors,
            )

    return FirstWritePacketResult(not errors, tuple(errors))
