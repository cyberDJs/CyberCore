from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cybercore.longrun.manifest import LongRunManifest


_PROFILE_KEYS = {
    "version",
    "profile",
    "minimum_wall_seconds",
    "maximum_wall_seconds",
    "evaluator_threshold",
    "checkpoint_every_steps",
    "max_consecutive_failures",
    "max_duplicate_steps",
    "allowed_effects",
    "prohibited_effects",
    "policy",
}
_MISSION_KEYS = {"version", "run_id", "objective", "metadata"}
_POLICY_KEYS = {
    "evidence_required",
    "independent_evaluation_required",
    "immutable_mission_required",
    "fail_closed_on_unknown_effect",
}


def _load_mapping(path: Path, *, label: str) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid {label} YAML: {path}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be a YAML mapping: {path}")
    return raw


def _reject_unknown(mapping: dict[str, Any], allowed: set[str], *, label: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise ValueError(f"unknown {label} fields: {unknown}")


def _require_int(mapping: dict[str, Any], key: str, *, label: str) -> int:
    value = mapping.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label}.{key} must be an integer")
    return value


def _require_float(mapping: dict[str, Any], key: str, *, label: str) -> float:
    value = mapping.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label}.{key} must be numeric")
    return float(value)


def _require_string(mapping: dict[str, Any], key: str, *, label: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}.{key} must be a non-empty string")
    return value.strip()


def _require_string_list(mapping: dict[str, Any], key: str, *, label: str) -> tuple[str, ...]:
    value = mapping.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label}.{key} must be a non-empty string list")
    return tuple(item.strip() for item in value if item.strip())


def load_manifest(profile_path: Path, mission_path: Path) -> LongRunManifest:
    profile = _load_mapping(profile_path, label="profile")
    mission = _load_mapping(mission_path, label="mission")
    _reject_unknown(profile, _PROFILE_KEYS, label="profile")
    _reject_unknown(mission, _MISSION_KEYS, label="mission")

    if _require_int(profile, "version", label="profile") != 0:
        raise ValueError("unsupported LongRun profile version")
    if _require_int(mission, "version", label="mission") != 0:
        raise ValueError("unsupported LongRun mission version")

    profile_name = _require_string(profile, "profile", label="profile")
    policy = profile.get("policy")
    if not isinstance(policy, dict):
        raise ValueError("profile.policy must be a mapping")
    _reject_unknown(policy, _POLICY_KEYS, label="profile.policy")
    for key in sorted(_POLICY_KEYS):
        if policy.get(key) is not True:
            raise ValueError(f"profile.policy.{key} must be true for operator runtime")

    raw_metadata = mission.get("metadata", {})
    if not isinstance(raw_metadata, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in raw_metadata.items()
    ):
        raise ValueError("mission.metadata must contain only string keys and values")
    metadata = dict(raw_metadata)
    metadata["longrun_profile"] = profile_name

    manifest = LongRunManifest(
        run_id=_require_string(mission, "run_id", label="mission"),
        objective=_require_string(mission, "objective", label="mission"),
        minimum_wall_seconds=_require_int(profile, "minimum_wall_seconds", label="profile"),
        maximum_wall_seconds=_require_int(profile, "maximum_wall_seconds", label="profile"),
        evaluator_threshold=_require_float(profile, "evaluator_threshold", label="profile"),
        checkpoint_every_steps=_require_int(profile, "checkpoint_every_steps", label="profile"),
        max_consecutive_failures=_require_int(profile, "max_consecutive_failures", label="profile"),
        max_duplicate_steps=_require_int(profile, "max_duplicate_steps", label="profile"),
        allowed_effects=_require_string_list(profile, "allowed_effects", label="profile"),
        prohibited_effects=_require_string_list(profile, "prohibited_effects", label="profile"),
        metadata=metadata,
    )
    manifest.validate()
    return manifest
