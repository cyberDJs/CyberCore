from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from pathlib import Path
import subprocess

import yaml

from cybercore.operation_context_disclosure import DisclosureMode, sanitize_disclosure_text
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


_WB0034_TRUSTED_MAIN_OPERATION = "WB-0034 trusted-main resolution"
_REQUIRED_OPERATION_IDENTITIES = {
    _WB0034_TRUSTED_MAIN_OPERATION: "git:github.com/cyberDJs/CyberCore",
}
_WB0034_CANONICAL_HTTPS_ORIGINS = {
    "https://github.com/cyberDJs/CyberCore",
    "https://github.com/cyberDJs/CyberCore.git",
}
_WB0034_REPOSITORY_ENV_KEYS = (
    "GIT_DIR",
    "GIT_COMMON_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_NAMESPACE",
    "GIT_CONFIG",
)
_WB0034_TRANSPORT_ENV_KEYS = (
    "GIT_SSH",
    "GIT_SSH_COMMAND",
    "GIT_PROXY_COMMAND",
    "GIT_EXEC_PATH",
    "GIT_SSL_NO_VERIFY",
    "GIT_SSL_CAINFO",
    "GIT_SSL_CAPATH",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)


class UniqueProjectKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_project_mapping(
    loader: UniqueProjectKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
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
                "found a duplicate mapping key",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueProjectKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_project_mapping,
)


def _configured_repository_identity(repo: Path) -> str | None:
    project = repo.expanduser().resolve() / ".cybercore" / "project.yaml"
    try:
        content = project.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except UnicodeError as exc:
        raise RepositoryIdentityPolicyError(
            "Canonical project state is not valid UTF-8 text"
        ) from exc
    except OSError as exc:
        raise RepositoryIdentityPolicyError(
            "Canonical project state cannot be read safely"
        ) from exc

    try:
        document = yaml.load(content, Loader=UniqueProjectKeyLoader)
    except (yaml.YAMLError, RecursionError) as exc:
        raise RepositoryIdentityPolicyError(
            "Canonical project state is invalid YAML or contains duplicate mapping keys"
        ) from exc

    if not isinstance(document, dict):
        raise RepositoryIdentityPolicyError("Canonical project state must be a YAML mapping")

    identity = document.get("identity")
    if identity is None:
        return None
    if not isinstance(identity, dict):
        raise RepositoryIdentityPolicyError("Canonical project identity must be a YAML mapping")

    repository = identity.get("repository")
    if repository is None:
        return None
    if not isinstance(repository, str):
        raise RepositoryIdentityPolicyError(
            "Canonical repository identity must be a YAML string scalar"
        )
    if not repository.startswith("git:"):
        raise RepositoryIdentityPolicyError(
            "Canonical repository identity must use the normalized git: form"
        )
    return repository


def _run_git_policy_query(repo: Path, *args: str) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RepositoryIdentityPolicyError(
            "WB-0034 cannot inspect Git transport configuration safely"
        ) from exc
    return completed.returncode, completed.stdout.strip()


def _optional_git_config_value(repo: Path, *args: str) -> str | None:
    returncode, output = _run_git_policy_query(repo, "config", *args)
    if returncode == 1:
        return None
    if returncode != 0:
        raise RepositoryIdentityPolicyError(
            "WB-0034 cannot evaluate Git transport configuration safely"
        )
    # A configured empty value is materially different from an absent value.
    # In particular Git parses an empty boolean as false, so preserve it here.
    return output


def _enforce_wb0034_repository_selection_environment() -> None:
    """Reject inherited variables that can redirect repository or config queries."""

    inherited_overrides = sorted(key for key in _WB0034_REPOSITORY_ENV_KEYS if key in os.environ)
    if inherited_overrides:
        raise RepositoryIdentityPolicyError(
            "WB-0034 trusted-main resolution rejects inherited Git repository-selection "
            "or config-selection overrides: " + ", ".join(inherited_overrides)
        )


def _enforce_wb0034_git_transport_policy(repo: Path) -> None:
    """Fail closed on Git transport overrides before trusted-main refresh.

    WB-0034 deliberately narrows the fetch transport to the canonical GitHub
    HTTPS origin. SSH origins and effective Git/environment overrides that can
    replace, proxy, rewrite, or weaken that transport are rejected before the
    existing `git fetch origin` trust refresh is allowed to run.
    """

    returncode, origin = _run_git_policy_query(repo, "remote", "get-url", "origin")
    if returncode != 0 or origin not in _WB0034_CANONICAL_HTTPS_ORIGINS:
        raise RepositoryIdentityPolicyError(
            "WB-0034 trusted-main refresh requires the exact canonical GitHub HTTPS origin"
        )

    inherited_overrides = sorted(
        key for key in _WB0034_TRANSPORT_ENV_KEYS if os.environ.get(key, "").strip()
    )
    if inherited_overrides:
        raise RepositoryIdentityPolicyError(
            "WB-0034 trusted-main refresh rejects inherited Git/HTTP transport overrides: "
            + ", ".join(inherited_overrides)
        )

    direct_config_checks = (
        ("--get", "core.sshCommand"),
        ("--get", "core.gitProxy"),
        ("--get", "remote.origin.proxy"),
        ("--get", "remote.origin.vcs"),
        ("--get-regexp", r"^protocol\..*\.allow$"),
        ("--get-regexp", r"^url\..*\.insteadof$"),
    )
    for query in direct_config_checks:
        value = _optional_git_config_value(repo, *query)
        if value is not None:
            raise RepositoryIdentityPolicyError(
                "WB-0034 trusted-main refresh rejects Git transport rewrite/override config"
            )

    # URL-scoped Git transport configuration must be evaluated against the exact
    # accepted origin value that the subsequent fetch will use. Git URL matching
    # distinguishes the canonical origin forms with and without the `.git` suffix.
    canonical_url = origin
    proxy = _optional_git_config_value(repo, "--get-urlmatch", "http.proxy", canonical_url)
    if proxy is not None:
        raise RepositoryIdentityPolicyError(
            "WB-0034 trusted-main refresh rejects configured HTTP proxy transport"
        )

    ssl_verify = _optional_git_config_value(
        repo,
        "--bool",
        "--get-urlmatch",
        "http.sslVerify",
        canonical_url,
    )
    if ssl_verify is not None and ssl_verify != "true":
        raise RepositoryIdentityPolicyError(
            "WB-0034 trusted-main refresh requires Git HTTPS certificate verification"
        )

    for option in ("http.sslCAInfo", "http.sslCAPath", "http.curloptResolve"):
        value = _optional_git_config_value(repo, "--get-urlmatch", option, canonical_url)
        if value is not None:
            raise RepositoryIdentityPolicyError(
                f"WB-0034 trusted-main refresh rejects custom Git transport option {option}"
            )


def expected_repository_identity(repo: Path) -> str:
    """Read the canonical repository identity from .cybercore/project.yaml."""
    resolved = repo.expanduser().resolve()
    project = resolved / ".cybercore" / "project.yaml"
    expected = _configured_repository_identity(resolved)
    if expected is None:
        if not project.exists():
            raise RepositoryIdentityPolicyError(f"Canonical project state is missing: {project}")
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
    """Enforce repository identity for identity-sensitive operations.

    Most legacy operations retain backward-compatible behavior when
    identity.repository is not configured. Operations listed in
    _REQUIRED_OPERATION_IDENTITIES are stronger trust boundaries: their
    canonical identity is pinned in code and must also be declared exactly in
    project state, so removing or rewriting the checkout's identity setting
    cannot downgrade enforcement.
    """
    resolved = repo.expanduser().resolve()
    configured_identity = _configured_repository_identity(resolved)
    required_identity = _REQUIRED_OPERATION_IDENTITIES.get(operation)

    if required_identity is not None:
        if configured_identity != required_identity:
            if configured_identity is None:
                raise RepositoryIdentityPolicyError(
                    f"{operation} requires pinned canonical repository identity "
                    f"{required_identity}; configured identity is not configured."
                )
            raise RepositoryIdentityPolicyError(
                f"{operation} requires pinned canonical repository identity "
                f"{required_identity}; configured identity does not match."
            )
        if operation == _WB0034_TRUSTED_MAIN_OPERATION:
            _enforce_wb0034_repository_selection_environment()
        result = evaluate_repository_identity_policy(resolved)
        if not result.compliant or result.actual_identity != required_identity:
            raise RepositoryIdentityPolicyError(
                f"{operation} rejected by repository identity policy: {result.message} "
                "The resolved repository identity did not match the pinned canonical identity."
            )
        if operation == _WB0034_TRUSTED_MAIN_OPERATION:
            _enforce_wb0034_git_transport_policy(resolved)
        return result

    if configured_identity is None:
        return None
    result = evaluate_repository_identity_policy(resolved)
    if not result.compliant:
        raise RepositoryIdentityPolicyError(
            f"{operation} rejected by repository identity policy: {result.message} "
            f"Expected {result.expected_identity}, got {result.actual_identity}."
        )
    return result


def disclosed_repository_identity_policy_payload(
    result: RepositoryIdentityPolicyResult,
    *,
    disclosure_mode: DisclosureMode | str = DisclosureMode.STANDARD,
) -> dict[str, str | bool | None]:
    mode = DisclosureMode(disclosure_mode)
    actual = result.actual_identity
    if result.source == "path_fallback":
        actual = (
            sanitize_disclosure_text(actual, mode=mode)
            if mode is DisclosureMode.FULL
            else "path:[REDACTED]"
        )
    else:
        actual = sanitize_disclosure_text(actual, mode=mode)

    origin = None if result.origin is None else sanitize_disclosure_text(result.origin, mode=mode)
    if mode is DisclosureMode.REDACTED:
        actual = "[REDACTED]"
        origin = "[REDACTED]" if origin is not None else None

    return {
        "status": result.status,
        "compliant": result.compliant,
        "expected_identity": sanitize_disclosure_text(
            result.expected_identity,
            mode=mode,
        ),
        "actual_identity": actual,
        "source": result.source,
        "origin": origin,
        "message": sanitize_disclosure_text(result.message, mode=mode),
    }


def render_repository_identity_policy(
    result: RepositoryIdentityPolicyResult,
    *,
    disclosure_mode: DisclosureMode | str = DisclosureMode.STANDARD,
) -> str:
    disclosed = disclosed_repository_identity_policy_payload(
        result,
        disclosure_mode=disclosure_mode,
    )
    origin = disclosed["origin"] or "not configured"
    return (
        "\n".join(
            [
                "REPOSITORY IDENTITY POLICY",
                f"Status: {disclosed['status']}",
                f"Compliant: {'yes' if disclosed['compliant'] else 'no'}",
                f"Expected: {disclosed['expected_identity']}",
                f"Actual: {disclosed['actual_identity']}",
                f"Source: {disclosed['source']}",
                f"Origin: {origin}",
                f"Message: {disclosed['message']}",
            ]
        )
        + "\n"
    )
