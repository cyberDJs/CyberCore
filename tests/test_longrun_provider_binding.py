from __future__ import annotations

from pathlib import Path

import pytest

from cybercore.longrun.evaluation import EvaluationResult, evidence_digest
from cybercore.longrun.loader import load_manifest
from cybercore.longrun.manifest import LongRunManifest
from cybercore.longrun.model_components import provider_components
from cybercore.longrun.provider import (
    ModelBinding,
    ModelRequest,
    ModelResponse,
    ModelRuntime,
    ProviderCallPolicy,
    ProviderError,
    ProviderRegistry,
)
from cybercore.longrun.state import RunState


class ScriptedProvider:
    def __init__(self, binding: ModelBinding, responses: list[object]) -> None:
        self._binding = binding
        self.responses = list(responses)
        self.requests: list[ModelRequest] = []
        self.timeouts: list[float] = []

    @property
    def binding(self) -> ModelBinding:
        return self._binding

    def invoke(self, request: ModelRequest, *, timeout_seconds: float) -> ModelResponse:
        self.requests.append(request)
        self.timeouts.append(timeout_seconds)
        if not self.responses:
            raise AssertionError("scripted provider exhausted")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        assert isinstance(response, ModelResponse)
        return response


def _binding(role: str, *, model: str | None = None) -> ModelBinding:
    return ModelBinding(
        binding_id=f"{role}-binding",
        role=role,
        provider_id="mock-provider",
        model_id=model or f"mock-{role}-model",
    )


def _manifest(**overrides) -> LongRunManifest:
    values = {
        "run_id": "provider-test",
        "objective": "prove provider-bound LongRun behavior",
        "minimum_wall_seconds": 0,
        "maximum_wall_seconds": 3600,
        "model_bindings": (
            _binding("planner"),
            _binding("worker"),
            _binding("evaluator"),
        ),
    }
    values.update(overrides)
    return LongRunManifest(**values)


def test_manifest_digest_binds_provider_and_model_identity():
    first = _manifest()
    changed = _manifest(
        model_bindings=(
            _binding("planner", model="planner-v2"),
            _binding("worker"),
            _binding("evaluator"),
        )
    )

    assert first.digest != changed.digest
    assert first.model_binding("planner") is not None
    assert first.model_binding("planner").model_id == "mock-planner-model"


def test_manifest_rejects_duplicate_model_roles():
    manifest = _manifest(
        model_bindings=(
            _binding("planner"),
            ModelBinding("planner-2", "planner", "mock-provider", "other-model"),
            _binding("worker"),
            _binding("evaluator"),
        )
    )

    with pytest.raises(ValueError, match="duplicate model binding role"):
        manifest.validate()


def test_loader_rejects_secret_or_unknown_binding_fields(tmp_path: Path):
    profile = tmp_path / "profile.yaml"
    profile.write_text(
        """version: 0
profile: test
minimum_wall_seconds: 0
maximum_wall_seconds: 60
evaluator_threshold: 0.95
checkpoint_every_steps: 1
max_consecutive_failures: 3
max_duplicate_steps: 2
allowed_effects: [read, sandbox_write]
prohibited_effects: [production_write, credential_mutation, billing_mutation, permission_mutation]
policy:
  evidence_required: true
  independent_evaluation_required: true
  immutable_mission_required: true
  fail_closed_on_unknown_effect: true
""",
        encoding="utf-8",
    )
    mission = tmp_path / "mission.yaml"
    mission.write_text(
        """version: 0
run_id: provider-test
objective: reject secrets from immutable provider binding
model_bindings:
  - binding_id: planner-binding
    role: planner
    provider_id: mock-provider
    model_id: mock-model
    credential_env: SHOULD_NOT_BE_ACCEPTED
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown mission.model_bindings"):
        load_manifest(profile, mission)


def test_runtime_retries_retryable_errors_and_receipt_contains_only_digests_and_usage():
    binding = _binding("planner")
    provider = ScriptedProvider(
        binding,
        [
            ProviderError("rate_limit", "retry", retryable=True),
            ModelResponse(
                request_id="run:planner:0",
                output_text='{"ok":true}',
                response_id="response-1",
                usage={"input_tokens": 12, "output_tokens": 3},
            ),
        ],
    )
    registry = ProviderRegistry()
    registry.register(provider)
    times = iter([10.0, 10.025])
    runtime = ModelRuntime(registry, clock=lambda: next(times))
    request = ModelRequest(
        request_id="run:planner:0",
        role="planner",
        payload={"prompt": "sensitive prompt body is not a receipt field"},
    )

    call = runtime.call(
        binding,
        request,
        policy=ProviderCallPolicy(timeout_seconds=12, max_attempts=2),
    )

    assert len(provider.requests) == 2
    assert provider.timeouts == [12.0, 12.0]
    assert call.receipt.attempts == 2
    assert call.receipt.latency_ms == pytest.approx(25.0)
    receipt_text = str(call.receipt.event_payload())
    assert "mock-provider" in receipt_text
    assert "mock-planner-model" in receipt_text
    assert "sensitive prompt body" not in receipt_text
    assert call.receipt.usage == {"input_tokens": 12, "output_tokens": 3}


def test_runtime_does_not_retry_nonretryable_errors():
    binding = _binding("worker")
    provider = ScriptedProvider(
        binding,
        [
            ProviderError("invalid_request", "bad payload", retryable=False),
            ModelResponse(request_id="run:worker:0", output_text="unused"),
        ],
    )
    registry = ProviderRegistry()
    registry.register(provider)
    runtime = ModelRuntime(registry)

    with pytest.raises(ProviderError, match="bad payload"):
        runtime.call(
            binding,
            ModelRequest("run:worker:0", "worker", {"task": "x"}),
            policy=ProviderCallPolicy(max_attempts=3),
        )

    assert len(provider.requests) == 1


def test_registry_fails_closed_on_binding_identity_drift():
    binding = _binding("planner")
    registry = ProviderRegistry()
    registry.register(ScriptedProvider(binding, []))
    changed = ModelBinding(
        binding_id=binding.binding_id,
        role=binding.role,
        provider_id=binding.provider_id,
        model_id="changed-model",
    )

    with pytest.raises(RuntimeError, match="immutable model binding"):
        registry.resolve(changed)


def test_provider_components_emit_planner_worker_and_evaluator_receipts():
    manifest = _manifest()
    planner_binding = manifest.model_binding("planner")
    worker_binding = manifest.model_binding("worker")
    evaluator_binding = manifest.model_binding("evaluator")
    assert planner_binding and worker_binding and evaluator_binding

    planner_provider = ScriptedProvider(
        planner_binding,
        [
            ModelResponse(
                request_id="provider-test:planner:0",
                output_text=(
                    '{"fingerprint":"step-1","expected_quality_gain":1.0,'
                    '"expected_information_gain":1.0,"cost":0.1,"risk":0.1,'
                    '"duplication_probability":0.0,"effect":"read"}'
                ),
                usage={"input_tokens": 10, "output_tokens": 10},
            )
        ],
    )
    worker_provider = ScriptedProvider(
        worker_binding,
        [
            ModelResponse(
                request_id="provider-test:worker:0",
                output_text='{"success":true,"evidence":{"artifact":"verified"}}',
                usage={"input_tokens": 9, "output_tokens": 5},
            )
        ],
    )
    registry = ProviderRegistry()
    registry.register(planner_provider)
    registry.register(worker_provider)
    runtime = ModelRuntime(registry)
    planner, executor, evaluator = provider_components(manifest, runtime)

    state = RunState(
        run_id=manifest.run_id,
        manifest_digest=manifest.digest,
        status="RUNNING",
        step_index=0,
        consecutive_failures=0,
        last_step_fingerprint=None,
        duplicate_count=0,
        evaluator_score=0.0,
        started_at=0.0,
        updated_at=0.0,
    )
    proposal = planner(state)
    result = executor(proposal)
    assert result.success is True
    assert result.evidence["artifact"] == "verified"
    calls = result.evidence["_cybercore_model_calls"]
    assert isinstance(calls, list)
    assert len(calls) == 2

    result_digest = evidence_digest(result.evidence)
    evaluator_provider = ScriptedProvider(
        evaluator_binding,
        [
            ModelResponse(
                request_id=f"provider-test:evaluator:{result_digest[:24]}",
                output_text='{"score":0.97,"verdict":"PASS","reasons":["verified"]}',
                usage={"input_tokens": 14, "output_tokens": 4},
            )
        ],
    )
    registry.register(evaluator_provider)
    evaluation = evaluator(proposal, result)

    evaluation.validate(expected_evidence_digest=result_digest)
    assert evaluation.verdict == "PASS"
    assert evaluation.score == pytest.approx(0.97)
    evaluator_receipt = evaluation.metadata["provider_receipt"]
    assert isinstance(evaluator_receipt, dict)
    assert evaluator_receipt["binding"]["role"] == "evaluator"
    assert evaluator_receipt["usage"]["input_tokens"] == 14


def test_evaluation_rejects_non_string_reasons_fail_closed():
    evaluation = EvaluationResult(
        evaluator_id="judge",
        evaluator_version="1",
        score=1.0,
        verdict="PASS",
        reasons=(123,),  # type: ignore[arg-type]
        evidence_digest="abc",
    )

    with pytest.raises(ValueError, match="reasons"):
        evaluation.validate(expected_evidence_digest="abc")


def test_runtime_cancellation_stops_before_provider_invocation():
    binding = _binding("worker")
    provider = ScriptedProvider(
        binding,
        [ModelResponse(request_id="run:worker:0", output_text="unused")],
    )
    registry = ProviderRegistry()
    registry.register(provider)
    runtime = ModelRuntime(registry)

    with pytest.raises(ProviderError, match="cancelled"):
        runtime.call(
            binding,
            ModelRequest("run:worker:0", "worker", {"task": "x"}),
            cancelled=lambda: True,
        )

    assert provider.requests == []


def test_provider_components_reject_nonfinite_planner_numbers():
    manifest = _manifest()
    planner_binding = manifest.model_binding("planner")
    worker_binding = manifest.model_binding("worker")
    evaluator_binding = manifest.model_binding("evaluator")
    assert planner_binding and worker_binding and evaluator_binding
    registry = ProviderRegistry()
    registry.register(
        ScriptedProvider(
            planner_binding,
            [
                ModelResponse(
                    request_id="provider-test:planner:0",
                    output_text=(
                        '{"fingerprint":"step-1","expected_quality_gain":NaN,'
                        '"expected_information_gain":1.0,"cost":0.1,"risk":0.1,'
                        '"duplication_probability":0.0,"effect":"read"}'
                    ),
                )
            ],
        )
    )
    registry.register(ScriptedProvider(worker_binding, []))
    registry.register(ScriptedProvider(evaluator_binding, []))
    runtime = ModelRuntime(registry)
    planner, _, _ = provider_components(manifest, runtime)
    state = RunState(
        run_id=manifest.run_id,
        manifest_digest=manifest.digest,
        status="RUNNING",
        step_index=0,
        consecutive_failures=0,
        last_step_fingerprint=None,
        duplicate_count=0,
        evaluator_score=0.0,
        started_at=0.0,
        updated_at=0.0,
    )

    with pytest.raises(ValueError, match="finite"):
        planner(state)
