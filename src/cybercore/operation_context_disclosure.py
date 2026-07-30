from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import re
from typing import Final, Mapping
from urllib.parse import unquote_plus, urlsplit, urlunsplit


class DisclosureClass(StrEnum):
    """Sensitivity classification for Trusted Operation Context fields."""

    PUBLIC = "public"
    OPERATIONAL = "operational"
    SENSITIVE = "sensitive"
    SECRET = "secret"


class DisclosureMode(StrEnum):
    """Supported disclosure profiles for human and machine output."""

    STANDARD = "standard"
    REDACTED = "redacted"
    FULL = "full"


@dataclass(frozen=True, slots=True)
class DisclosureField:
    """One stable field-level disclosure rule."""

    name: str
    classification: DisclosureClass
    rationale: str


DISCLOSURE_FIELDS: Final[tuple[DisclosureField, ...]] = (
    DisclosureField(
        "trusted",
        DisclosureClass.PUBLIC,
        "Boolean policy outcome required by human and machine consumers.",
    ),
    DisclosureField(
        "dirty",
        DisclosureClass.PUBLIC,
        "Boolean working-tree state without repository content.",
    ),
    DisclosureField(
        "project_kernel_present",
        DisclosureClass.PUBLIC,
        "Boolean Project Kernel presence indicator.",
    ),
    DisclosureField(
        "project_state_present",
        DisclosureClass.PUBLIC,
        "Boolean Project State presence indicator.",
    ),
    DisclosureField(
        "operation",
        DisclosureClass.OPERATIONAL,
        "Operation identifier needed to interpret policy results.",
    ),
    DisclosureField(
        "risk",
        DisclosureClass.OPERATIONAL,
        "Risk classification needed to interpret enforcement strength.",
    ),
    DisclosureField(
        "branch",
        DisclosureClass.OPERATIONAL,
        "Current branch is operational metadata and may reveal workflow names.",
    ),
    DisclosureField(
        "commit",
        DisclosureClass.OPERATIONAL,
        "Commit identity is operational metadata and evidence binding.",
    ),
    DisclosureField(
        "commit_subject",
        DisclosureClass.OPERATIONAL,
        "Commit subject is operational metadata and may include local context.",
    ),
    DisclosureField(
        "checks",
        DisclosureClass.OPERATIONAL,
        "Policy check names and outcomes are operational diagnostics.",
    ),
    DisclosureField(
        "repository",
        DisclosureClass.SENSITIVE,
        "Absolute local repository paths can reveal usernames and host layout.",
    ),
    DisclosureField(
        "remote_url",
        DisclosureClass.SENSITIVE,
        "Repository remotes can contain private locations or embedded credentials.",
    ),
    DisclosureField(
        "credentials",
        DisclosureClass.SECRET,
        "Credentials, tokens and secret-like values must never be disclosed.",
    ),
)

_FIELD_INDEX: Final[dict[str, DisclosureField]] = {
    field.name: field for field in DISCLOSURE_FIELDS
}
_REDACTED: Final[str] = "[REDACTED]"
_REDACTED_PATH: Final[str] = "[REDACTED_PATH]"
_PATH_CHARS = r"[^\r\n;,`'\"\)\]\}<]+"
_POSIX_PATH = re.compile(rf"(?<![\w.:@-])/{_PATH_CHARS}")
_WINDOWS_DRIVE_PATH = re.compile(rf"(?<![\w.-])[A-Za-z]:\\{_PATH_CHARS}")
_UNC_PATH = re.compile(rf"\\\\{_PATH_CHARS}")
_URL = re.compile(r"\b(?:https?|ssh|git|file)://[^\s`'\")]+")
_SCP_LIKE_GIT = re.compile(
    r"(?<![\w.-])(?P<user>[^@\s:/]+)@(?P<host>[^:\s/]+):(?P<path>[^\s`'\")]+)"
)
_SECRET_OPTION = re.compile(
    r"(?i)(token|password|passwd|secret|credential|api[-_]?key|access[-_]?key)"
)
_SECRET_PARAMETER_NAMES: Final[set[str]] = {
    "token",
    "access_token",
    "refresh_token",
    "password",
    "passwd",
    "secret",
    "credential",
    "api_key",
    "access_key",
}
_URL_PARAMETER = re.compile(r"(?P<prefix>^|[&;])(?P<key>[^=&;#]+)=(?P<value>[^&;#]*)")
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?P<prefix>\b(?:token|access_token|refresh_token|password|passwd|"
    r"secret|credential|api[-_]?key|access[-_]?key)\b\s*[:=]\s*)"
    r"(?P<quote>[\"']?)(?P<value>[^\s,;`\"')\]}<]+)(?P=quote)"
)


def disclosure_field(name: str) -> DisclosureField:
    """Return the canonical disclosure rule for a context field."""
    try:
        return _FIELD_INDEX[name]
    except KeyError as exc:
        raise KeyError(f"Unknown operation context disclosure field: {name}") from exc


def disclosure_class(name: str) -> DisclosureClass:
    """Return only the sensitivity class for a context field."""
    return disclosure_field(name).classification


def _is_secret_parameter_name(value: str) -> bool:
    normalized = unquote_plus(value).lower().replace("-", "_")
    return normalized in _SECRET_PARAMETER_NAMES


def _redact_url_component_secrets(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        if not _is_secret_parameter_name(match.group("key")):
            return match.group(0)
        return f"{match.group('prefix')}{match.group('key')}={_REDACTED}"

    return _URL_PARAMETER.sub(replace, value)


def _redact_url_credentials(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme == "file":
        return f"file://{_REDACTED_PATH}"
    if not parsed.scheme or not parsed.netloc:
        return value
    netloc = parsed.netloc
    if "@" in parsed.netloc:
        host = parsed.hostname or ""
        if parsed.port is not None:
            host = f"{host}:{parsed.port}"
        netloc = host
    return urlunsplit(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            _redact_url_component_secrets(parsed.query),
            _redact_url_component_secrets(parsed.fragment),
        )
    )


def _redact_scp_like_git_credentials(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        user = match.group("user")
        host = match.group("host")
        path = match.group("path")
        if user == "git":
            return match.group(0)
        return f"{host}:{path}"

    return _SCP_LIKE_GIT.sub(replace, value)


def _redact_secret_assignments(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        quote = match.group("quote")
        return f"{match.group('prefix')}{quote}{_REDACTED}{quote}"

    return _SECRET_ASSIGNMENT.sub(replace, value)


def sanitize_disclosure_text(
    value: object,
    *,
    mode: DisclosureMode | str = DisclosureMode.STANDARD,
) -> str:
    """Return a terminal-safe diagnostic string for disclosure surfaces."""
    selected_mode = DisclosureMode(mode)
    text = str(value)
    protected_urls: list[str] = []

    def protect_url(match: re.Match[str]) -> str:
        protected_urls.append(_redact_url_credentials(match.group(0)))
        return f"__CYBERCORE_URL_{len(protected_urls) - 1}__"

    text = _URL.sub(protect_url, text)
    text = _redact_scp_like_git_credentials(text)
    text = _redact_secret_assignments(text)
    if selected_mode is not DisclosureMode.FULL:
        text = _UNC_PATH.sub(_REDACTED_PATH, text)
        text = _WINDOWS_DRIVE_PATH.sub(_REDACTED_PATH, text)
        text = _POSIX_PATH.sub(_REDACTED_PATH, text)
    for index, url in enumerate(protected_urls):
        text = text.replace(f"__CYBERCORE_URL_{index}__", url)
    return text


def sanitize_command_argument(value: str) -> str:
    """Sanitize one persisted command argument."""
    if "=" in value:
        key, _separator, raw_value = value.partition("=")
        if _SECRET_OPTION.search(key):
            return f"{key}={_REDACTED}"
        return f"{key}={sanitize_disclosure_text(raw_value)}"
    if _SECRET_OPTION.fullmatch(value.lstrip("-")):
        return value
    return sanitize_disclosure_text(value)


def sanitize_command_arguments(arguments: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Sanitize command argv for persisted evidence."""
    sanitized: list[str] = []
    redact_next = False
    for argument in arguments:
        if redact_next:
            sanitized.append(_REDACTED)
            redact_next = False
            continue
        sanitized_argument = sanitize_command_argument(str(argument))
        sanitized.append(sanitized_argument)
        option_name = str(argument).lstrip("-")
        if "=" not in str(argument) and _SECRET_OPTION.fullmatch(option_name):
            redact_next = True
    return tuple(sanitized)


def disclosure_display_path(
    path: Path,
    *,
    repo: Path | None = None,
    mode: DisclosureMode | str = DisclosureMode.STANDARD,
) -> str:
    """Render a path for terminal diagnostics without leaking local layout."""
    selected_mode = DisclosureMode(mode)
    resolved = path.expanduser()
    if selected_mode is DisclosureMode.FULL:
        return str(resolved.resolve())
    if repo is not None:
        try:
            return str(resolved.resolve().relative_to(repo.expanduser().resolve()))
        except ValueError:
            pass
    return resolved.name or _REDACTED_PATH


def _sanitize_nested(value: object, *, mode: DisclosureMode) -> object:
    if isinstance(value, str):
        return sanitize_disclosure_text(value, mode=mode)
    if isinstance(value, bool) or value is None or isinstance(value, (int, float)):
        return value
    if isinstance(value, Mapping):
        sanitized: dict[str, object] = {}
        for key, item in value.items():
            name = str(key)
            if name in _FIELD_INDEX:
                if disclosure_class(name) is DisclosureClass.SECRET:
                    continue
            elif name not in {"name", "passed", "detail"}:
                continue
            sanitized[name] = _sanitize_nested(item, mode=mode)
        return sanitized
    if isinstance(value, (list, tuple)):
        return [_sanitize_nested(item, mode=mode) for item in value]
    return sanitize_disclosure_text(value, mode=mode)


def disclose_context_payload(
    payload: Mapping[str, object],
    *,
    mode: DisclosureMode | str = DisclosureMode.STANDARD,
) -> dict[str, object]:
    """Return a stable, policy-filtered context payload.

    Unknown fields and secret fields are omitted. Public values are always preserved.
    Standard mode exposes operational values and redacts sensitive values. Redacted
    mode additionally redacts operational values. Full mode exposes sensitive values
    but still never emits secret fields.
    """
    selected_mode = DisclosureMode(mode)
    disclosed: dict[str, object] = {}

    for field in DISCLOSURE_FIELDS:
        if field.name not in payload:
            continue
        value = payload[field.name]
        classification = field.classification

        if classification is DisclosureClass.SECRET:
            continue
        if classification is DisclosureClass.PUBLIC:
            disclosed[field.name] = value
            continue
        if classification is DisclosureClass.OPERATIONAL:
            disclosed[field.name] = (
                _REDACTED
                if selected_mode is DisclosureMode.REDACTED
                else _sanitize_nested(value, mode=selected_mode)
            )
            continue
        disclosed[field.name] = (
            _sanitize_nested(value, mode=selected_mode)
            if selected_mode is DisclosureMode.FULL
            else _REDACTED
        )

    return disclosed


def render_disclosed_context(
    payload: Mapping[str, object],
    *,
    mode: DisclosureMode | str = DisclosureMode.STANDARD,
) -> str:
    """Render the policy-filtered payload without bypassing field classification."""
    disclosed = disclose_context_payload(payload, mode=mode)
    lines = ["TRUSTED OPERATION CONTEXT"]
    for field in DISCLOSURE_FIELDS:
        if field.name not in disclosed:
            continue
        lines.append(f"{field.name}: {disclosed[field.name]}")
    return "\n".join(lines) + "\n"
