from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Mapping


class IntelligenceConfigError(ValueError):
    pass


def _numeric_config_value(
    data: Mapping[str, object],
    key: str,
    default: str | int | float,
) -> str | int | float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise IntelligenceConfigError(f"intelligence {key} must be numeric")
    return value


@dataclass(frozen=True)
class IntelligenceConfig:
    enabled: bool = False
    provider: str = "ollama"
    model: str = "qwen3:4b"
    base_url: str = "http://127.0.0.1:11434"
    timeout_s: float = 12.0
    min_confidence: float = 0.75
    max_answer_chars: int = 1200

    def __post_init__(self) -> None:
        if self.provider != "ollama":
            raise IntelligenceConfigError("WB-0039 reference provider must be 'ollama'")
        if not self.model.strip():
            raise IntelligenceConfigError("intelligence model must not be empty")
        if self.timeout_s <= 0:
            raise IntelligenceConfigError("intelligence timeout_s must be positive")
        if not 0.0 <= self.min_confidence <= 1.0:
            raise IntelligenceConfigError("intelligence min_confidence must be between 0 and 1")
        if not 80 <= self.max_answer_chars <= 8000:
            raise IntelligenceConfigError(
                "intelligence max_answer_chars must be between 80 and 8000"
            )

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> IntelligenceConfig:
        allowed = {
            "enabled",
            "provider",
            "model",
            "base_url",
            "timeout_s",
            "min_confidence",
            "max_answer_chars",
        }
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise IntelligenceConfigError(
                "unknown intelligence config field(s): " + ", ".join(unknown)
            )
        enabled = data.get("enabled", False)
        if not isinstance(enabled, bool):
            raise IntelligenceConfigError("intelligence enabled must be boolean")

        timeout_s = _numeric_config_value(data, "timeout_s", 12.0)
        min_confidence = _numeric_config_value(data, "min_confidence", 0.75)
        max_answer_chars = _numeric_config_value(data, "max_answer_chars", 1200)

        return cls(
            enabled=enabled,
            provider=str(data.get("provider", "ollama")),
            model=str(data.get("model", "qwen3:4b")),
            base_url=str(data.get("base_url", "http://127.0.0.1:11434")),
            timeout_s=float(timeout_s),
            min_confidence=float(min_confidence),
            max_answer_chars=int(max_answer_chars),
        )


def default_intelligence_config_path() -> Path:
    value = os.getenv("CYBERCORE_VOICE_INTELLIGENCE_CONFIG")
    if value:
        return Path(value).expanduser()
    return Path("~/.config/cybercore/voice-intelligence.json").expanduser()


def load_intelligence_config(path: Path | str | None = None) -> IntelligenceConfig:
    config_path = (
        Path(path).expanduser() if path is not None else default_intelligence_config_path()
    )
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if path is None:
            return IntelligenceConfig(enabled=False)
        raise IntelligenceConfigError(f"intelligence config not found: {config_path}")
    except json.JSONDecodeError as exc:
        raise IntelligenceConfigError(
            f"intelligence config is not valid JSON: {config_path}: {exc.msg}"
        ) from exc
    if not isinstance(raw, Mapping):
        raise IntelligenceConfigError("intelligence config root must be a JSON object")
    try:
        return IntelligenceConfig.from_mapping(raw)
    except IntelligenceConfigError:
        raise
    except (TypeError, ValueError) as exc:
        raise IntelligenceConfigError(f"invalid intelligence config value: {exc}") from exc
