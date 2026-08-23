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

CREDENTIAL_LITERAL_RE = re.compile(
    r"(?:"
    r"\bgh[pousr]_[A-Za-z0-9]{20,}\b|"
    r"\bgithub_pat_[A-Za-z0-9_]{20,}\b|"
    r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|"
    r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b|"
    r"\bglpat-[A-Za-z0-9_-]{20,}\b|"
    r"\bAIza[A-Za-z0-9_-]{30,}\b|"
    r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}\b"
    r")",
    re.IGNORECASE,
)

REFERENCE_LINE_RE = re.compile(
    r"(?m)^\s*([A-Za-z0-9_]*reference)\s*:\s*([^\s#]+)\s*$",
    re.IGNORECASE,
)

APPROVED_REFERENCE_VALUE_RE = re.compile(
    r"^(?:"
    r"evidence:wb0034:[A-Za-z0-9][A-Za-z0-9._:-]{2,191}|"
    r"approval:wb0034:[A-Za-z0-9][A-Za-z0-9._:-]{2,191}|"
    r"\.\./evidence/[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.ya?ml|"
    r"[0-9a-fA-F]{40}|"
    r"WB0034_[A-Z0-9_]{2,127}|"
    r"INTERSERVER_[A-Z0-9_]{2,127}|"
    r"REQUIRED_BEFORE_REMOTE_WRITE|"
    r"NOT_REQUIRED_FOR_PLAN_ONLY|"
    r"TBD"
    r")$"
)


def _reference_value_is_allowlisted(value: str) -> bool:
    return APPROVED_REFERENCE_VALUE_RE.fullmatch(value) is not None


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

    if CREDENTIAL_LITERAL_RE.search(text):
        errors.append(f"{label} contains a recognizable credential literal")

    for match in REFERENCE_LINE_RE.finditer(text):
        key, value = match.groups()
        if not _reference_value_is_allowlisted(value):
            errors.append(f"{label} reference field {key} uses a non-allowlisted value")

    return tuple(errors)
