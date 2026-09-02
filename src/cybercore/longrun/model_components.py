from __future__ import annotations

import json
import math

from cybercore.longrun.engine import Evaluator, Executor, Planner, StepResult
from cybercore.longrun.evaluation import EvaluationResult, evidence_digest
from cybercore.longrun.governor import StepProposal
from cybercore.longrun.manifest import LongRunManifest
from cybercore.longrun.provider import (
    ModelRequest,
    ModelRuntime,
    ProviderCallPolicy,
    ProviderCallReceipt,
)
from cybercore.longrun.state import RunState


_MODEL_CALLS_KEY = "_cybercore_model_calls"


def _decode_object(text: str, *, label: str) -> dict[str, object]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must return a JSON object") from exc
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{label} must return a JSON object")
    return value


def _reject_unknown(value: dict[str, object], allowed: set[str], *, label: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"unknown {label} fields: {unknown}")


def _number(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _proposal_payload(proposal: StepProposal) -> dict[str, object]:
    return {
        "fingerprint": proposal.fingerprint,
        "expected_quality_gain": proposal.expected_quality_gain,
        "expected_information_gain": proposal.expected_information_gain,
        "cost": proposal.cost,
        "risk": proposal.risk,
        "duplication_probability": proposal.duplication_probability,
        "effect": proposal.effect,
    }


def _parse_proposal(text: str) -> StepProposal:
    raw = _decode_object(text, label="planner")
    allowed = {
        "fingerprint",
        "expected_quality_gain",
        "expected_information_gain",
        "cost",
        "risk",
        "duplication_probability",
        "effect",
    }
    _reject_unknown(raw, allowed, label="planner response")
    if set(raw) != allowed:
        raise ValueError("planner response is missing required fields")
    return StepProposal(
        fingerprint=_string(raw["fingerprint"], label="planner.fingerprint"),
        expected_quality_gain=_number(
            raw["expected_quality_gain"], label="planner.expected_quality_gain"
        ),
        expected_information_gain=_number(
            raw["expected_information_gain"], label="planner.expected_information_gain"
        ),
        cost=_number(raw["cost"], label="planner.cost"),
        risk=_number(raw["risk"], label="planner.risk"),
        duplication_probability=_number(
            raw["duplication_probability"], label="planner.duplication_probability"
        ),
        effect=_string(raw["effect"], label="planner.effect"),
    )


def _parse_worker(text: str) -> tuple[bool, dict[str, object]]:
    raw = _decode_object(text, label="worker")
    _reject_unknown(raw, {"success", "evidence"}, label="worker response")
    if set(raw) != {"success", "evidence"}:
        raise ValueError("worker response is missing required fields")
    success = raw["success"]
    evidence = raw["evidence"]
    if not isinstance(success, bool):
        raise ValueError("worker.success must be boolean")
    if not isinstance(evidence, dict) or not all(isinstance(key, str) for key in evidence):
        raise ValueError("worker.evidence must be an object with string keys")
    if _MODEL_CALLS_KEY in evidence:
        raise ValueError(f"worker.evidence cannot use reserved key {_MODEL_CALLS_KEY}")
    return success, evidence


def _parse_evaluation(text: str) -> tuple[float, str, tuple[str, ...]]:
    raw = _decode_object(text, label="evaluator")
    _reject_unknown(raw, {"score", "verdict", "reasons"}, label="evaluator response")
    if set(raw) != {"score", "verdict", "reasons"}:
        raise ValueError("evaluator response is missing required fields")
    score = _number(raw["score"], label="evaluator.score")
    verdict = _string(raw["verdict"], label="evaluator.verdict")
    reasons = raw["reasons"]
    if not isinstance(reasons, list) or not reasons or not all(
        isinstance(reason, str) and reason.strip() for reason in reasons
    ):
        raise ValueError("evaluator.reasons must contain non-empty strings")
    return score, verdict, tuple(reason.strip() for reason in reasons)


def provider_components(
    manifest: LongRunManifest,
    runtime: ModelRuntime,
    *,
    call_policy: ProviderCallPolicy | None = None,
) -> tuple[Planner, Executor, Evaluator]:
    manifest.validate()
    planner_binding = manifest.model_binding("planner")
    worker_binding = manifest.model_binding("worker")
    evaluator_binding = manifest.model_binding("evaluator")
    if planner_binding is None or worker_binding is None or evaluator_binding is None:
        raise ValueError("provider-bound runtime requires planner, worker, and evaluator bindings")
    if evaluator_binding.binding_id in {planner_binding.binding_id, worker_binding.binding_id}:
        raise ValueError("independent evaluator must use a distinct binding identity")

    policy = call_policy or ProviderCallPolicy()
    policy.validate()
    pending_planner: tuple[str, ProviderCallReceipt] | None = None

    def planner(state: RunState) -> StepProposal:
        nonlocal pending_planner
        request = ModelRequest(
            request_id=f"{manifest.run_id}:planner:{state.step_index}",
            role="planner",
            payload={
                "objective": manifest.objective,
                "state": {
                    "step_index": state.step_index,
                    "consecutive_failures": state.consecutive_failures,
                    "last_step_fingerprint": state.last_step_fingerprint,
                    "duplicate_count": state.duplicate_count,
                    "evaluator_score": state.evaluator_score,
                },
                "contract": {
                    "allowed_effects": list(manifest.allowed_effects),
                    "prohibited_effects": list(manifest.prohibited_effects),
                },
            },
        )
        call = runtime.call(planner_binding, request, policy=policy)
        proposal = _parse_proposal(call.response.output_text)
        pending_planner = (proposal.fingerprint, call.receipt)
        return proposal

    def executor(proposal: StepProposal) -> StepResult:
        nonlocal pending_planner
        if pending_planner is None or pending_planner[0] != proposal.fingerprint:
            raise RuntimeError("worker call has no matching provider planner receipt")
        planner_receipt = pending_planner[1]
        pending_planner = None
        request = ModelRequest(
            request_id=planner_receipt.request_id.replace(":planner:", ":worker:", 1),
            role="worker",
            payload={
                "objective": manifest.objective,
                "proposal": _proposal_payload(proposal),
            },
        )
        call = runtime.call(worker_binding, request, policy=policy)
        success, evidence = _parse_worker(call.response.output_text)
        evidence = dict(evidence)
        evidence[_MODEL_CALLS_KEY] = [
            planner_receipt.event_payload(),
            call.receipt.event_payload(),
        ]
        return StepResult(success=success, evidence=evidence)

    def evaluator(proposal: StepProposal, result: StepResult) -> EvaluationResult:
        result_digest = evidence_digest(result.evidence)
        request = ModelRequest(
            request_id=f"{manifest.run_id}:evaluator:{result_digest[:24]}",
            role="evaluator",
            payload={
                "objective": manifest.objective,
                "proposal": _proposal_payload(proposal),
                "execution": {
                    "success": result.success,
                    "evidence": result.evidence,
                    "evidence_digest": result_digest,
                },
            },
        )
        call = runtime.call(evaluator_binding, request, policy=policy)
        score, verdict, reasons = _parse_evaluation(call.response.output_text)
        return EvaluationResult(
            evaluator_id=evaluator_binding.identity,
            evaluator_version="provider-binding-v1",
            score=score,
            verdict=verdict,
            reasons=reasons,
            evidence_digest=result_digest,
            metadata={"provider_receipt": call.receipt.event_payload()},
        )

    return planner, executor, evaluator
