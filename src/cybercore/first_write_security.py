from __future__ import annotations

import re


PRIVATE_KEY_HEADER_RE = re.compile(
    r"-----BEGIN (?:[A-Z0-9][A-Z0-9 -]* )?PRIVATE KEY(?: BLOCK)?-----",
    re.IGNORECASE,
)

SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?im)\b(?:password|passwd|api[_-]?key|api[_-]?token|private[_-]?key|"
    r"secret(?:_value)?|credential|access[_-]?token|refresh[_-]?token)\s*[:=]\s*\S+"
)

CREDENTIAL_URL_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^/\s:@]+:[^@\s/]+@")


def scan_first_write_yaml_text(text: str, label: str) -> tuple[str, ...]:
    """Reject raw-text constructs that may hide credentials from YAML parsing."""

    errors: list[str] = []

    # WB-0034 machine artifacts are intentionally comment-free. This makes
    # credentials hidden in comments impossible and keeps the approval packet
    # deterministic for hashing and review.
    if "#" in text:
        errors.append(f"{label} forbids YAML comments")

    if PRIVATE_KEY_HEADER_RE.search(text):
        errors.append(f"{label} contains private-key material")

    if SENSITIVE_ASSIGNMENT_RE.search(text):
        errors.append(f"{label} contains a credential-like assignment")

    if CREDENTIAL_URL_RE.search(text):
        errors.append(f"{label} contains a credential-bearing URL")

    return tuple(errors)
