from __future__ import annotations

from dataclasses import dataclass, replace
import time
from typing import Callable

from cybercore.longrun.evaluation import EvaluationResult, evidence_digest
from cybercore.longrun.governor import StepProposal, authorize_step
from cybercore.longrun.manifest import LongRunManifest
from cybercore.longrun.state import LongRunStateStore, RunState
from cybercore.longrun.watchdog import evaluate_watchdog


@dataclass(frozen=True, slots=True)
class StepResult:
    success: bool
    evidence: dict[str, object]


Planner = Callable[[RunState], StepProposal]
Executor = Callable[[StepProposal], StepResult]
Evaluator = Callable[[StepProposal, StepResult], EvaluationResult]
Clock = Callable[[], float]


class LongRunEngine:
    def __init__(
        self,
        manifest: LongRunManifest,
        store: LongRunStateStore,
        *,
        planner: Planner,
        executor: Executor,
        evaluator: Evaluator | None = None,
        clock: Clock = time.time,
    ) -> None:
        manifest.validate()
        if evaluator is executor:
            raise ValueError("executor and independent evaluator must be different callbacks")
        self.manifest = manifest
        self.store = store
        self.planner = planner
        self.executor = executor
        self.evaluator = evaluator
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
            self.store.create_with_event(
                state,
                "RUN_STARTED",
                {"manifest_digest": state.manifest_digest},
                state.started_at,
            )
            return state
        if existing.manifest_digest != self.manifest.digest:
            raise RuntimeError("manifest digest mismatch; immutable mission contract changed")
        return existing

    def _persist_transition(
        self,
        state: RunState,
        kind: str,
        payload: dict[str, object],
    ) -> RunState:
        self.store.save_with_event(state, kind, payload, state.updated_at)
        return state

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
            return self._persist_transition(
                stopped,
                "WATCHDOG_STOP",
                {"reason": watchdog.reason},
            )
        if watchdog.action == "REPLAN":
            state = replace(
                state,
                consecutive_failures=0,
                duplicate_count=0,
                last_step_fingerprint=None,
                updated_at=now,
            )
            self._persist_transition(
                state,
                "WATCHDOG_REPLAN",
                {"reason": watchdog.reason},
            )

        try:
            proposal = self.planner(state)
        except Exception as exc:
            now = self.clock()
            elapsed = now - state.started_at
            failed = replace(
                state,
                status=(
                    "STOPPED" if elapsed >= self.manifest.maximum_wall_seconds else state.status
                ),
                step_index=state.step_index + 1,
                consecutive_failures=state.consecutive_failures + 1,
                updated_at=now,
            )
            payload: dict[str, object] = {
                "exception_type": type(exc).__name__,
                "status": failed.status,
            }
            if failed.status == "STOPPED":
                payload["terminal_reason"] = "maximum wall budget exhausted during planning"
            self._persist_transition(failed, "PLANNER_EXCEPTION", payload)
            raise

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
            return self._persist_transition(
                stopped,
                "WATCHDOG_STOP",
                {"reason": watchdog.reason, "phase": "post_planning"},
            )

        allowed, reason = authorize_step(
            proposal,
            allowed_effects=self.manifest.allowed_effects,
            prohibited_effects=self.manifest.prohibited_effects,
        )
        if not allowed:
            blocked = replace(state, status="BLOCKED", updated_at=self.clock())
            return self._persist_transition(
                blocked,
                "STEP_BLOCKED",
                {"fingerprint": proposal.fingerprint, "reason": reason},
            )

        if self.manifest.independent_evaluation_required and self.evaluator is None:
            blocked = replace(state, status="BLOCKED", updated_at=self.clock())
            return self._persist_transition(
                blocked,
                "EVALUATION_BLOCKED",
                {
                    "fingerprint": proposal.fingerprint,
                    "reason": "independent evaluator is required but not configured",
                },
            )

        duplicate_count = (
            state.duplicate_count + 1 if proposal.fingerprint == state.last_step_fingerprint else 0
        )
        try:
            result = self.executor(proposal)
        except Exception as exc:
            now = self.clock()
            failed = replace(
                state,
                step_index=state.step_index + 1,
                consecutive_failures=state.consecutive_failures + 1,
                last_step_fingerprint=proposal.fingerprint,
                duplicate_count=duplicate_count,
                updated_at=now,
            )
            self._persist_transition(
                failed,
                "STEP_EXCEPTION",
                {
                    "fingerprint": proposal.fingerprint,
                    "exception_type": type(exc).__name__,
                    "value": proposal.value,
                },
            )
            raise

        now = self.clock()
        try:
            result_evidence_digest = evidence_digest(result.evidence)
        except (TypeError, ValueError) as exc:
            failed = replace(
                state,
                step_index=state.step_index + 1,
                consecutive_failures=state.consecutive_failures + 1,
                last_step_fingerprint=proposal.fingerprint,
                duplicate_count=duplicate_count,
                updated_at=now,
            )
            self._persist_transition(
                failed,
                "STEP_PERSISTENCE_FAILURE",
                {
                    "fingerprint": proposal.fingerprint,
                    "exception_type": type(exc).__name__,
                    "reason": "step result evidence is not canonical JSON",
                    "value": proposal.value,
                },
            )
            raise RuntimeError("step result evidence is not canonical JSON") from exc

        if self.manifest.evidence_required and not result.evidence:
            blocked = replace(
                state,
                status="BLOCKED",
                step_index=state.step_index + 1,
                last_step_fingerprint=proposal.fingerprint,
                duplicate_count=duplicate_count,
                updated_at=now,
            )
            return self._persist_transition(
                blocked,
                "EVALUATION_BLOCKED",
                {
                    "fingerprint": proposal.fingerprint,
                    "reason": "executor evidence is required but empty",
                    "evidence_digest": result_evidence_digest,
                },
            )

        evaluation: EvaluationResult | None = None
        if self.evaluator is not None:
            try:
                evaluation = self.evaluator(proposal, result)
            except Exception as exc:
                now = self.clock()
                failed = replace(
                    state,
                    step_index=state.step_index + 1,
                    consecutive_failures=state.consecutive_failures + 1,
                    last_step_fingerprint=proposal.fingerprint,
                    duplicate_count=duplicate_count,
                    updated_at=now,
                )
                self._persist_transition(
                    failed,
                    "EVALUATION_EXCEPTION",
                    {
                        "fingerprint": proposal.fingerprint,
                        "exception_type": type(exc).__name__,
                        "evidence_digest": result_evidence_digest,
                    },
                )
                raise

            if not isinstance(evaluation, EvaluationResult):
                blocked = replace(
                    state,
                    status="BLOCKED",
                    step_index=state.step_index + 1,
                    last_step_fingerprint=proposal.fingerprint,
                    duplicate_count=duplicate_count,
                    updated_at=self.clock(),
                )
                return self._persist_transition(
                    blocked,
                    "EVALUATION_INVALID",
                    {
                        "fingerprint": proposal.fingerprint,
                        "reason": "evaluator returned an invalid result type",
                        "evidence_digest": result_evidence_digest,
                    },
                )

            try:
                evaluation.validate(expected_evidence_digest=result_evidence_digest)
            except ValueError as exc:
                blocked = replace(
                    state,
                    status="BLOCKED",
                    step_index=state.step_index + 1,
                    last_step_fingerprint=proposal.fingerprint,
                    duplicate_count=duplicate_count,
                    updated_at=self.clock(),
                )
                return self._persist_transition(
                    blocked,
                    "EVALUATION_INVALID",
                    {
                        "fingerprint": proposal.fingerprint,
                        "reason": str(exc),
                        "evidence_digest": result_evidence_digest,
                    },
                )

        now = self.clock()
        evaluated_score = evaluation.score if evaluation is not None else 0.0
        new_state = replace(
            state,
            step_index=state.step_index + 1,
            consecutive_failures=0 if result.success else state.consecutive_failures + 1,
            last_step_fingerprint=proposal.fingerprint,
            duplicate_count=duplicate_count,
            evaluator_score=max(state.evaluator_score, evaluated_score),
            updated_at=now,
        )

        elapsed = now - new_state.started_at
        terminal_reason: str | None = None
        if elapsed >= self.manifest.maximum_wall_seconds:
            new_state = replace(new_state, status="STOPPED")
            terminal_reason = "maximum wall budget exhausted after evaluation"
        elif (
            result.success
            and evaluation is not None
            and evaluation.verdict == "PASS"
            and evaluation.score >= self.manifest.evaluator_threshold
            and elapsed >= self.manifest.minimum_wall_seconds
        ):
            new_state = replace(new_state, status="COMPLETED")

        payload: dict[str, object] = {
            "fingerprint": proposal.fingerprint,
            "success": result.success,
            "value": proposal.value,
            "evidence": result.evidence,
            "evidence_digest": result_evidence_digest,
            "status": new_state.status,
        }
        if evaluation is not None:
            payload["evaluation"] = evaluation.event_payload()
        if terminal_reason is not None:
            payload["terminal_reason"] = terminal_reason

        try:
            self._persist_transition(new_state, "STEP_RESULT", payload)
        except (TypeError, ValueError) as exc:
            failed = replace(
                state,
                step_index=state.step_index + 1,
                consecutive_failures=state.consecutive_failures + 1,
                last_step_fingerprint=proposal.fingerprint,
                duplicate_count=duplicate_count,
                updated_at=now,
            )
            self._persist_transition(
                failed,
                "STEP_PERSISTENCE_FAILURE",
                {
                    "fingerprint": proposal.fingerprint,
                    "exception_type": type(exc).__name__,
                    "reason": "step result payload is not JSON serializable",
                    "value": proposal.value,
                },
            )
            raise RuntimeError("step result payload is not JSON serializable") from exc
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
