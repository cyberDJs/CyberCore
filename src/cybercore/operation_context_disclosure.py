from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import re
from typing import Final, Mapping
from urllib.parse import urlsplit, urlunsplit


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
_ABSOLUTE_PATH = re.compile(
    r"(?<![\w.-])/(?:Users|home|private|tmp|var|Volumes)/[^\s;,)`'\"]+"
)
_URL = re.compile(r"\bhttps?://[^\s`'\")]+")


def disclosure_field(name: str) -> DisclosureField:
    """Return the canonical disclosure rule for a context field."""
    try:
        return _FIELD_INDEX[name]
    except KeyError as exc:
        raise KeyError(f"Unknown operation context disclosure field: {name}") from exc


def disclosure_class(name: str) -> DisclosureClass:
    """Return only the sensitivity class for a context field."""
    return disclosure_field(name).classification


def _redact_url_credentials(value: str) -> str:
    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.netloc or "@" not in parsed.netloc:
        return value
    host = parsed.hostname or ""
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))


def sanitize_disclosure_text(
    value: object,
    *,
    mode: DisclosureMode | str = DisclosureMode.STANDARD,
) -> str:
    """Return a terminal-safe diagnostic string for disclosure surfaces."""
    selected_mode = DisclosureMode(mode)
    text = str(value)
    text = _URL.sub(lambda match: _redact_url_credentials(match.group(0)), text)
    if selected_mode is not DisclosureMode.FULL:
        text = _ABSOLUTE_PATH.sub(_REDACTED_PATH, text)
    return text


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
