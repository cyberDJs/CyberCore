from __future__ import annotations

import re

import yaml


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

# Evidence references are opaque metadata locators, not containers for commit
# or digest material. Digest-shaped values are reserved for dedicated commit
# and digest fields elsewhere in the WB-0034 schemas.
_REFERENCE_EVIDENCE_ID = r"[0-9]{8}(?:T[0-9]{6}Z)?(?:-[A-Za-z0-9]{6,16})?"
APPROVED_REFERENCE_VALUE_RE = re.compile(
    r"^(?:"
    r"evidence:wb0034:[a-z0-9]+(?:-[a-z0-9]+){0,5}:" + _REFERENCE_EVIDENCE_ID + r"|"
    r"approval:wb0034:[0-9]{8}T[0-9]{6}Z(?:-[A-Za-z0-9]{6,16})?|"
    r"\.\./evidence/[A-Za-z0-9]+(?:-[A-Za-z0-9]+){0,15}\.ya?ml|"
    r"WB0034_[A-Z0-9_]{2,127}|"
    r"INTERSERVER_[A-Z0-9_]{2,127}|"
    r"REQUIRED_BEFORE_REMOTE_WRITE|"
    r"NOT_REQUIRED_FOR_PLAN_ONLY|"
    r"TBD"
    r")$"
)
SOURCE_COMMIT_REFERENCE_RE = re.compile(r"^[0-9a-fA-F]{40}$")

WB0034_RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[A-Za-z0-9]{6,16}$")
APPROVED_RUN_ID_PLACEHOLDERS = {"WB0034-FIRST-STAGING-WRITE-PLAN"}


def _reference_value_is_allowlisted(field_name: str, value: str) -> bool:
    if (
        field_name.lower() == "source_commit_reference"
        and SOURCE_COMMIT_REFERENCE_RE.fullmatch(value) is not None
    ):
        return True
    return APPROVED_REFERENCE_VALUE_RE.fullmatch(value) is not None


def _run_id_value_is_allowlisted(value: str) -> bool:
    return value in APPROVED_RUN_ID_PLACEHOLDERS or WB0034_RUN_ID_RE.fullmatch(value) is not None


def _scan_parsed_policy_fields(document: object, label: str) -> tuple[str, ...]:
    """Validate security-sensitive parsed fields independent of YAML syntax."""

    errors: list[str] = []
    pending: list[tuple[str, object]] = [("$", document)]
    seen_containers: set[int] = set()

    while pending:
        path, value = pending.pop()

        if isinstance(value, dict):
            object_id = id(value)
            if object_id in seen_containers:
                continue
            seen_containers.add(object_id)

            for key, child in value.items():
                key_text = str(key) if isinstance(key, str) else repr(key)
                child_path = f"{path}.{key_text}"
                if isinstance(key, str) and key.lower().endswith("reference"):
                    if (
                        not isinstance(child, str)
                        or not _reference_value_is_allowlisted(key, child)
                    ):
                        errors.append(
                            f"{label} reference field {child_path} uses a non-allowlisted value"
                        )
                if isinstance(key, str) and key.lower() == "run_id":
                    if not isinstance(child, str) or not _run_id_value_is_allowlisted(child):
                        errors.append(
                            f"{label} run_id field {child_path} must use the structured WB-0034 format"
                        )
                pending.append((child_path, child))

        elif isinstance(value, list):
            object_id = id(value)
            if object_id in seen_containers:
                continue
            seen_containers.add(object_id)
            for index, child in enumerate(value):
                pending.append((f"{path}[{index}]", child))

    return tuple(errors)


def scan_first_write_yaml_text(text: str, label: str) -> tuple[str, ...]:
    """Reject raw-text and parsed constructs that may hide credentials."""

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

    # Keep the line-oriented check as defense in depth for the ordinary YAML
    # representation, but never rely on it as the authority boundary.
    for match in REFERENCE_LINE_RE.finditer(text):
        key, value = match.groups()
        if not _reference_value_is_allowlisted(key, value):
            errors.append(f"{label} reference field {key} uses a non-allowlisted value")

    # YAML permits equivalent mappings to be expressed with explicit keys,
    # flow mappings, quoted scalars, and other layouts that a line regex cannot
    # recognize. Parse the document and validate security-sensitive fields in
    # the normalized object graph so syntax cannot bypass policy.
    try:
        parsed = yaml.safe_load(text)
    except (RecursionError, yaml.YAMLError) as exc:
        errors.append(f"{label} cannot be parsed safely for reference validation: {exc}")
    else:
        errors.extend(_scan_parsed_policy_fields(parsed, label))

    return tuple(errors)
