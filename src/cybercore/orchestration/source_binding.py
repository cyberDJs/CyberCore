from __future__ import annotations

import re
from typing import Literal, NotRequired, TypedDict

from cybercore.orchestration.contracts import Authority, Scalar, SourceSnapshot

Provider = Literal["GITHUB", "GOOGLE_DRIVE"]
LocatorScalar = str | int | bool | None
BindingStatus = Literal["BOUND", "UNKNOWN"]
BindingIssueReason = Literal[
    "INVALID_BINDING",
    "DUPLICATE_BINDING_ID",
    "DUPLICATE_SOURCE_ID",
    "UNSUPPORTED_PROVIDER",
    "UNSAFE_LOCATOR",
    "UNBOUND",
    "AMBIGUOUS_BINDING",
    "INVALID_CONTENT_HASH",
]

_VALID_PROVIDERS = frozenset({"GITHUB", "GOOGLE_DRIVE"})
_VALID_AUTHORITIES = frozenset({"CANONICAL", "EVIDENCE", "WORKING"})
_SAFE_LOCATOR_KEYS: dict[Provider, frozenset[str]] = {
    "GITHUB": frozenset({"repository", "ref", "path", "resource_kind", "number", "sha"}),
    "GOOGLE_DRIVE": frozenset(
        {"file_id", "parent_id", "ancestor_id", "resource_kind", "mime_type"}
    ),
}


class ProviderObservation(TypedDict):
    """Provider metadata plus normalized facts; never carries authority."""

    source_id: str
    provider: Provider
    locator: dict[str, LocatorScalar]
    facts: dict[str, Scalar]
    observed_at: NotRequired[str]
    content_sha256: NotRequired[str]


class TrustedSourceBinding(TypedDict):
    """Authority rule supplied by the trusted CASER-SOURCER layer."""

    binding_id: str
    provider: Provider
    authority: Authority
    match: dict[str, LocatorScalar]


class SourceProvenance(TypedDict):
    source_id: str
    provider: Provider
    authority: Authority
    binding_id: str
    locator: dict[str, LocatorScalar]
    observed_at: NotRequired[str]
    content_sha256: NotRequired[str]


class BindingIssue(TypedDict):
    source_id: str
    reason: BindingIssueReason
    candidate_binding_ids: list[str]
    detail: str


class BindingResult(TypedDict):
    status: BindingStatus
    sources: list[SourceSnapshot]
    provenance: list[SourceProvenance]
    binding_issues: list[BindingIssue]


def _issue(
    source_id: str,
    reason: BindingIssueReason,
    detail: str,
    candidate_binding_ids: list[str] | None = None,
) -> BindingIssue:
    return {
        "source_id": source_id,
        "reason": reason,
        "candidate_binding_ids": sorted(candidate_binding_ids or []),
        "detail": detail,
    }


def _valid_match_value(value: LocatorScalar) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _validate_binding(binding: TrustedSourceBinding) -> str | None:
    provider = binding["provider"]
    if provider not in _VALID_PROVIDERS:
        return f"Unsupported binding provider: {provider!r}."

    authority = binding["authority"]
    if authority not in _VALID_AUTHORITIES:
        return f"Unsupported binding authority: {authority!r}."

    match = binding.get("match", {})
    if not match:
        return "Binding match must not be empty; provider-wide authority is forbidden."

    safe_keys = _SAFE_LOCATOR_KEYS[provider]
    unsafe_keys = sorted(set(match) - safe_keys)
    if unsafe_keys:
        return f"Binding uses unsupported locator keys: {', '.join(unsafe_keys)}"
    if any(not _valid_match_value(value) for value in match.values()):
        return "Binding match values must be stable, non-empty locator values."

    if provider == "GITHUB" and "repository" not in match:
        return "GitHub bindings must pin repository identity."
    if provider == "GOOGLE_DRIVE" and not {
        "file_id",
        "parent_id",
        "ancestor_id",
    }.intersection(match):
        return "Google Drive bindings must pin a file, parent, or ancestor identity."
    return None


def _binding_matches(
    observation: ProviderObservation,
    binding: TrustedSourceBinding,
) -> bool:
    if observation["provider"] != binding["provider"]:
        return False
    locator = observation["locator"]
    return all(locator.get(key) == value for key, value in binding["match"].items())


def _safe_observation_locator(observation: ProviderObservation) -> str | None:
    safe_keys = _SAFE_LOCATOR_KEYS[observation["provider"]]
    unsafe_keys = sorted(set(observation.get("locator", {})) - safe_keys)
    if unsafe_keys:
        return f"Observation uses unsupported locator keys: {', '.join(unsafe_keys)}"
    return None


def _valid_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", value))


def bind_provider_observations(
    observations: list[ProviderObservation],
    bindings: list[TrustedSourceBinding],
) -> BindingResult:
    """Bind provider observations to authority using trusted exact-match rules.

    Authority is never read from provider content. Any invalid, unbound, or ambiguous
    observation fails the complete binding result closed as ``UNKNOWN`` while still
    returning safe diagnostics and successfully bound snapshots for inspection.
    """

    issues: list[BindingIssue] = []
    valid_bindings: list[TrustedSourceBinding] = []

    seen_binding_ids: set[str] = set()
    duplicate_binding_ids: set[str] = set()
    for binding in bindings:
        binding_id = binding["binding_id"]
        if binding_id in seen_binding_ids:
            duplicate_binding_ids.add(binding_id)
        seen_binding_ids.add(binding_id)

    for binding in bindings:
        binding_id = binding["binding_id"]
        if binding_id in duplicate_binding_ids:
            continue
        error = _validate_binding(binding)
        if error is not None:
            issues.append(_issue("*", "INVALID_BINDING", f"{binding_id}: {error}", [binding_id]))
            continue
        valid_bindings.append(binding)

    for binding_id in sorted(duplicate_binding_ids):
        issues.append(
            _issue(
                "*",
                "DUPLICATE_BINDING_ID",
                f"Trusted binding id is duplicated: {binding_id}",
                [binding_id],
            )
        )

    seen_source_ids: set[str] = set()
    duplicate_source_ids: set[str] = set()
    for observation in observations:
        source_id = observation["source_id"]
        if source_id in seen_source_ids:
            duplicate_source_ids.add(source_id)
        seen_source_ids.add(source_id)

    for source_id in sorted(duplicate_source_ids):
        issues.append(
            _issue(
                source_id,
                "DUPLICATE_SOURCE_ID",
                f"Provider observation source_id is duplicated: {source_id}",
            )
        )

    sources: list[SourceSnapshot] = []
    provenance: list[SourceProvenance] = []

    for observation in observations:
        source_id = observation["source_id"]
        if source_id in duplicate_source_ids:
            continue

        provider = observation["provider"]
        if provider not in _VALID_PROVIDERS:
            issues.append(
                _issue(
                    source_id,
                    "UNSUPPORTED_PROVIDER",
                    f"Unsupported observation provider: {provider!r}.",
                )
            )
            continue

        locator_error = _safe_observation_locator(observation)
        if locator_error is not None:
            issues.append(_issue(source_id, "UNSAFE_LOCATOR", locator_error))
            continue

        content_hash = observation.get("content_sha256")
        if content_hash is not None and not _valid_sha256(content_hash):
            issues.append(
                _issue(
                    source_id,
                    "INVALID_CONTENT_HASH",
                    "content_sha256 must be exactly 64 hexadecimal characters.",
                )
            )
            continue

        candidates = [
            binding for binding in valid_bindings if _binding_matches(observation, binding)
        ]
        if not candidates:
            issues.append(
                _issue(
                    source_id,
                    "UNBOUND",
                    "No trusted source binding matches this provider observation.",
                )
            )
            continue
        if len(candidates) > 1:
            candidate_ids = [binding["binding_id"] for binding in candidates]
            issues.append(
                _issue(
                    source_id,
                    "AMBIGUOUS_BINDING",
                    "Multiple trusted bindings match; authority cannot be resolved safely.",
                    candidate_ids,
                )
            )
            continue

        binding = candidates[0]
        sources.append(
            {
                "source_id": source_id,
                "authority": binding["authority"],
                "facts": dict(observation["facts"]),
            }
        )
        provenance_record: SourceProvenance = {
            "source_id": source_id,
            "provider": observation["provider"],
            "authority": binding["authority"],
            "binding_id": binding["binding_id"],
            "locator": dict(observation["locator"]),
        }
        if "observed_at" in observation:
            provenance_record["observed_at"] = observation["observed_at"]
        if content_hash is not None:
            provenance_record["content_sha256"] = content_hash.lower()
        provenance.append(provenance_record)

    return {
        "status": "UNKNOWN" if issues else "BOUND",
        "sources": sources,
        "provenance": provenance,
        "binding_issues": issues,
    }
