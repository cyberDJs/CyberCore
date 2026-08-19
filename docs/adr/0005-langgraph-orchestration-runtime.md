# ADR-0005 — LangGraph as Optional Orchestration Runtime

- Status: Accepted
- Date: 2026-08-19
- Accepted: 2026-08-19
- Authorized by: Jan Kočí
- Decision owners: CyberCore maintainers
- Related: LG-0001, OPS-0001

## Context

CyberCore already defines an evidence-first lifecycle with explicit authority, approval,
execution, verification and memory boundaries. The project also has deterministic checkpoint
and state foundations, but it does not yet have a dedicated orchestration runtime for
multi-step, resumable or eventually human-interrupted agent workflows.

Recent post-merge reconciliation work provides a concrete test case: GitHub may already show
a pull request as merged while a tracked project-state document still reports the pre-merge
state. A reconciler must detect that drift without treating lower-authority copies as canonical
and without opening duplicate remediation when an existing pull request already covers it.

## Decision

Adopt LangGraph as an **optional orchestration runtime** behind CyberCore's existing governance
and provider boundaries.

LangGraph owns workflow control flow and transient graph state. It does not become:

- the CyberCore source of truth;
- an authorization or policy authority;
- an evidence store;
- a secrets store;
- a provider abstraction;
- a bypass around human approval or existing execution gates.

The first slice, LG-0001, is deliberately deterministic and read-only. It normalizes already
observed facts, resolves explicitly designated canonical sources, classifies
`CURRENT | DRIFT | CONFLICT | UNKNOWN`, detects existing remediation, and returns a
recommendation. It performs no network calls and no writes.

The dependency remains optional for consumers. Development and CI install it so the accepted
orchestration boundary remains continuously exercised.

## Why LangGraph

LangGraph provides an explicit StateGraph model and a path to checkpointing, durable execution
and human-in-the-loop interrupts without forcing CyberCore to replace its own domain model,
source-of-truth rules or execution governance.

## Consequences

Positive:

- explicit, inspectable orchestration instead of hidden agent loops;
- deterministic workflows can coexist with later agentic nodes;
- future checkpoint and interrupt support maps cleanly to CASER approval gates;
- orchestration remains separable from providers and canonical data.

Costs and risks:

- one additional runtime dependency and its transitive dependency surface;
- overlap risk with CyberCore's existing checkpoint/state abstractions;
- framework churn could leak into core contracts if the boundary is not kept narrow;
- a graph can make bad policy decisions faster if governance is accidentally embedded inside it.

## Alternatives considered

### Custom state machine

Keeps dependencies minimal but duplicates orchestration, checkpoint and future interrupt
mechanics that are not CyberCore's differentiating value.

### LangChain agent abstraction

Higher-level and faster for generic agents, but too opinionated for the initial deterministic,
governed workflow boundary.

### Generic task queue or workflow engine

Useful for background jobs, but does not directly address stateful agent control flow and would
still require a separate agent orchestration model.

### No orchestration runtime

Lowest complexity now, but leaves repeated multi-step control flow to ad-hoc code as workflows
grow.

## Acceptance evidence

ADR-0005 was accepted after LG-0001 satisfied the proposed acceptance gate on candidate head
`2536b6728ef03abff84302161d6b14779be88352`:

1. deterministic `CURRENT`, `DRIFT`, `CONFLICT`, and `UNKNOWN` classification is covered by the
   LG-0001 regression suite;
2. the PR #37 / PR #38 duplicate-remediation scenario is covered and returns
   `OBSERVE_EXISTING_REMEDIATION`;
3. independent diff review found no provider writes, network calls, LLM calls, write nodes, or
   secret persistence in LG-0001;
4. hosted CI run `32256609212` passed Python 3.11–3.14 tests, Ruff lint/format, Pyright, package
   build and wheel smoke test; hosted CodeQL run `32256609137` passed;
5. LG-0001 documents a removal path that leaves the canonical CyberCore domain model, provider
   contracts and persisted formats intact.

Acceptance establishes the architecture decision only. It does **not** authorize merge,
deployment, production mutation, provider writes, secret access, or future write-capable
LangGraph nodes. Those remain subject to their existing independent governance gates.
