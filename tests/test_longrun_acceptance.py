from __future__ import annotations

from pathlib import Path

import pytest

from cybercore.longrun.acceptance import AcceleratedAcceptanceHarness, SimulatedClock
from cybercore.longrun.engine import LongRunEngine, StepResult
from cybercore.longrun.evaluation import EvaluationResult, evidence_digest
from cybercore.longrun.governor import StepProposal
from cybercore.longrun.manifest import LongRunManifest
from cybercore.longrun.state import LongRunStateStore


def _manifest(**overrides) -> LongRunManifest:
    values = {
        "run_id": "acceptance-test",
        "objective": "prove independent evaluator acceptance behavior",
        "minimum_wall_seconds": 0,
        "maximum_wall_seconds": 100,
        "max_consecutive_failures": 1,
    }
    values.update(overrides)
    return LongRunManifest(**values)


def _proposal() -> StepProposal:
    return StepProposal(
        fingerprint="acceptance-step",
        expected_quality_gain=1.0,
        expected_information_gain=1.0,
        cost=0.01,
        risk=0.01,
        duplication_probability=0.0,
        effect="read",
    )


def test_accelerated_harness_crash_resume_replan_and_complete(tmp_path: Path):
    store = LongRunStateStore(tmp_path / "state.sqlite")
    harness = AcceleratedAcceptanceHarness(
        clock=SimulatedClock(),
        crash_once_at_step=0,
        evaluator_score=1.0,
        evaluator_verdict="PASS",
    )

    first_engine = harness.engine(_manifest(), store)
    with pytest.raises(RuntimeError, match="crash injection"):
        first_engine.run_step()

    persisted = store.load("acceptance-test")
    assert persisted is not None
    assert persisted.step_index == 1
    assert persisted.consecutive_failures == 1

    reconstructed = harness.engine(_manifest(), LongRunStateStore(tmp_path / "state.sqlite"))
    completed = reconstructed.run_step()

    assert completed.status == "COMPLETED"
    assert completed.evaluator_score == 1.0
    events = LongRunStateStore(tmp_path / "state.sqlite").list_events("acceptance-test")
    assert [event.kind for event in events] == [
        "RUN_STARTED",
        "STEP_EXCEPTION",
        "WATCHDOG_REPLAN",
        "STEP_RESULT",
    ]
    evaluation = events[-1].payload["evaluation"]
    assert evaluation["evaluator_id"] == "cybercore.accelerated-acceptance-judge"
    assert evaluation["verdict"] == "PASS"
    assert evaluation["evidence_digest"] == events[-1].payload["evidence_digest"]
    assert evaluation["evaluation_digest"]


def test_missing_independent_evaluator_blocks_before_execution(tmp_path: Path):
    executed = []
    engine = LongRunEngine(
        _manifest(),
        LongRunStateStore(tmp_path / "state.sqlite"),
        planner=lambda state: _proposal(),
        executor=lambda proposal: (
            executed.append(proposal) or StepResult(True, {"proof": "should-not-run"})
        ),
    )

    state = engine.run_step()

    assert state.status == "BLOCKED"
    assert executed == []
    events = engine.store.list_events("acceptance-test")
    assert events[-1].kind == "EVALUATION_BLOCKED"
    assert "not configured" in events[-1].payload["reason"]


def test_tampered_evaluation_digest_blocks_completion(tmp_path: Path):
    def evaluator(proposal, result):
        return EvaluationResult(
            evaluator_id="tests.tampered-judge",
            evaluator_version="1",
            score=1.0,
            verdict="PASS",
            reasons=("claims acceptance without binding the real evidence",),
            evidence_digest="0" * 64,
        )

    engine = LongRunEngine(
        _manifest(),
        LongRunStateStore(tmp_path / "state.sqlite"),
        planner=lambda state: _proposal(),
        executor=lambda proposal: StepResult(True, {"proof": "real-evidence"}),
        evaluator=evaluator,
    )

    state = engine.run_step()

    assert state.status == "BLOCKED"
    assert state.evaluator_score == 0.0
    events = engine.store.list_events("acceptance-test")
    assert events[-1].kind == "EVALUATION_INVALID"
    assert "digest does not match" in events[-1].payload["reason"]


def test_evaluator_cannot_mutate_executor_evidence_snapshot(tmp_path: Path):
    executor_evidence = {"proof": {"value": "original"}}

    def evaluator(proposal, result):
        bound_digest = evidence_digest(result.evidence)
        proof = result.evidence["proof"]
        assert isinstance(proof, dict)
        proof["value"] = "tampered"
        return EvaluationResult(
            evaluator_id="tests.mutating-judge",
            evaluator_version="1",
            score=1.0,
            verdict="PASS",
            reasons=("mutated evaluator input after binding its original digest",),
            evidence_digest=bound_digest,
        )

    engine = LongRunEngine(
        _manifest(),
        LongRunStateStore(tmp_path / "state.sqlite"),
        planner=lambda state: _proposal(),
        executor=lambda proposal: StepResult(True, executor_evidence),
        evaluator=evaluator,
    )

    state = engine.run_step()

    assert state.status == "BLOCKED"
    assert executor_evidence == {"proof": {"value": "original"}}
    events = engine.store.list_events("acceptance-test")
    assert events[-1].kind == "EVALUATION_INVALID"
    assert events[-1].payload["reason"] == "evaluator mutated executor evidence snapshot"


def test_empty_executor_evidence_blocks_before_evaluator(tmp_path: Path):
    evaluated = []

    def evaluator(proposal, result):
        evaluated.append(result)
        raise AssertionError("evaluator must not run without required evidence")

    engine = LongRunEngine(
        _manifest(),
        LongRunStateStore(tmp_path / "state.sqlite"),
        planner=lambda state: _proposal(),
        executor=lambda proposal: StepResult(True, {}),
        evaluator=evaluator,
    )

    state = engine.run_step()

    assert state.status == "BLOCKED"
    assert evaluated == []
    events = engine.store.list_events("acceptance-test")
    assert events[-1].kind == "EVALUATION_BLOCKED"
    assert "evidence is required" in events[-1].payload["reason"]
