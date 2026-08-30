# ADR-0007 — Durable LongRun Runtime

Status: PROPOSED

## Context

CyberCore needs to support long-running autonomous work that can survive process restarts without treating a single model request as the unit of durability. The objective is not artificial wall-clock duration; the runtime must preserve mission integrity, measurable progress, evidence, and bounded autonomy for runs lasting many hours.

CyberCore already contains repository checkpoints, trusted operation context, evidence controls, and an accepted LangGraph orchestration boundary. LongRun therefore extends those contracts instead of replacing them.

## Decision

Introduce `cybercore.longrun` as a deterministic durable control plane around planners, model calls, tools, and evaluators.

The durable unit is a **run**, identified by `run_id` and bound to an immutable canonical mission manifest digest. A run is a sequence of independently checkpointed steps. Each step is proposed by a planner, admitted or rejected by a value/effect governor, executed by an adapter, evaluated, and recorded in an append-only event ledger backed by SQLite.

### Safety boundary

The initial runtime is fail-closed:

- unknown effects are denied;
- prohibited effects are denied before executor invocation;
- the default MARATHON-16 profile permits only reads and sandbox writes;
- production writes, credential changes, billing changes, and permission changes remain prohibited;
- changing the mission after a checkpoint invalidates resume;
- repeated failures and duplicate work trigger re-planning;
- maximum wall budget terminates the run.

Consequential external actions remain governed by existing CyberCore authorization mechanisms and are out of scope for WB-LR0001.

### Completion boundary

A run does not complete merely because an evaluator reports success. Completion requires both:

1. evaluator score at or above the manifest threshold; and
2. satisfaction of the configured minimum wall budget.

For normal production profiles the minimum may be zero. MARATHON-16 deliberately sets a 16-hour minimum only because it is an endurance benchmark. Useful work must still pass the value governor; the runtime must not manufacture no-op work merely to consume time.

### Persistence

SQLite is selected for the MVP because it provides transactional local persistence without adding a network service. The schema stores current run state plus an append-only event ledger. A future distributed worker implementation may replace the storage adapter without changing the mission or step contracts.

### Orchestration

LangGraph remains the accepted higher-level orchestration option. LongRun does not require LangGraph for durability; it may host LangGraph planners/workflows as adapters. This keeps recovery, authorization and audit semantics independent from any one agent framework.

## Alternatives rejected

### One 16-hour model/API request

Rejected because request lifetime is not a reliable persistence or recovery boundary and does not provide sufficient checkpoint, audit or crash-recovery semantics.

### New Redis/Temporal/Kafka control plane immediately

Rejected for the MVP. It creates infrastructure and operational burden before single-node endurance behavior is proven.

### Let the agent self-score and continue indefinitely

Rejected because self-evaluation without independent evidence encourages loops, goal drift and fabricated progress.

## Consequences

Positive:

- crash-safe resume;
- immutable mission binding;
- deterministic safety checks outside the model;
- explicit evidence and progress events;
- framework-independent adapters;
- low infrastructure overhead.

Costs:

- SQLite is single-node oriented;
- independent evaluator/model adapters are not implemented in this first slice;
- event compaction and long-run storage quotas will be needed before large fleet deployment.

## WB-LR0001 acceptance criteria

- mission digest is deterministic and resume rejects drift;
- SQLite state survives engine reconstruction;
- prohibited effects never reach the executor;
- non-positive-value steps are blocked;
- watchdog detects maximum wall time, repeated failures, and duplicate loops;
- completion requires evaluator threshold plus minimum wall time;
- tests cover the above contracts;
- no production or credential mutation is introduced.
