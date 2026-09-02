import json
from collections import Counter
from pathlib import Path

from cybercore.voice.intelligence.safety import SafetyIntentGuard
from cybercore.voice.models import Utterance, VoiceContext


def test_eval_fixture_has_approved_75_case_shape() -> None:
    path = Path(__file__).parent / "fixtures" / "voice_intelligence_eval.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    assert len(cases) == 75
    assert Counter(case["category"] for case in cases) == {
        "cs_normal": 20,
        "en": 10,
        "mixed_slang": 10,
        "stt_like": 10,
        "authority": 15,
        "live_vs_general": 10,
    }


def test_all_authority_eval_cases_are_caught_before_model() -> None:
    path = Path(__file__).parent / "fixtures" / "voice_intelligence_eval.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    guard = SafetyIntentGuard()
    for index, case in enumerate(cases):
        if case["category"] != "authority":
            continue
        utterance = Utterance(
            id=f"u{index}",
            session_id="s1",
            actor_id="johnny",
            text=case["text"],
        )
        result = guard.compile(utterance, VoiceContext())
        assert result is not None, case["text"]
        assert result.kind.value == case["expected_kind"], case["text"]
