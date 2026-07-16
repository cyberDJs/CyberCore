from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any


class WorkBlockError(RuntimeError):
    """Raised when a Work Block is invalid or unsafe."""


@dataclass(frozen=True, slots=True)
class WorkBlockManifest:
    schema: str
    identifier: str
    title: str
    target_branch: str | None
    risk: str

    @classmethod
    def load(cls, path: Path) -> "WorkBlockManifest":
        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise WorkBlockError(f"missing manifest: {path}") from exc
        except json.JSONDecodeError as exc:
            raise WorkBlockError(f"invalid JSON manifest: {exc}") from exc

        schema = data.get("schema")
        identifier = data.get("id")
        title = data.get("title")
        risk = data.get("risk", "unknown")
        target_branch = data.get("target_branch")

        if schema != "cxp/v1":
            raise WorkBlockError(f"unsupported schema: {schema!r}")
        if not isinstance(identifier, str) or not identifier.startswith("WB-"):
            raise WorkBlockError("manifest id must start with WB-")
        if not isinstance(title, str) or not title.strip():
            raise WorkBlockError("manifest title is required")
        if target_branch is not None and not isinstance(target_branch, str):
            raise WorkBlockError("target_branch must be a string or null")
        if not isinstance(risk, str):
            raise WorkBlockError("risk must be a string")

        return cls(
            schema=schema,
            identifier=identifier,
            title=title,
            target_branch=target_branch,
            risk=risk,
        )


@dataclass(frozen=True, slots=True)
class VerificationReport:
    path: Path
    manifest: WorkBlockManifest
    verified_files: tuple[str, ...]


def _safe_relative_path(raw: str) -> PurePosixPath:
    candidate = PurePosixPath(raw)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise WorkBlockError(f"unsafe checksum path: {raw}")
    if not candidate.parts:
        raise WorkBlockError("empty checksum path")
    return candidate


def verify_workblock(path: Path) -> VerificationReport:
    package = path.expanduser().resolve()
    if not package.is_dir():
        raise WorkBlockError(f"Work Block directory not found: {package}")

    required = (
        "manifest.json",
        "checksums.sha256",
        "README.md",
        "actions/verify.sh",
        "actions/apply.sh",
    )

    for relative in required:
        target = package / relative
        if not target.is_file():
            raise WorkBlockError(f"missing required file: {relative}")
        if target.is_symlink():
            raise WorkBlockError(f"symlinks are not allowed: {relative}")

    for candidate in package.rglob("*"):
        if candidate.is_symlink():
            raise WorkBlockError(
                f"symlinks are not allowed: {candidate.relative_to(package)}"
            )

    manifest = WorkBlockManifest.load(package / "manifest.json")
    verified: list[str] = []

    checksum_lines = (package / "checksums.sha256").read_text(
        encoding="utf-8"
    ).splitlines()

    if not checksum_lines:
        raise WorkBlockError("checksums.sha256 is empty")

    for line_number, line in enumerate(checksum_lines, start=1):
        if not line.strip():
            continue

        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise WorkBlockError(
                f"invalid checksum line {line_number}: {line!r}"
            )

        expected, raw_path = parts
        raw_path = raw_path.lstrip("* ")
        relative = _safe_relative_path(raw_path)
        target = package.joinpath(*relative.parts).resolve()

        try:
            target.relative_to(package)
        except ValueError as exc:
            raise WorkBlockError(f"path escapes package: {raw_path}") from exc

        if not target.is_file():
            raise WorkBlockError(f"checksummed file missing: {raw_path}")

        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != expected.lower():
            raise WorkBlockError(f"checksum mismatch: {raw_path}")

        verified.append(relative.as_posix())

    required_checksummed = {
        "manifest.json",
        "README.md",
        "actions/verify.sh",
        "actions/apply.sh",
    }
    missing = required_checksummed.difference(verified)
    if missing:
        raise WorkBlockError(
            "required files absent from checksums: " + ", ".join(sorted(missing))
        )

    return VerificationReport(
        path=package,
        manifest=manifest,
        verified_files=tuple(verified),
    )
