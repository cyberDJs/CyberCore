import json
import pytest

from cybercore.voice.intelligence.contracts import INTENT_SCHEMA, ModelIntent
from cybercore.voice.models import IntentKind


def payload(**overrides):
    value = {
        "kind": "question",
        "operation": "explain",
        "target": None,
        "language": "cs",
        "confidence": 0.95,
        "needs_live_data": False,
    }
    value.update(overrides)
    return value


def test_model_intent_accepts_exact_schema() -> None:
    result = ModelIntent.from_json(json.dumps(payload()))
    assert result.kind is IntentKind.QUESTION
    assert result.language == "cs"


def test_model_intent_rejects_extra_fields() -> None:
    with pytest.raises(ValueError, match="fields do not match schema"):
        ModelIntent.from_mapping(payload(authority=True))


def test_model_intent_rejects_dangerous_kind() -> None:
    with pytest.raises(ValueError, match="authority-sensitive"):
        ModelIntent.from_mapping(payload(kind="approve"))


def test_model_intent_rejects_invalid_confidence() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        ModelIntent.from_mapping(payload(confidence=1.2))


def test_schema_does_not_offer_dangerous_kinds() -> None:
    kinds = set(INTENT_SCHEMA["properties"]["kind"]["enum"])
    assert {"cancel", "approve", "execute"}.isdisjoint(kinds)
