---
id: CCL-0001
type: language-specification
title: CyberCore Canonical Language — Core Vocabulary
status: draft
version: 0.1.0
owner: CyberCore
created: 2026-07-28
updated: 2026-07-28
architecture: docs/architecture/reference-architecture-v2.md
genome: docs/audits/cybercore-genome.v0.yaml
---

# CyberCore Canonical Language — Core Vocabulary

## 1. Purpose

CyberCore Canonical Language (CCL) defines the domain terms used across the Evidence Runtime, providers, knowledge layer, decision layer, mutation layer, CLI, APIs, reports, demos, tests, and AI-assisted workflows.

CCL is normative. Implementations may add internal detail, but they must not silently redefine a canonical term.

## 2. Core lifecycle

```text
Provider / Observer
  -> Observation
  -> Evidence
  -> Entity + Claim + Relationship
  -> Knowledge State
  -> Finding + Policy Evaluation
  -> Decision Candidate
  -> Mutation Plan
  -> Approval
  -> Apply Result
  -> Verification Observation
```

## 3. Global language rules

1. Unknown is a valid state and must not be converted into certainty.
2. Assumptions are not evidence.
3. Evidence requires provenance and observation time.
4. Contradictions are preserved and reported.
5. Decisions must remain traceable to supporting evidence.
6. Mutation requires explicit approval bound to a specific plan revision.
7. Mutation results must be observed again.
8. Provider-specific names must not replace canonical domain terms.
9. Public artifacts must not contain secrets or prohibited production details.
10. Identifiers must be stable, machine-readable, and unambiguous within their namespace.

## 4. Canonical terms

### 4.1 Source

A system, actor, document, interface, sensor, API, command, repository, or other origin from which an observation is obtained.

Required properties:

- `source_id`
- `source_type`
- `authority`
- `classification`

A Source does not become trustworthy merely because it exists. Trust is expressed separately through evidence quality, confidence, and policy.

### 4.2 Provider

An adapter that communicates with an external system and exposes declared capabilities.

A Provider may observe reality and may execute an approved mutation. It must not independently define knowledge, approve its own mutation, or bypass governance.

Required properties:

- `provider_id`
- `provider_type`
- `capabilities`
- `mode`: `read_only | mutation_capable`
- `configuration_reference`

### 4.3 Observation

A raw or minimally normalized result obtained from a Source at a specific time.

Required properties:

- `observation_id`
- `source_id`
- `observed_at`
- `payload`
- `payload_type`
- `collection_method`

Lifecycle:

```text
collected -> validated | rejected -> transformed_to_evidence
```

An Observation is not automatically Evidence.

### 4.4 Evidence

A traceable, validated record derived from an Observation and suitable for supporting or challenging a Claim.

Required properties:

- `evidence_id`
- `observation_id`
- `source_id`
- `observed_at`
- `recorded_at`
- `classification`
- `freshness`
- `integrity`
- `content_reference`

Lifecycle:

```text
active -> stale -> expired
active -> superseded
active -> invalidated
```

Evidence is append-only. Corrections create new records and relationships; they do not rewrite history.

### 4.5 Entity

A stable subject in the managed world, such as a server, domain, account, service, repository, certificate, application, provider resource, network, or organization.

Required properties:

- `entity_id`
- `entity_type`
- `display_name`
- `identity_keys`
- `lifecycle_state`

An Entity represents identity, not a temporary observation of state.

### 4.6 Identity

The set of stable keys and resolution rules used to determine whether records refer to the same Entity.

Identity must distinguish:

- canonical identifier,
- provider-native identifiers,
- aliases,
- environment scope,
- confidence of resolution.

### 4.7 Claim

A typed statement about an Entity or Relationship, supported, challenged, or left unresolved by Evidence.

Required properties:

- `claim_id`
- `subject_id`
- `predicate`
- `value`
- `evidence_ids`
- `confidence`
- `valid_from`
- `valid_until`
- `status`

Allowed status values:

```text
supported | contested | rejected | unknown | stale
```

### 4.8 Relationship

A typed, directional connection between Entities, Claims, Evidence records, Decisions, Plans, or Outcomes.

Required properties:

- `relationship_id`
- `relationship_type`
- `from_id`
- `to_id`
- `evidence_ids`
- `confidence`

Examples:

```text
depends_on
hosted_on
resolves_to
owned_by
supports
contradicts
supersedes
produced_by
approved_by
verified_by
```

### 4.9 Confidence

A bounded expression of how strongly available Evidence supports a Claim, Relationship, Finding, or Decision Candidate.

Canonical representation:

```yaml
confidence:
  score: 0.0
  level: unknown | low | medium | high | verified
  rationale: string
```

Confidence is not probability unless a specific model explicitly defines it as such.

### 4.10 Contradiction

A preserved condition in which two or more Claims about the same subject and predicate cannot all be valid within the same scope and time window.

A Contradiction must reference all participating Claims and must not silently choose a winner.

### 4.11 Unknown

An explicitly represented absence of sufficient validated information.

Unknown is different from:

- `false`,
- `null` used as a transport placeholder,
- failure to collect,
- hidden information,
- contradictory information.

### 4.12 Knowledge State

The validated, time-bounded view composed of Entities, Claims, Relationships, Contradictions, Unknowns, and freshness information.

A Knowledge State is derived. It is reproducible from its referenced Evidence set and evaluation rules.

Required properties:

- `knowledge_state_id`
- `generated_at`
- `evidence_set`
- `rule_set_version`
- `entities`
- `claims`
- `relationships`
- `contradictions`
- `unknowns`

### 4.13 Finding

A notable condition derived from a Knowledge State, such as drift, stale evidence, unsupported runtime, missing backup, policy violation, expiring resource, risk, or cost anomaly.

Required properties:

- `finding_id`
- `finding_type`
- `severity`
- `subject_ids`
- `claim_ids`
- `evidence_ids`
- `explanation`
- `status`

A Finding describes a condition. It does not authorize action.

### 4.14 Policy

A versioned rule or constraint used to evaluate Knowledge States, Findings, Decisions, Plans, Approvals, or execution boundaries.

Required properties:

- `policy_id`
- `version`
- `scope`
- `rule`
- `enforcement`

Enforcement values:

```text
informational | advisory | required | blocking
```

### 4.15 Capability

A stable operation or outcome CyberCore can request independently of a concrete Provider implementation.

Examples:

```text
dns.record.read
dns.record.change
compute.instance.observe
certificate.expiry.inspect
repository.branch.create
```

Required properties:

- `capability_id`
- `input_contract`
- `output_contract`
- `risk_class`
- `approval_requirement`

### 4.16 Intent

A requested outcome expressed without prematurely selecting a concrete Provider or implementation mechanism.

Required properties:

- `intent_id`
- `requested_outcome`
- `scope`
- `constraints`
- `requester`

Intent is translated into capability requirements and may produce one or more Decision Candidates.

### 4.17 Decision Candidate

A proposed conclusion or course of action supported by Findings, Policy evaluation, constraints, and Evidence. It has not yet been approved.

Required properties:

- `decision_id`
- `intent_id`
- `finding_ids`
- `evidence_ids`
- `alternatives`
- `recommended_option`
- `risk`
- `rationale`
- `status`

Allowed status values:

```text
proposed | rejected | selected | expired
```

### 4.18 Mutation Plan

A deterministic, versioned description of intended changes, prerequisites, checks, expected effects, recovery considerations, and required verification.

Required properties:

- `plan_id`
- `revision`
- `decision_id`
- `steps`
- `preconditions`
- `expected_changes`
- `verification_requirements`
- `rollback_metadata`
- `risk`
- `status`

Allowed status values:

```text
draft | verified | approval_required | approved | applying | completed | failed | superseded
```

Any material plan change invalidates prior Approval.

### 4.19 Approval

An explicit human authorization bound to a specific Mutation Plan and revision.

Required properties:

- `approval_id`
- `plan_id`
- `plan_revision`
- `approved_by`
- `approved_at`
- `scope`
- `expires_at`

Approval cannot be inferred from silence, prior approvals, successful dry runs, or provider capability.

### 4.20 Mutation

A controlled operation that changes external or internal managed state according to an approved Mutation Plan.

Mutation must retain:

- plan identity,
- approval identity,
- executor identity,
- provider identity,
- step-level results,
- timestamps,
- failure and recovery information.

### 4.21 Apply Result

The immutable execution record produced by a Mutation attempt.

Required properties:

- `apply_result_id`
- `plan_id`
- `plan_revision`
- `approval_id`
- `started_at`
- `completed_at`
- `step_results`
- `status`
- `provider_receipts`

Allowed status values:

```text
succeeded | partially_succeeded | failed | cancelled
```

An Apply Result is not proof that desired state was achieved.

### 4.22 Verification

The evaluation of new post-mutation Observations and Evidence against the expected effects defined by a Mutation Plan.

Required properties:

- `verification_id`
- `plan_id`
- `apply_result_id`
- `observation_ids`
- `evidence_ids`
- `expected_effects`
- `actual_effects`
- `status`

Allowed status values:

```text
verified | mismatch | inconclusive | failed
```

### 4.23 Outcome

The governed conclusion describing whether an Intent was satisfied after execution and Verification.

Required properties:

- `outcome_id`
- `intent_id`
- `decision_id`
- `plan_id`
- `apply_result_id`
- `verification_id`
- `status`
- `explanation`

## 5. Minimal serialization envelope

All canonical records should support this envelope unless a narrower schema explicitly overrides it:

```yaml
id: string
type: string
schema_version: string
created_at: timestamp
created_by: string
classification: public | internal | confidential | restricted
correlation_id: string | null
attributes: {}
relationships: []
```

## 6. Identifier convention

Recommended form:

```text
<namespace>:<type>:<stable-key>
```

Examples:

```text
cybercore:entity:domain-eimyherrer-com
cybercore:evidence:ev-01J...
cybercore:plan:plan-01J...
```

Identifiers must not embed secrets. Human-readable aliases may change; canonical identifiers must remain stable.

## 7. Conformance

An implementation conforms to CCL-0001 when:

1. it uses canonical terms with the meanings defined here;
2. serialized records retain required traceability fields;
3. unknowns and contradictions remain explicit;
4. no mutation path bypasses plan and approval semantics;
5. verification is based on post-change observation;
6. provider-specific concepts are mapped to canonical terms at the boundary.

## 8. Non-goals

CCL-0001 does not yet define:

- complete JSON Schemas,
- graph database storage layout,
- provider API contracts,
- policy expression syntax,
- query language grammar,
- CLI command names,
- transport-specific CXP representation.

These are subsequent artifacts and must reference this vocabulary rather than redefine it.

## 9. Next artifacts

- `CCL-0002` — record schemas and validation contracts
- `CCL-0003` — relationship and graph semantics
- `ADR` — acceptance of CCL as the canonical domain vocabulary
