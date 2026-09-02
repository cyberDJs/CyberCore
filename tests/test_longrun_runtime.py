from pathlib import Path

import pytest

from cybercore.longrun.engine import LongRunEngine, StepResult
from cybercore.longrun.governor import StepProposal, authorize_step
from cybercore.longrun.manifest import LongRunManifest
from cybercore.longrun.state import LongRunStateStore
from cybercore.longrun.watchdog import evaluate_watchdog


def _manifest(**overrides):
    values = {
        "run_id": "marathon-test",
        "objective": "prove durable autonomous execution",
        "minimum_wall_seconds": 0,
        "maximum_wall_seconds": 3600,
    }
    values.update(overrides)
    return LongRunManifest(**values)


def _proposal(*, fingerprint="step-1", effect="read", value_gain=2.0):
    return StepProposal(
        fingerprint=fingerprint,
        expected_quality_gain=value_gain,
        expected_information_gain=1.0,
        cost=0.5,
        risk=0.1,
        duplication_probability=0.1,
        effect=effect,
    )


def test_manifest_digest_is_stable_and_immutable_contract_changes_digest():
    first = _manifest()
    same = _manifest()
    changed = _manifest(objective="different mission")
    assert first.digest == same.digest
    assert first.digest != changed.digest


def test_manifest_rejects_effect_overlap():
    manifest = _manifest(
        allowed_effects=("read", "production_write"),
        prohibited_effects=("production_write",),
    )
    with pytest.raises(ValueError):
        manifest.validate()


def test_value_governor_blocks_non_positive_and_non_allowlisted_steps():
    allowed, _ = authorize_step(
        _proposal(value_gain=-1.0),
        allowed_effects=("read",),
        prohibited_effects=("production_write",),
    )
    assert not allowed
    allowed, _ = authorize_step(
        _proposal(effect="sandbox_write"),
        allowed_effects=("read",),
        prohibited_effects=("production_write",),
    )
    assert not allowed


def test_watchdog_replans_failure_and_duplicate_loops():
    decision = evaluate_watchdog(
        elapsed_seconds=1,
        maximum_wall_seconds=100,
        consecutive_failures=3,
        max_consecutive_failures=3,
        duplicate_count=0,
        max_duplicate_steps=2,
    )
    assert decision.action == "REPLAN"
    decision = evaluate_watchdog(
        elapsed_seconds=1,
        maximum_wall_seconds=100,
        consecutive_failures=0,
        max_consecutive_failures=3,
        duplicate_count=2,
        max_duplicate_steps=2,
    )
    assert decision.action == "REPLAN"


def test_engine_resumes_from_sqlite_checkpoint(tmp_path: Path):
    store = LongRunStateStore(tmp_path / "state.sqlite")
    manifest = _manifest(evaluator_threshold=0.99)
    clock_value = [1000.0]

    def clock():
        clock_value[0] += 1
        return clock_value[0]

    def planner(state):
        return _proposal(fingerprint=f"step-{state.step_index + 1}")

    def executor(proposal):
        return StepResult(True, 0.5, {"proof": proposal.fingerprint})

    first_engine = LongRunEngine(manifest, store, planner=planner, executor=executor, clock=clock)
    state = first_engine.run_step()
    assert state.step_index == 1

    second_engine = LongRunEngine(
        manifest,
        LongRunStateStore(tmp_path / "state.sqlite"),
        planner=planner,
        executor=executor,
        clock=clock,
    )
    resumed = second_engine.run_step()
    assert resumed.step_index == 2


def test_engine_refuses_changed_manifest_after_checkpoint(tmp_path: Path):
    store = LongRunStateStore(tmp_path / "state.sqlite")
    original = _manifest()
    engine = LongRunEngine(
        original,
        store,
        planner=lambda state: _proposal(),
        executor=lambda proposal: StepResult(True, 1.0, {}),
    )
    engine.load_or_create()

    changed = _manifest(objective="silently changed objective")
    changed_engine = LongRunEngine(
        changed,
        store,
        planner=lambda state: _proposal(),
        executor=lambda proposal: StepResult(True, 1.0, {}),
    )
    with pytest.raises(RuntimeError, match="immutable mission contract"):
        changed_engine.load_or_create()


def test_engine_blocks_prohibited_effect_before_executor(tmp_path: Path):
    store = LongRunStateStore(tmp_path / "state.sqlite")
    executed = []
    engine = LongRunEngine(
        _manifest(),
        store,
        planner=lambda state: _proposal(effect="production_write"),
        executor=lambda proposal: executed.append(proposal) or StepResult(True, 1.0, {}),
    )
    state = engine.run_step()
    assert state.status == "BLOCKED"
    assert executed == []


def test_completion_requires_score_and_minimum_wall_budget(tmp_path: Path):
    store = LongRunStateStore(tmp_path / "state.sqlite")
    times = iter([0.0, 1.0, 2.0, 3.0, 6.0, 7.0])
    engine = LongRunEngine(
        _manifest(minimum_wall_seconds=5, evaluator_threshold=0.9),
        store,
        planner=lambda state: _proposal(fingerprint=f"step-{state.step_index}"),
        executor=lambda proposal: StepResult(True, 0.95, {"verified": True}),
        clock=lambda: next(times),
    )
    state = engine.run_step()
    assert state.status == "RUNNING"
    state = engine.run_step()
    assert state.status == "COMPLETED"
