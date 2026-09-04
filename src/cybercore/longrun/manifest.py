from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json

from cybercore.longrun.provider import ModelBinding


@dataclass(frozen=True, slots=True)
class LongRunManifest:
    run_id: str
    objective: str
    minimum_wall_seconds: int
    maximum_wall_seconds: int
    evaluator_threshold: float = 0.95
    checkpoint_every_steps: int = 1
    max_consecutive_failures: int = 3
    max_duplicate_steps: int = 2
    evidence_required: bool = True
    independent_evaluation_required: bool = True
    allowed_effects: tuple[str, ...] = ("read", "sandbox_write")
    prohibited_effects: tuple[str, ...] = (
        "production_write",
        "credential_mutation",
        "billing_mutation",
        "permission_mutation",
    )
    model_bindings: tuple[ModelBinding, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.run_id.strip() or not self.objective.strip():
            raise ValueError("run_id and objective are required")
        if self.minimum_wall_seconds < 0:
            raise ValueError("minimum_wall_seconds must be non-negative")
        if self.maximum_wall_seconds <= 0:
            raise ValueError("maximum_wall_seconds must be positive")
        if self.minimum_wall_seconds > self.maximum_wall_seconds:
            raise ValueError("minimum wall budget cannot exceed maximum")
        if not 0.0 <= self.evaluator_threshold <= 1.0:
            raise ValueError("evaluator_threshold must be between 0 and 1")
        if self.checkpoint_every_steps < 1:
            raise ValueError("checkpoint_every_steps must be >= 1")
        if self.max_consecutive_failures < 1 or self.max_duplicate_steps < 1:
            raise ValueError("failure and duplicate limits must be >= 1")
        if not isinstance(self.evidence_required, bool):
            raise ValueError("evidence_required must be boolean")
        if not isinstance(self.independent_evaluation_required, bool):
            raise ValueError("independent_evaluation_required must be boolean")
        overlap = set(self.allowed_effects).intersection(self.prohibited_effects)
        if overlap:
            raise ValueError(f"effects cannot be both allowed and prohibited: {sorted(overlap)}")

        roles: set[str] = set()
        binding_ids: set[str] = set()
        for binding in self.model_bindings:
            if not isinstance(binding, ModelBinding):
                raise ValueError("model_bindings must contain ModelBinding values")
            binding.validate()
            if binding.role in roles:
                raise ValueError(f"duplicate model binding role: {binding.role}")
            if binding.binding_id in binding_ids:
                raise ValueError(f"duplicate model binding_id: {binding.binding_id}")
            roles.add(binding.role)
            binding_ids.add(binding.binding_id)

    def model_binding(self, role: str) -> ModelBinding | None:
        self.validate()
        for binding in self.model_bindings:
            if binding.role == role:
                return binding
        return None

    def canonical_payload(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "objective": self.objective,
            "minimum_wall_seconds": self.minimum_wall_seconds,
            "maximum_wall_seconds": self.maximum_wall_seconds,
            "evaluator_threshold": self.evaluator_threshold,
            "checkpoint_every_steps": self.checkpoint_every_steps,
            "max_consecutive_failures": self.max_consecutive_failures,
            "max_duplicate_steps": self.max_duplicate_steps,
            "evidence_required": self.evidence_required,
            "independent_evaluation_required": self.independent_evaluation_required,
            "allowed_effects": list(self.allowed_effects),
            "prohibited_effects": list(self.prohibited_effects),
            "model_bindings": [
                binding.canonical_payload()
                for binding in sorted(
                    self.model_bindings,
                    key=lambda item: (item.role, item.binding_id),
                )
            ],
            "metadata": dict(sorted(self.metadata.items())),
        }

    @property
    def digest(self) -> str:
        self.validate()
        encoded = json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return sha256(encoded).hexdigest()
