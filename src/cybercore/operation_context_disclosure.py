from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class DisclosureClass(StrEnum):
    """Sensitivity classification for Trusted Operation Context fields."""

    PUBLIC = "public"
    OPERATIONAL = "operational"
    SENSITIVE = "sensitive"
    SECRET = "secret"


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


def disclosure_field(name: str) -> DisclosureField:
    """Return the canonical disclosure rule for a context field."""
    try:
        return _FIELD_INDEX[name]
    except KeyError as exc:
        raise KeyError(f"Unknown operation context disclosure field: {name}") from exc


def disclosure_class(name: str) -> DisclosureClass:
    """Return only the sensitivity class for a context field."""
    return disclosure_field(name).classification
