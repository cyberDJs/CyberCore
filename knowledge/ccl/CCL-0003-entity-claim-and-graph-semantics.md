---
id: CCL-0003
type: language-specification
title: CyberCore Canonical Language — Entity, Claim and Graph Semantics
status: draft
version: 0.1.0
owner: CyberCore
created: 2026-07-28
updated: 2026-07-28
requires:
  - CCL-0001
  - CCL-0002
---

# CCL-0003 — Entity, Claim and Graph Semantics

## 1. Purpose

CCL-0003 defines the canonical graph slice that transforms validated Evidence into explainable Knowledge State.

```text
Evidence -> Entity -> Claim -> Relationship -> Contradiction -> Knowledge State
```

## 2. Entity semantics

An Entity is a stable identity in the managed world. Entity records must not be replaced merely because observed state changes.

Required invariants:

1. `entity_id` is stable within its namespace.
2. `entity_type` is canonical and provider-independent.
3. `identity_keys` contain no secrets.
4. aliases may change without changing canonical identity.
5. lifecycle state is explicit.
6. merges and splits are represented as new relationships and audit events.

Canonical lifecycle states:

```text
unknown | discovered | active | degraded | retired | deleted
```

## 3. Claim semantics

A Claim is a typed statement about a subject.

Canonical tuple:

```text
(subject_id, predicate, value, scope, valid_time)
```

A Claim must reference Evidence unless its status is `unknown`. Assertions created by users or AI are still claims and require explicit provenance.

Canonical status values:

```text
supported | contested | rejected | unknown | stale
```

Claims are immutable. A changed statement creates a new Claim and a `supersedes` relationship.

## 4. Confidence semantics

Confidence expresses support strength, not truth.

Canonical levels:

```text
unknown | low | medium | high | verified
```

Suggested score mapping:

```text
unknown:  score absent
low:      0.00–0.39
medium:   0.40–0.69
high:     0.70–0.94
verified: 0.95–1.00 plus verification evidence
```

A semantic validator must reject inconsistent level and score combinations.

## 5. Relationship semantics

Relationships are directional, typed, time-bounded, evidence-backed graph edges.

Core relationship types:

```text
depends_on
hosted_on
resolves_to
owned_by
managed_by
connected_to
contains
member_of
supports
contradicts
supersedes
derived_from
produced_by
approved_by
verified_by
```

Inverse relationships may be generated as views but must not be persisted as independent truth unless explicitly observed.

## 6. Contradiction semantics

A Contradiction groups claims that cannot simultaneously hold in the same scope and validity interval.

Contradiction lifecycle:

```text
open -> investigated -> resolved
open -> accepted_ambiguity
```

Resolution must preserve all original claims and evidence. Resolution selects or creates a resulting claim; it never deletes history.

## 7. Knowledge State semantics

Knowledge State is a reproducible snapshot derived from a declared evidence set and rule-set version.

It contains:

- entities,
- claims,
- relationships,
- contradictions,
- unknowns,
- freshness summary,
- generation metadata.

Knowledge State is not an append-only source record. It is a derived artifact and may be regenerated.

## 8. Temporal model

CCL distinguishes:

- observation time — when reality was observed,
- valid time — when a claim applies to reality,
- transaction time — when CyberCore recorded the object,
- generation time — when a derived Knowledge State was produced.

Implementations must not collapse these timestamps into one field.

## 9. Graph conformance

A conforming implementation must:

1. preserve stable Entity identity;
2. keep Claims immutable;
3. attach provenance to Claims and Relationships;
4. represent unknowns and contradictions explicitly;
5. preserve validity intervals;
6. produce reproducible Knowledge States;
7. prevent provider-native concepts from redefining canonical graph semantics.

## 10. Initial schema set

```text
schemas/ccl/v1/confidence.schema.json
schemas/ccl/v1/entity.schema.json
schemas/ccl/v1/claim.schema.json
schemas/ccl/v1/relationship.schema.json
schemas/ccl/v1/contradiction.schema.json
schemas/ccl/v1/knowledge-state.schema.json
```

## 11. Next artifact

`CCL-0004` will define Finding, Policy, Intent and Decision Candidate contracts.
