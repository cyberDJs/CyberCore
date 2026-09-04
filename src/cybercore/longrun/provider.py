from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import math
import time
from typing import Callable, Protocol


_ALLOWED_ROLES = {"planner", "worker", "evaluator"}


def _canonical_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _validate_json_object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{label} must be an object with string keys")
    try:
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain canonical JSON values") from exc
    return value


@dataclass(frozen=True, slots=True)
class ModelBinding:
    binding_id: str
    role: str
    provider_id: str
    model_id: str

    def validate(self) -> None:
        for label, value in (
            ("binding_id", self.binding_id),
            ("provider_id", self.provider_id),
            ("model_id", self.model_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"model binding {label} must be a non-empty string")
        if self.role not in _ALLOWED_ROLES:
            raise ValueError(f"model binding role must be one of {sorted(_ALLOWED_ROLES)}")

    @property
    def identity(self) -> str:
        self.validate()
        return f"{self.provider_id}:{self.model_id}:{self.binding_id}"

    def canonical_payload(self) -> dict[str, str]:
        self.validate()
        return {
            "binding_id": self.binding_id,
            "role": self.role,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
        }


@dataclass(frozen=True, slots=True)
class ProviderCallPolicy:
    timeout_seconds: float = 60.0
    max_attempts: int = 3

    def validate(self) -> None:
        if isinstance(self.timeout_seconds, bool) or not isinstance(
            self.timeout_seconds, (int, float)
        ):
            raise ValueError("provider timeout_seconds must be numeric")
        if not math.isfinite(float(self.timeout_seconds)):
            raise ValueError("provider timeout_seconds must be finite")
        if self.timeout_seconds <= 0 or self.timeout_seconds > 600:
            raise ValueError("provider timeout_seconds must be between 0 and 600")
        if isinstance(self.max_attempts, bool) or not isinstance(self.max_attempts, int):
            raise ValueError("provider max_attempts must be an integer")
        if self.max_attempts < 1 or self.max_attempts > 10:
            raise ValueError("provider max_attempts must be between 1 and 10")

    def canonical_payload(self) -> dict[str, object]:
        self.validate()
        return {
            "timeout_seconds": float(self.timeout_seconds),
            "max_attempts": self.max_attempts,
        }


@dataclass(frozen=True, slots=True)
class ModelRequest:
    request_id: str
    role: str
    payload: dict[str, object]

    def validate(self) -> None:
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise ValueError("model request_id must be a non-empty string")
        if self.role not in _ALLOWED_ROLES:
            raise ValueError(f"model request role must be one of {sorted(_ALLOWED_ROLES)}")
        _validate_json_object(self.payload, label="model request payload")

    @property
    def digest(self) -> str:
        self.validate()
        return _canonical_digest(
            {
                "request_id": self.request_id,
                "role": self.role,
                "payload": self.payload,
            }
        )


@dataclass(frozen=True, slots=True)
class ModelResponse:
    request_id: str
    output_text: str
    response_id: str = ""
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)

    def validate(self, *, expected_request_id: str) -> None:
        if self.request_id != expected_request_id:
            raise ValueError("model response request_id does not match request")
        if not isinstance(self.output_text, str):
            raise ValueError("model response output_text must be a string")
        if not isinstance(self.response_id, str) or not isinstance(self.finish_reason, str):
            raise ValueError("model response identifiers must be strings")
        if not isinstance(self.usage, dict) or not all(
            isinstance(key, str)
            and isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 0
            for key, value in self.usage.items()
        ):
            raise ValueError("model response usage must contain non-negative integer counters")

    def canonical_payload(self) -> dict[str, object]:
        self.validate(expected_request_id=self.request_id)
        return {
            "request_id": self.request_id,
            "output_text": self.output_text,
            "response_id": self.response_id,
            "finish_reason": self.finish_reason,
            "usage": dict(sorted(self.usage.items())),
        }

    @property
    def digest(self) -> str:
        return _canonical_digest(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ProviderCallReceipt:
    binding: ModelBinding
    request_id: str
    request_digest: str
    response_digest: str
    attempts: int
    latency_ms: float
    usage: dict[str, int]
    finish_reason: str

    def validate(self) -> None:
        self.binding.validate()
        if not self.request_id.strip() or not self.request_digest or not self.response_digest:
            raise ValueError("provider receipt request identity and digests are required")
        if self.attempts < 1:
            raise ValueError("provider receipt attempts must be >= 1")
        if not math.isfinite(float(self.latency_ms)) or self.latency_ms < 0:
            raise ValueError("provider receipt latency must be finite and non-negative")
        if not all(
            isinstance(key, str)
            and isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 0
            for key, value in self.usage.items()
        ):
            raise ValueError("provider receipt usage must contain non-negative integer counters")

    def canonical_payload(self) -> dict[str, object]:
        self.validate()
        return {
            "binding": self.binding.canonical_payload(),
            "request_id": self.request_id,
            "request_digest": self.request_digest,
            "response_digest": self.response_digest,
            "attempts": self.attempts,
            "latency_ms": round(float(self.latency_ms), 3),
            "usage": dict(sorted(self.usage.items())),
            "finish_reason": self.finish_reason,
        }

    @property
    def digest(self) -> str:
        return _canonical_digest(self.canonical_payload())

    def event_payload(self) -> dict[str, object]:
        payload = self.canonical_payload()
        payload["receipt_digest"] = self.digest
        return payload


@dataclass(frozen=True, slots=True)
class ProviderCall:
    response: ModelResponse
    receipt: ProviderCallReceipt


class ProviderError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        if not code.strip():
            raise ValueError("provider error code is required")
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class ModelProvider(Protocol):
    @property
    def binding(self) -> ModelBinding: ...

    def invoke(self, request: ModelRequest, *, timeout_seconds: float) -> ModelResponse: ...


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}

    def register(self, provider: ModelProvider) -> None:
        binding = provider.binding
        binding.validate()
        if binding.binding_id in self._providers:
            raise ValueError(f"duplicate provider binding_id: {binding.binding_id}")
        self._providers[binding.binding_id] = provider

    def resolve(self, binding: ModelBinding) -> ModelProvider:
        binding.validate()
        provider = self._providers.get(binding.binding_id)
        if provider is None:
            raise LookupError(f"provider binding is not registered: {binding.binding_id}")
        if provider.binding != binding:
            raise RuntimeError(
                "registered provider identity does not match immutable model binding"
            )
        return provider


Clock = Callable[[], float]
CancellationCheck = Callable[[], bool]


class ModelRuntime:
    def __init__(self, registry: ProviderRegistry, *, clock: Clock = time.monotonic) -> None:
        self.registry = registry
        self.clock = clock

    def call(
        self,
        binding: ModelBinding,
        request: ModelRequest,
        *,
        policy: ProviderCallPolicy | None = None,
        cancelled: CancellationCheck | None = None,
    ) -> ProviderCall:
        binding.validate()
        request.validate()
        if request.role != binding.role:
            raise ValueError("model request role does not match immutable binding role")
        call_policy = policy or ProviderCallPolicy()
        call_policy.validate()
        provider = self.registry.resolve(binding)
        started = self.clock()
        attempts = 0
        while True:
            if cancelled is not None and cancelled():
                raise ProviderError("cancelled", "provider call cancelled", retryable=False)
            attempts += 1
            try:
                response = provider.invoke(
                    request,
                    timeout_seconds=float(call_policy.timeout_seconds),
                )
                break
            except ProviderError as exc:
                if not exc.retryable or attempts >= call_policy.max_attempts:
                    raise
        response.validate(expected_request_id=request.request_id)
        finished = self.clock()
        latency_ms = max(0.0, (finished - started) * 1000.0)
        receipt = ProviderCallReceipt(
            binding=binding,
            request_id=request.request_id,
            request_digest=request.digest,
            response_digest=response.digest,
            attempts=attempts,
            latency_ms=latency_ms,
            usage=dict(response.usage),
            finish_reason=response.finish_reason,
        )
        receipt.validate()
        return ProviderCall(response=response, receipt=receipt)
