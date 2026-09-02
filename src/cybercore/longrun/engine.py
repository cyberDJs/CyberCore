from __future__ import annotations

from dataclasses import dataclass, replace
import time
from typing import Callable

from cybercore.longrun.governor import StepProposal, authorize_step
from cybercore.longrun.manifest import LongRunManifest
from cybercore.longrun.state import LongRunStateStore, RunState
from cybercore.longrun.watchdog import evaluate_watchdog


@dataclass(frozen=True, slots=True)
class StepResult:
    success: bool
    evaluator_score: float
    evidence: dict[str, object]


Planner = Callable[[RunState], StepProposal]
Executor = Callable[[StepProposal], StepResult]
Clock = Callable[[], float]


class LongRunEngine:
    def __init__(
        self,
        manifest: LongRunManifest,
        store: LongRunStateStore,
        *,
        planner: Planner,
        executor: Executor,
        clock: Clock = time.time,
    ) -> None:
        manifest.validate()
        self.manifest = manifest
        self.store = store
        self.planner = planner
        self.executor = executor
        self.clock = clock

    def _initial_state(self) -> RunState:
        now = self.clock()
        return RunState(
            run_id=self.manifest.run_id,
            manifest_digest=self.manifest.digest,
            status="RUNNING",
            step_index=0,
            consecutive_failures=0,
            last_step_fingerprint=None,
            duplicate_count=0,
            evaluator_score=0.0,
            started_at=now,
            updated_at=now,
        )

    def load_or_create(self) -> RunState:
        existing = self.store.load(self.manifest.run_id)
        if existing is None:
            state = self._initial_state()
            self.store.create(state)
            self.store.append_event(
                state.run_id,
                state.step_index,
                "RUN_STARTED",
                {"manifest_digest": state.manifest_digest},
                state.started_at,
            )
            return state
        if existing.manifest_digest != self.manifest.digest:
            raise RuntimeError("manifest digest mismatch; immutable mission contract changed")
        return existing

    def run_step(self) -> RunState:
        state = self.load_or_create()
        if state.status in {"COMPLETED", "STOPPED", "BLOCKED"}:
            return state

        now = self.clock()
        elapsed = now - state.started_at
        watchdog = evaluate_watchdog(
            elapsed_seconds=elapsed,
            maximum_wall_seconds=self.manifest.maximum_wall_seconds,
            consecutive_failures=state.consecutive_failures,
            max_consecutive_failures=self.manifest.max_consecutive_failures,
            duplicate_count=state.duplicate_count,
            max_duplicate_steps=self.manifest.max_duplicate_steps,
        )
        if watchdog.action == "STOP":
            stopped = replace(state, status="STOPPED", updated_at=now)
            self.store.save(stopped)
            self.store.append_event(
                stopped.run_id,
                stopped.step_index,
                "WATCHDOG_STOP",
                {"reason": watchdog.reason},
                now,
            )
            return stopped
        if watchdog.action == "REPLAN":
            state = replace(
                state,
                consecutive_failures=0,
                duplicate_count=0,
                last_step_fingerprint=None,
                updated_at=now,
            )
            self.store.save(state)
            self.store.append_event(
                state.run_id, state.step_index, "WATCHDOG_REPLAN", {"reason": watchdog.reason}, now
            )

        proposal = self.planner(state)
        allowed, reason = authorize_step(
            proposal,
            allowed_effects=self.manifest.allowed_effects,
            prohibited_effects=self.manifest.prohibited_effects,
        )
        if not allowed:
            blocked = replace(state, status="BLOCKED", updated_at=self.clock())
            self.store.save(blocked)
            self.store.append_event(
                blocked.run_id,
                blocked.step_index,
                "STEP_BLOCKED",
                {"fingerprint": proposal.fingerprint, "reason": reason},
                blocked.updated_at,
            )
            return blocked

        duplicate_count = (
            state.duplicate_count + 1 if proposal.fingerprint == state.last_step_fingerprint else 0
        )
        result = self.executor(proposal)
        now = self.clock()
        new_state = replace(
            state,
            step_index=state.step_index + 1,
            consecutive_failures=0 if result.success else state.consecutive_failures + 1,
            last_step_fingerprint=proposal.fingerprint,
            duplicate_count=duplicate_count,
            evaluator_score=max(state.evaluator_score, result.evaluator_score),
            updated_at=now,
        )

        elapsed = now - new_state.started_at
        if (
            result.success
            and result.evaluator_score >= self.manifest.evaluator_threshold
            and elapsed >= self.manifest.minimum_wall_seconds
        ):
            new_state = replace(new_state, status="COMPLETED")

        self.store.save(new_state)
        self.store.append_event(
            new_state.run_id,
            new_state.step_index,
            "STEP_RESULT",
            {
                "fingerprint": proposal.fingerprint,
                "success": result.success,
                "evaluator_score": result.evaluator_score,
                "value": proposal.value,
                "evidence": result.evidence,
            },
            now,
        )
        return new_state

    def run_until_terminal(self, *, max_steps: int | None = None) -> RunState:
        steps = 0
        state = self.load_or_create()
        while state.status == "RUNNING":
            if max_steps is not None and steps >= max_steps:
                return state
            state = self.run_step()
            steps += 1
        return state
