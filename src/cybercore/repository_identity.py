from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit, urlunsplit


class RepositoryIdentityError(ValueError):
    """Raised when repository identity cannot satisfy the requested contract."""


@dataclass(frozen=True, slots=True)
class RepositoryIdentityDiagnostic:
    repository: str
    identity: str
    source: str
    origin: str | None
    diagnostic: str

    def as_dict(self) -> dict[str, str | None]:
        return asdict(self)


def _clean_repository_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/").lstrip("/").rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    if not normalized or normalized in {".", ".."}:
        raise RepositoryIdentityError("Git remote does not contain a repository path")
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise RepositoryIdentityError("Git remote contains an unsafe repository path")
    return "/".join(parts)


def normalize_git_remote(remote: str) -> str:
    """Return a stable transport-independent identity for a Git remote."""
    value = remote.strip()
    if not value:
        raise RepositoryIdentityError("Git remote is empty")

    scp_match = re.fullmatch(r"(?:[^@/:\s]+@)?([^:/\s]+):(.+)", value)
    if scp_match and "://" not in value:
        host = scp_match.group(1).lower()
        path = _clean_repository_path(scp_match.group(2))
        return f"git:{host}/{path}"

    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https", "ssh", "git"}:
        raise RepositoryIdentityError(
            f"Unsupported Git remote scheme: {parsed.scheme or 'local-path'}"
        )
    if not parsed.hostname:
        raise RepositoryIdentityError("Git remote does not contain a host")

    host = parsed.hostname.lower()
    port = parsed.port
    default_port = {"http": 80, "https": 443, "ssh": 22, "git": 9418}[parsed.scheme]
    authority = host if port in {None, default_port} else f"{host}:{port}"
    path = _clean_repository_path(parsed.path)
    return f"git:{authority}/{path}"


def redact_git_remote(remote: str) -> str:
    """Return an operator-safe remote URL without embedded credentials."""
    value = remote.strip()
    if not value:
        return value
    if "://" not in value:
        scp_match = re.fullmatch(r"(?:[^@/:\s]+@)?([^:/\s]+):(.+)", value)
        if scp_match:
            return f"{scp_match.group(1).lower()}:{scp_match.group(2)}"
        return value

    parsed = urlsplit(value)
    if parsed.hostname is None:
        return value
    host = parsed.hostname.lower()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    authority = host
    if parsed.port is not None:
        authority = f"{authority}:{parsed.port}"
    return urlunsplit((parsed.scheme, authority, parsed.path, parsed.query, parsed.fragment))


def _origin_url(repo: Path) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(repo), "remote", "get-url", "origin"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def resolve_repository_identity(
    repo: Path,
    *,
    strict: bool = False,
) -> RepositoryIdentityDiagnostic:
    """Resolve identity and expose whether a remote or path fallback was selected."""
    resolved = repo.expanduser().resolve()
    origin = _origin_url(resolved)
    safe_origin = redact_git_remote(origin) if origin is not None else None

    if origin is not None:
        try:
            identity = normalize_git_remote(origin)
        except RepositoryIdentityError as exc:
            diagnostic = f"Configured origin is unusable: {exc}"
        else:
            return RepositoryIdentityDiagnostic(
                repository=str(resolved),
                identity=identity,
                source="remote",
                origin=safe_origin,
                diagnostic="Normalized identity derived from origin.",
            )
    else:
        diagnostic = "No origin remote is configured."

    if strict:
        raise RepositoryIdentityError(f"Remote repository identity required: {diagnostic}")

    return RepositoryIdentityDiagnostic(
        repository=str(resolved),
        identity=f"path:{resolved}",
        source="path_fallback",
        origin=safe_origin,
        diagnostic=diagnostic,
    )


def repository_identity(repo: Path) -> str:
    """Resolve canonical identity while preserving the original string API."""
    return resolve_repository_identity(repo).identity


def render_repository_identity(diagnostic: RepositoryIdentityDiagnostic) -> str:
    origin = diagnostic.origin or "not configured"
    return "\n".join(
        [
            "REPOSITORY IDENTITY",
            f"Repository: {diagnostic.repository}",
            f"Identity: {diagnostic.identity}",
            f"Source: {diagnostic.source}",
            f"Origin: {origin}",
            f"Diagnostic: {diagnostic.diagnostic}",
        ]
    ) + "\n"
