from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re

from cybercore.repository_identity import RepositoryIdentityDiagnostic, resolve_repository_identity


class RepositoryIdentityPolicyError(ValueError):
    """Raised when canonical repository identity policy cannot be evaluated."""


@dataclass(frozen=True, slots=True)
class RepositoryIdentityPolicyResult:
    status: str
    compliant: bool
    expected_identity: str
    actual_identity: str
    source: str
    origin: str | None
    message: str

    def as_dict(self) -> dict[str, str | bool | None]:
        return asdict(self)


def _configured_repository_identity(repo: Path) -> str | None:
    project = repo.expanduser().resolve() / ".cybercore" / "project.yaml"
    try:
        content = project.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None

    in_identity = False
    for line in content.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith((" ", "\t")):
            in_identity = line.strip() == "identity:"
            continue
        if not in_identity:
            continue
        match = re.fullmatch(r"\s{2}repository:\s*(.+?)\s*", line)
        if match:
            value = match.group(1).strip().strip("'\"")
            if not value.startswith("git:"):
                raise RepositoryIdentityPolicyError(
                    "Canonical repository identity must use the normalized git: form"
                )
            return value
    return None


def expected_repository_identity(repo: Path) -> str:
    """Read the canonical repository identity from .cybercore/project.yaml."""
    resolved = repo.expanduser().resolve()
    project = resolved / ".cybercore" / "project.yaml"
    expected = _configured_repository_identity(resolved)
    if expected is None:
        if not project.exists():
            raise RepositoryIdentityPolicyError(
                f"Canonical project state is missing: {project}"
            )
        raise RepositoryIdentityPolicyError(
            "Canonical repository identity is not configured at identity.repository"
        )
    return expected


def evaluate_repository_identity_policy(
    repo: Path,
    *,
    advisory: bool = False,
) -> RepositoryIdentityPolicyResult:
    """Compare resolved repository identity with the canonical project identity."""
    resolved = repo.expanduser().resolve()
    expected = expected_repository_identity(resolved)
    diagnostic: RepositoryIdentityDiagnostic = resolve_repository_identity(resolved)

    if diagnostic.source != "remote":
        message = "Stable remote identity is required; path fallback is not policy-compliant."
        compliant = False
    elif diagnostic.identity != expected:
        message = (
            "Repository identity mismatch: this clone is connected to an unexpected "
            "repository or fork."
        )
        compliant = False
    else:
        message = "Repository identity matches canonical project policy."
        compliant = True

    status = "verified" if compliant else ("warning" if advisory else "failed")
    return RepositoryIdentityPolicyResult(
        status=status,
        compliant=compliant,
        expected_identity=expected,
        actual_identity=diagnostic.identity,
        source=diagnostic.source,
        origin=diagnostic.origin,
        message=message,
    )


def enforce_configured_repository_identity_policy(
    repo: Path,
    *,
    operation: str,
) -> RepositoryIdentityPolicyResult | None:
    """Enforce identity when a canonical policy is configured.

    Repositories without identity.repository retain backward-compatible behavior.
    Once configured, identity-sensitive operations fail closed on fallback or mismatch.
    """
    resolved = repo.expanduser().resolve()
    if _configured_repository_identity(resolved) is None:
        return None
    result = evaluate_repository_identity_policy(resolved)
    if not result.compliant:
        raise RepositoryIdentityPolicyError(
            f"{operation} rejected by repository identity policy: {result.message} "
            f"Expected {result.expected_identity}, got {result.actual_identity}."
        )
    return result


def render_repository_identity_policy(result: RepositoryIdentityPolicyResult) -> str:
    origin = result.origin or "not configured"
    return "\n".join(
        [
            "REPOSITORY IDENTITY POLICY",
            f"Status: {result.status}",
            f"Compliant: {'yes' if result.compliant else 'no'}",
            f"Expected: {result.expected_identity}",
            f"Actual: {result.actual_identity}",
            f"Source: {result.source}",
            f"Origin: {origin}",
            f"Message: {result.message}",
        ]
    ) + "\n"
