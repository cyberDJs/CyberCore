from __future__ import annotations

from dataclasses import dataclass

from cybercore.longrun.engine import LongRunEngine, StepResult
from cybercore.longrun.evaluation import EvaluationResult, evidence_digest
from cybercore.longrun.governor import StepProposal
from cybercore.longrun.manifest import LongRunManifest
from cybercore.longrun.state import LongRunStateStore, RunState


@dataclass(slots=True)
class SimulatedClock:
    now: float = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float = 1.0) -> float:
        if seconds < 0:
            raise ValueError("simulated clock cannot move backwards")
        self.now += seconds
        return self.now


@dataclass(slots=True)
class AcceleratedAcceptanceHarness:
    clock: SimulatedClock
    crash_once_at_step: int | None = None
    evaluator_score: float = 1.0
    evaluator_verdict: str = "PASS"
    _crash_injected: bool = False

    def engine(self, manifest: LongRunManifest, store: LongRunStateStore) -> LongRunEngine:
        def planner(state: RunState) -> StepProposal:
            self.clock.advance()
            return StepProposal(
                fingerprint=f"acceptance-step-{state.step_index}",
                expected_quality_gain=1.0,
                expected_information_gain=1.0,
                cost=0.01,
                risk=0.01,
                duplication_probability=0.0,
                effect="read",
            )

        def executor(proposal: StepProposal) -> StepResult:
            self.clock.advance()
            step_index = int(proposal.fingerprint.rsplit("-", 1)[1])
            if (
                self.crash_once_at_step is not None
                and step_index == self.crash_once_at_step
                and not self._crash_injected
            ):
                self._crash_injected = True
                raise RuntimeError("accelerated acceptance crash injection")
            return StepResult(
                success=True,
                evidence={
                    "harness": "accelerated-longrun-acceptance",
                    "fingerprint": proposal.fingerprint,
                    "simulated_time": self.clock.now,
                },
            )

        def evaluator(proposal: StepProposal, result: StepResult) -> EvaluationResult:
            self.clock.advance()
            return EvaluationResult(
                evaluator_id="cybercore.accelerated-acceptance-judge",
                evaluator_version="1",
                score=self.evaluator_score,
                verdict=self.evaluator_verdict,
                reasons=(
                    f"evaluated {proposal.fingerprint} from deterministic acceptance evidence",
                ),
                evidence_digest=evidence_digest(result.evidence),
            )

        return LongRunEngine(
            manifest,
            store,
            planner=planner,
            executor=executor,
            evaluator=evaluator,
            clock=self.clock,
        )
