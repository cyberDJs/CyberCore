from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Mapping


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


def disclosure_field(name: str) -> DisclosureField:
    """Return the canonical disclosure rule for a context field."""
    try:
        return _FIELD_INDEX[name]
    except KeyError as exc:
        raise KeyError(f"Unknown operation context disclosure field: {name}") from exc


def disclosure_class(name: str) -> DisclosureClass:
    """Return only the sensitivity class for a context field."""
    return disclosure_field(name).classification


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
                _REDACTED if selected_mode is DisclosureMode.REDACTED else value
            )
            continue
        disclosed[field.name] = (
            value if selected_mode is DisclosureMode.FULL else _REDACTED
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
