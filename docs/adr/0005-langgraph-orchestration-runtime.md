# ADR-0005 — LangGraph as Optional Orchestration Runtime

- Status: Proposed
- Date: 2026-08-19
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

## Proposed decision

Adopt LangGraph as an **optional orchestration runtime** behind CyberCore's existing governance
and provider boundaries.

LangGraph would own workflow control flow and transient graph state. It would not become:

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

The dependency remains optional for consumers while the decision is evaluated. Development
and CI install it so the candidate implementation can be tested.

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

## Acceptance gate

This ADR remains **Proposed** until LG-0001 demonstrates all of the following in hosted CI:

1. deterministic `CURRENT`, `DRIFT`, `CONFLICT`, and `UNKNOWN` classification;
2. regression coverage for the PR #37 / PR #38 duplicate-remediation scenario;
3. no provider writes, network calls, LLM calls, or secret persistence;
4. no regression in existing CyberCore tests, package build, lint, type checks or CodeQL;
5. a documented removal path that leaves the core domain model intact.

Acceptance or rejection requires an explicit maintainer decision after that evidence exists.
