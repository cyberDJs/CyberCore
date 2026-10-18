# ADR-0014 — Governed Action Kernel integration (proposal)

Status: Proposed
Tracking: #118
Date: 2026-10-18

## Context

CyberCore already has a deny-by-default MCP registry and trusted CyberDJs Room broker (ADR-0013). The existing `execution/policy.py` applies narrowly to the Vikunja WB-0037 target, and is not a general-purpose authorization engine. CyberHIVE ADR-0015 provides a typed local NodeAgent/NodeActionDispatcher, not network enrollment or a remote command facility. Nexus has capability, provenance and receipt contracts.

## Decision

Add a small, provider-neutral **Action Kernel** as an additive and separately feature-gated vertical slice:

```text
authenticated ingress -> TaskRequest -> capability lookup -> policy gate
  -> local read-only dispatcher -> ExecutionReceipt -> canonical evidence
```

The trusted actor comes from the transport/backend, never from model-supplied payload. Preserve ADR-0013's single room-ledger writer and event identity boundaries.

### Wire contracts (v0)

- `TaskRequest`: `schema_version`, `task_id`, `correlation_id`, `capability_name`, `target_id`, `arguments`, `expires_at`, `requested_by` (server-populated).
- `CapabilityDescriptor`: versioned name, input and output schemas, target restrictions, `effect_class`, timeout and evidence-size limits.
- `PolicyVerdict`: allowed/denied, stable reason code, required approval class, policy version.
- `ExecutionReceipt`: task and correlation references, capability version, status, start/finish timestamps, redacted evidence hash and provenance.
- Define canonical field names only after contract comparison against existing Nexus and CyberHIVE implementations. This section is conceptual, not a declaration of finalized schema compatibility.

### Initial capability set

Only explicitly allowlisted local read-only synthetic diagnostics / target-resolution / bounded port checks. The target set is preconfigured and cannot be arbitrary model-provided hostnames or IPs. No generic shell, filesystem, deployment changes, network listener, secret expansion, or direct production SSH.

### Security invariants

1. Fail closed on invalid identity, unsupported capability, schema error, missing target, timeout or unavailable backend.
2. Model output is an untrusted proposed request, not an authorization decision.
3. Actor identity binding, approval, target allowlist, idempotency and deadline are enforced outside the model.
4. Secrets and unsafe output fields are recursively redacted before they enter any model context or evidence ledger.
5. Every execution produces a bounded structured receipt; append evidence through the existing single-writer backend only.
6. No autonomous merge or production mutation from this work block.
7. Prefer Linux-only CI for platform-independent validation.

## Delivery sequence

1. Inventory existing CyberCore/CyberHIVE/Nexus schemas, dependencies and tests.
2. Add contract compatibility tests and explicitly versioned schemas.
3. Implement minimal local mock/stub dispatcher plus policy and evidence adapter.
4. Negative tests: spoofed actor, unknown tool, arbitrary target, malformed/oversized data, deadline, secrets, duplicate task and backend unavailable.
5. Draft PR + CI + security review. Defer remote enrollment and GPT-Live integration behind separate approvals and feature flags.

## Follow-ups

- Secure remote node transport/enrollment (separate ADR and security review).
- GPT-Live client-delegation adapter (text-first kernel must be independently usable).
- Repository-allowlisted code agent producing draft PRs.
- Controlled changes under signed MOP and human approval.

## Rollback

Disable the Action Kernel feature flag and remove its read-only MCP registration. Keep canonical ledger and already written receipts intact. Do not change existing CyberDJs Room broker behavior.
