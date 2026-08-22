from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
from typing import cast

import yaml

from cybercore.first_write import validate_first_write_readiness
from cybercore.first_write_evidence import (
    FirstWriteEvidenceResult,
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
MAX_PACKET_DOCUMENT_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class ValidatedFirstWriteArtifact:
    name: str
    sha256: str
    content: bytes


@dataclass(frozen=True)
class FirstWriteUploadInput:
    source_commit: str
    run_id: str
    destination: str
    protocol: str
    deploy_identity_scope_reference: str
    authorization_reference: str
    artifacts: tuple[ValidatedFirstWriteArtifact, ...]

    def artifact_bytes(self, name: str) -> bytes:
        for artifact in self.artifacts:
            if artifact.name == name:
                return artifact.content
        raise KeyError(name)


@dataclass(frozen=True)
class FirstWritePacketResult:
    ready: bool
    errors: tuple[str, ...]
    upload_input: FirstWriteUploadInput | None = None

    def as_text(self) -> str:
        lines = [f"wb0034 final preflight packet: {'READY' if self.ready else 'BLOCKED'}"]
        if self.errors:
            lines.append("errors:")
            lines.extend(f"- {error}" for error in self.errors)
        return "\n".join(lines)


def _read_document_once(path: Path, label: str, errors: list[str]) -> bytes | None:
    try:
        with path.open("rb") as handle:
            data = handle.read(MAX_PACKET_DOCUMENT_BYTES + 1)
    except OSError as exc:
        errors.append(f"cannot read {label}: {exc}")
        return None
    if len(data) > MAX_PACKET_DOCUMENT_BYTES:
        errors.append(f"{label} exceeds packet document size limit")
        return None
    return data


def _decode_document(raw_bytes: bytes, label: str, errors: list[str]) -> str | None:
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        errors.append(f"{label} must be UTF-8")
        return None


def _parse_mapping_text(text: str, label: str, errors: list[str]) -> dict[str, object] | None:
    try:
        loaded = yaml.safe_load(text)
    except (RecursionError, yaml.YAMLError) as exc:
        errors.append(f"cannot parse {label}: {exc}")
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


def _check_artifact_entries(entries: set[str], label: str, errors: list[str]) -> None:
    missing = sorted(EXPECTED_ARTIFACTS - entries)
    unexpected = sorted(entries - EXPECTED_ARTIFACTS)
    if missing:
        errors.append(f"deployment artifact directory {label} is missing: {', '.join(missing)}")
    if unexpected:
        errors.append(
            f"deployment artifact directory {label} contains unexpected entries: "
            + ", ".join(unexpected)
        )


def _local_artifacts(
    artifact_dir: Path,
    errors: list[str],
) -> dict[str, tuple[str, bytes]]:
    directory_fd = _open_artifact_directory_no_follow(artifact_dir, errors)
    if directory_fd is None:
        return {}

    artifacts: dict[str, tuple[str, bytes]] = {}
    try:
        try:
            before_entries = set(os.listdir(directory_fd))
        except OSError as exc:
            errors.append(f"cannot list deployment artifact directory before reads: {exc}")
            return {}
        _check_artifact_entries(before_entries, "before reads", errors)

        for name in sorted(EXPECTED_ARTIFACTS):
            result = _read_artifact_no_follow(directory_fd, name, errors)
            if result is not None:
                artifacts[name] = result

        try:
            after_entries = set(os.listdir(directory_fd))
        except OSError as exc:
            errors.append(f"cannot list deployment artifact directory after reads: {exc}")
            return artifacts
        _check_artifact_entries(after_entries, "after reads", errors)
        if after_entries != before_entries:
            errors.append("deployment artifact directory changed during validation")
    finally:
        os.close(directory_fd)

    return artifacts


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
            errors.append(
                f"cybercore-version.json contains unexpected keys: {', '.join(unexpected)}"
            )

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


def _snapshot_evidence_path(
    snapshot_readiness: Path,
    evidence_reference: object,
    snapshot_root: Path,
    errors: list[str],
) -> Path | None:
    if not isinstance(evidence_reference, str) or not evidence_reference.strip():
        errors.append("final packet evidence bundle reference is invalid")
        return None
    candidate = (snapshot_readiness.parent / evidence_reference).resolve()
    try:
        candidate.relative_to(snapshot_root.resolve())
    except ValueError:
        errors.append("final packet evidence snapshot escapes the private packet snapshot")
        return None
    if candidate.suffix not in {".yaml", ".yml"}:
        errors.append("final packet evidence snapshot must be YAML")
        return None
    return candidate


def _validate_private_packet_snapshot(
    manifest_bytes: bytes,
    readiness_bytes: bytes,
    evidence_bytes: bytes,
    evidence_reference: object,
    evidence_sha: object,
    errors: list[str],
) -> FirstWriteEvidenceResult | None:
    with tempfile.TemporaryDirectory(prefix="cybercore-wb0034-") as temporary:
        snapshot_root = Path(temporary) / "deploy"
        manifest_snapshot = snapshot_root / "manifests" / "manifest.yaml"
        readiness_snapshot = snapshot_root / "readiness" / "readiness.yaml"
        manifest_snapshot.parent.mkdir(parents=True)
        readiness_snapshot.parent.mkdir(parents=True)

        evidence_snapshot = _snapshot_evidence_path(
            readiness_snapshot,
            evidence_reference,
            snapshot_root,
            errors,
        )
        if evidence_snapshot is None:
            return None
        evidence_snapshot.parent.mkdir(parents=True, exist_ok=True)

        manifest_snapshot.write_bytes(manifest_bytes)
        readiness_snapshot.write_bytes(readiness_bytes)
        evidence_snapshot.write_bytes(evidence_bytes)
        for snapshot in (manifest_snapshot, readiness_snapshot, evidence_snapshot):
            snapshot.chmod(0o400)

        manifest_result = validate_first_write_manifest(manifest_snapshot, final_preflight=True)
        if not manifest_result.ok:
            errors.extend(f"manifest: {error}" for error in manifest_result.errors)

        readiness_result = validate_first_write_readiness(readiness_snapshot)
        if not readiness_result.schema_ok:
            errors.extend(f"readiness schema: {error}" for error in readiness_result.errors)
        if readiness_result.schema_ok and not readiness_result.ready:
            errors.extend(f"readiness: {blocker}" for blocker in readiness_result.blockers)

        expected_sha = evidence_sha if isinstance(evidence_sha, str) else None
        if expected_sha is None:
            errors.append("final packet evidence bundle sha256 is missing")
        evidence = validate_first_write_evidence(
            evidence_snapshot,
            expected_sha256=expected_sha,
        )
        if not evidence.ok:
            errors.extend(f"evidence: {error}" for error in evidence.errors)

        snapshots = (
            (manifest_snapshot, manifest_bytes, "manifest"),
            (readiness_snapshot, readiness_bytes, "readiness"),
            (evidence_snapshot, evidence_bytes, "evidence bundle"),
        )
        for snapshot, expected, label in snapshots:
            try:
                observed = snapshot.read_bytes()
            except OSError as exc:
                errors.append(f"cannot verify private {label} snapshot integrity: {exc}")
                continue
            if observed != expected:
                errors.append(f"private {label} snapshot changed during validation")

        return evidence


def _capture_packet_documents(
    manifest_path: Path,
    readiness_path: Path,
    errors: list[str],
) -> tuple[dict[str, object], dict[str, object], FirstWriteEvidenceResult | None] | None:
    manifest_bytes = _read_document_once(manifest_path, "manifest", errors)
    readiness_bytes = _read_document_once(readiness_path, "readiness", errors)
    if manifest_bytes is None or readiness_bytes is None:
        return None

    manifest_text = _decode_document(manifest_bytes, "manifest", errors)
    readiness_text = _decode_document(readiness_bytes, "readiness", errors)
    if manifest_text is None or readiness_text is None:
        return None

    manifest = _parse_mapping_text(manifest_text, "manifest", errors)
    readiness = _parse_mapping_text(readiness_text, "readiness", errors)
    if manifest is None or readiness is None:
        return None

    evidence_reference = readiness.get("evidence_bundle_reference")
    evidence_sha = readiness.get("evidence_bundle_sha256")
    evidence_path = resolve_evidence_bundle_path(readiness_path, evidence_reference)
    if evidence_path is None:
        errors.append("final packet evidence bundle reference is invalid")
        return None

    evidence_bytes = _read_document_once(evidence_path, "evidence bundle", errors)
    if evidence_bytes is None:
        return None

    evidence = _validate_private_packet_snapshot(
        manifest_bytes,
        readiness_bytes,
        evidence_bytes,
        evidence_reference,
        evidence_sha,
        errors,
    )
    return manifest, readiness, evidence


def _build_upload_input(
    evidence: FirstWriteEvidenceResult,
    artifacts: dict[str, tuple[str, bytes]],
    errors: list[str],
) -> FirstWriteUploadInput | None:
    required = {
        "source_commit": evidence.source_commit,
        "run_id": evidence.run_id,
        "destination": evidence.destination,
        "protocol": evidence.protocol,
        "deploy_identity_scope_reference": evidence.deploy_identity_scope_reference,
        "authorization_reference": evidence.authorization_reference,
    }
    missing = sorted(key for key, value in required.items() if not isinstance(value, str))
    if missing:
        errors.append(f"validated upload input is missing fields: {', '.join(missing)}")
        return None
    if set(artifacts) != EXPECTED_ARTIFACTS:
        errors.append("validated upload input does not contain the exact two approved artifacts")
        return None

    sealed_artifacts = tuple(
        ValidatedFirstWriteArtifact(
            name=name, sha256=artifacts[name][0], content=artifacts[name][1]
        )
        for name in sorted(EXPECTED_ARTIFACTS)
    )
    return FirstWriteUploadInput(
        source_commit=cast(str, required["source_commit"]),
        run_id=cast(str, required["run_id"]),
        destination=cast(str, required["destination"]),
        protocol=cast(str, required["protocol"]),
        deploy_identity_scope_reference=cast(str, required["deploy_identity_scope_reference"]),
        authorization_reference=cast(str, required["authorization_reference"]),
        artifacts=sealed_artifacts,
    )


def validate_first_write_packet(
    manifest_path: Path,
    readiness_path: Path,
    repository_root: Path,
    artifact_dir: Path,
) -> FirstWritePacketResult:
    errors: list[str] = []

    captured = _capture_packet_documents(manifest_path, readiness_path, errors)
    if captured is None:
        return FirstWritePacketResult(False, tuple(errors))
    manifest, readiness, evidence = captured

    head = _git_head(repository_root, errors)
    main_commit = _git_main_commit(repository_root, errors)
    if head is None or main_commit is None:
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

    if evidence is None or not evidence.ok:
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
    local_artifacts = _local_artifacts(artifact_dir, errors)
    for name in sorted(EXPECTED_ARTIFACTS):
        expected_digest = evidence_hashes.get(name)
        actual = local_artifacts.get(name)
        actual_digest = actual[0] if actual is not None else None
        if expected_digest is None:
            errors.append(f"evidence is missing deployment artifact digest: {name}")
        elif actual_digest is not None and actual_digest != expected_digest:
            errors.append(f"deployment artifact digest mismatch: {name}")

    version_artifact = local_artifacts.get("cybercore-version.json")
    if version_artifact is not None:
        if evidence.run_id is None:
            errors.append("evidence run_id is unavailable for version-marker validation")
        else:
            _validate_version_marker(
                version_artifact[1],
                expected_commit=head,
                expected_run_id=evidence.run_id,
                errors=errors,
            )

    upload_input: FirstWriteUploadInput | None = None
    if not errors:
        upload_input = _build_upload_input(evidence, local_artifacts, errors)
    ready = not errors and upload_input is not None
    return FirstWritePacketResult(ready, tuple(errors), upload_input)
