---
id: CCL-0005
type: language-specification
title: CyberCore Canonical Language — Mutation, Approval, Verification and Outcome
status: draft
version: 0.1.0
owner: CyberCore
created: 2026-07-28
updated: 2026-07-28
requires:
  - CCL-0001
  - CCL-0002
  - CCL-0003
  - CCL-0004
---

# CCL-0005 — Mutation, Approval, Verification and Outcome

## 1. Purpose

CCL-0005 defines the governed execution layer that converts a selected Decision Candidate into a controlled, auditable and verified change.

```text
Decision Candidate
  -> Mutation Plan
  -> Verification of plan
  -> Approval
  -> Apply Result
  -> Post-change Observation
  -> Verification
  -> Outcome
```

## 2. Mutation Plan semantics

A Mutation Plan is deterministic, versioned and immutable per revision.

Required invariants:

1. every plan references exactly one Decision Candidate;
2. steps have stable ordering and identifiers;
3. preconditions are explicit;
4. expected effects are explicit;
5. verification requirements are explicit;
6. risk and rollback metadata are explicit;
7. any material change creates a new revision;
8. prior approvals do not apply to a new revision.

Canonical statuses:

```text
draft | verified | approval_required | approved | applying | completed | failed | superseded
```

## 3. Approval semantics

Approval is an explicit human authorization bound to a specific plan and revision.

Approval must include:

- approver identity,
- approval time,
- approved scope,
- plan identifier,
- plan revision,
- optional expiration,
- optional conditions.

Approval cannot be inferred from silence, past approvals, successful dry runs, provider capability or AI recommendation.

Canonical statuses:

```text
active | expired | revoked | consumed
```

## 4. Apply Result semantics

Apply Result is the immutable execution record for one mutation attempt.

It records:

- plan and revision,
- approval identity,
- executor and provider identities,
- start and completion times,
- step-level results,
- provider receipts,
- failure and recovery metadata.

Canonical statuses:

```text
succeeded | partially_succeeded | failed | cancelled
```

A successful Apply Result is not proof that desired state was achieved.

## 5. Verification semantics

Verification evaluates new post-change Observations and Evidence against the plan's expected effects.

Required invariants:

1. verification references the Apply Result;
2. observations occur after execution begins;
3. expected and actual effects are recorded separately;
4. mismatches are preserved;
5. inconclusive verification does not become success.

Canonical statuses:

```text
verified | mismatch | inconclusive | failed
```

## 6. Outcome semantics

Outcome is the governed conclusion describing whether the originating Intent was satisfied.

Canonical statuses:

```text
satisfied | partially_satisfied | not_satisfied | unknown | rolled_back
```

Outcome must reference:

- Intent,
- Decision Candidate,
- Mutation Plan,
- Apply Result,
- Verification.

## 7. Safety invariants

1. no mutation without a verified plan;
2. no mutation without active matching approval;
3. no approval reuse across plan revisions;
4. no success conclusion from provider response alone;
5. every mutation requires post-change observation;
6. partial execution is never silently reported as full success;
7. rollback is itself a governed mutation;
8. all execution artifacts preserve traceability to Evidence.

## 8. Initial schema set

```text
schemas/ccl/v1/mutation-plan.schema.json
schemas/ccl/v1/approval.schema.json
schemas/ccl/v1/apply-result.schema.json
schemas/ccl/v1/verification.schema.json
schemas/ccl/v1/outcome.schema.json
```

## 9. Conformance

A conforming implementation must:

1. bind approval to a specific plan revision;
2. reject execution without valid approval;
3. record step-level execution results;
4. perform post-change observation;
5. evaluate expected versus actual effects;
6. distinguish execution success from outcome satisfaction;
7. retain immutable execution and verification history.

## 10. Lifecycle completion

With CCL-0005, the first complete CyberCore canonical lifecycle is specified:

```text
Provider
-> Observation
-> Evidence
-> Entity / Claim / Relationship
-> Knowledge State
-> Finding / Policy
-> Intent
-> Decision Candidate
-> Mutation Plan
-> Approval
-> Apply Result
-> Verification
-> Outcome
```

The next phase is reference implementation and conformance testing against CCL-0001 through CCL-0005.
