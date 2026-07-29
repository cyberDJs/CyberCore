---
id: CCL-0004
type: language-specification
title: CyberCore Canonical Language — Finding, Policy, Intent and Decision
status: draft
version: 0.1.0
owner: CyberCore
created: 2026-07-28
updated: 2026-07-28
requires:
  - CCL-0001
  - CCL-0002
  - CCL-0003
---

# CCL-0004 — Finding, Policy, Intent and Decision

## 1. Purpose

CCL-0004 defines the decision layer that transforms Knowledge State into governed, explainable proposals.

```text
Knowledge State
  -> Finding
  -> Policy Evaluation
  -> Intent
  -> Decision Candidate
```

A Decision Candidate is never an approved mutation.

## 2. Finding semantics

A Finding is a derived condition detected from Knowledge State.

Required invariants:

1. every Finding references the Knowledge State from which it was derived;
2. supporting claims and evidence remain traceable;
3. severity is explicit;
4. status is explicit;
5. a Finding describes a condition, not an authorization;
6. identical active findings should be correlated rather than duplicated without reason.

Canonical severities:

```text
informational | low | medium | high | critical
```

Canonical statuses:

```text
open | acknowledged | suppressed | resolved | obsolete
```

## 3. Policy semantics

A Policy is a versioned, deterministic rule or constraint.

Canonical enforcement levels:

```text
informational | advisory | required | blocking
```

A Policy Evaluation records:

- policy identity and version,
- evaluated subject,
- input Knowledge State,
- result,
- explanation,
- referenced findings and evidence,
- evaluator version and timestamp.

Canonical results:

```text
pass | fail | unknown | not_applicable | error
```

AI may explain a policy result but may not replace deterministic evaluation where a deterministic policy exists.

## 4. Intent semantics

Intent expresses a requested outcome without binding prematurely to a provider or implementation.

Required invariants:

1. requested outcome is explicit;
2. requester identity is explicit;
3. scope and constraints are explicit;
4. intent may be informational or mutating;
5. mutating intent does not imply approval;
6. capability resolution occurs after intent capture.

Canonical intent modes:

```text
observe | explain | assess | recommend | change
```

Canonical statuses:

```text
draft | submitted | evaluating | satisfied | cancelled | expired
```

## 5. Decision Candidate semantics

A Decision Candidate is a proposed conclusion or course of action supported by findings, policies, constraints and evidence.

Required invariants:

1. it references the originating Intent;
2. it references all material Findings and Policy Evaluations;
3. alternatives are preserved;
4. risks and assumptions are explicit;
5. recommendation rationale is traceable;
6. status `selected` does not authorize mutation;
7. any resulting Mutation Plan is a separate artifact.

Canonical statuses:

```text
proposed | rejected | selected | expired | superseded
```

## 6. Risk representation

Risk is represented as:

```yaml
risk:
  likelihood: rare | unlikely | possible | likely | almost_certain
  impact: negligible | minor | moderate | major | severe
  level: low | medium | high | critical
  rationale: string
```

The semantic validator must verify that the derived level is consistent with the configured risk matrix version.

## 7. Explainability contract

Every Finding, Policy Evaluation and Decision Candidate must provide:

- a concise human-readable explanation;
- machine-readable supporting references;
- explicit unknowns and assumptions;
- generation or evaluator identity;
- timestamp and version information.

## 8. Initial schema set

```text
schemas/ccl/v1/finding.schema.json
schemas/ccl/v1/policy.schema.json
schemas/ccl/v1/intent.schema.json
schemas/ccl/v1/decision-candidate.schema.json
```

## 9. Conformance

A conforming implementation must:

1. derive Findings from declared Knowledge State;
2. version every Policy and evaluation;
3. separate user Intent from implementation choice;
4. preserve Decision alternatives and rationale;
5. prevent Decision Candidates from bypassing planning and approval;
6. preserve evidence traceability through the complete decision chain.

## 10. Next artifact

`CCL-0005` will define Mutation Plan, Approval, Apply Result, Verification and Outcome contracts.
