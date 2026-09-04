# ADR-0008: Provider and Model Binding for LongRun

Status: PROPOSED

## Context

WB-LR0003 established a durable LongRun engine with separate planner, executor, and
independent evaluator callbacks. The operator runtime still uses only deterministic local
repository reads. LongRun therefore needs a provider-neutral model contract before any live
provider, credential, or paid inference can be enabled.

## Decision

LongRun binds model identity into the immutable mission manifest using `ModelBinding` values.
Each binding contains only:

- `binding_id`
- `role` (`planner`, `worker`, or `evaluator`)
- `provider_id`
- `model_id`

Credential values, API keys, tokens, endpoint secrets, and billing identifiers are prohibited
from this binding schema. A future live adapter must obtain credentials from an approved runtime
secret source outside the mission file and append-only event ledger.

A provider adapter is registered against one exact `ModelBinding`. Resolution fails closed if an
adapter's provider or model identity differs from the immutable binding.

`ModelRuntime` owns bounded call policy and receipt generation. The provider adapter receives the
request plus an explicit per-attempt timeout. Only explicitly retryable `ProviderError` failures
are retried, and retries are capped by `max_attempts`.

Every successful call emits a digest-bound receipt containing provider/model/binding identity,
request ID, request digest, response digest, attempt count, latency, usage counters, finish reason,
and a receipt digest. Raw request payloads and raw model outputs are not copied into receipts.

`provider_components()` creates provider-backed planner, worker, and evaluator callbacks for the
existing `LongRunEngine`. Planner and worker call receipts are embedded in executor evidence. The
evaluator call receipt is embedded in evaluation metadata and is therefore covered by the
`EvaluationResult` digest.

The default CLI deterministic engine refuses missions that contain model bindings. WB-LR0004 does
not enable live provider execution from the CLI.

## Independence boundary

The evaluator must use a distinct logical binding identity from planner and worker. This is
structural separation, not proof of an independent trust domain. A later live-runtime decision
must decide whether evaluator independence also requires a different provider, account, region,
or model family.

## Failure behavior

- unknown binding fields fail closed;
- credential-like extra fields are rejected as unknown schema;
- missing planner/worker/evaluator bindings block provider component construction;
- adapter identity drift fails closed;
- request role mismatch fails closed;
- malformed provider JSON fails closed;
- non-retryable provider errors are never retried;
- retryable errors stop at the configured maximum attempt count;
- worker evidence cannot overwrite the reserved CyberCore model-call receipt key;
- model-bound missions cannot silently fall back to deterministic CLI execution.

## Security boundary

WB-LR0004 adds no provider SDK, network transport, credential loading, production write, billing
mutation, permission mutation, deployment, or runtime promotion. Live inference requires a
separate approval gate and a concrete adapter with explicit egress, secret handling, rate-limit,
timeout, and cost controls.

## Acceptance sequence

1. scripted provider unit tests;
2. full repository CI and CodeQL;
3. separate approval for a live provider adapter and credentials;
4. one-request smoke test;
5. five-step smoke test;
6. 30-minute endurance run;
7. 2-hour endurance run;
8. MARATHON-001 16-hour acceptance.
