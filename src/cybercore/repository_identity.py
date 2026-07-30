from __future__ import annotations

from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit


class RepositoryIdentityError(ValueError):
    """Raised when a configured Git remote cannot be normalized safely."""


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


def repository_identity(repo: Path) -> str:
    """Resolve canonical remote identity, falling back deterministically to path."""
    resolved = repo.expanduser().resolve()
    remote = _origin_url(resolved)
    if remote is not None:
        try:
            return normalize_git_remote(remote)
        except RepositoryIdentityError:
            pass
    return f"path:{resolved}"
