# ADR-0011 — CyberCore Multi-Agent Room Orchestration MVP

- Status: Proposed
- Date: 2026-09-27

## Context

CyberCore owns routing, agent selection, workflow and floor control. CyberHIVE owns runtime
transport and canonical communication persistence. The two layers must remain replaceable and
must not import each other's implementation classes.

## Decision

Add a `communication` application boundary in CyberCore. `RoomCoordinator` depends only on an
`EventGateway` protocol. `AgentRegistry` owns runtime agent identity, availability and deterministic
priority ordering. For an MVP broadcast, Core gives the floor sequentially by `(priority, actor_id)`
and appends each reply to the same room/session through the gateway.

Agent failures become canonical `system.error` events while other eligible agents continue.
Voice transcripts enter the same session history through `message.voice.transcript`; CyberCore does
not own audio transport.

## Consequences

- CyberCore remains the policy/orchestration owner.
- CyberHIVE persistence can be replaced without changing Core orchestration.
- The deterministic MVP floor-control policy is deliberately small and testable.
- Consensus and model-based agent selection remain future policies behind the same boundary.

## Rejected alternatives

- Importing `cyberhive_core` directly into CyberCore: couples control and runtime planes.
- Letting Open WebUI call agents independently: creates parallel conversations and no canonical floor control.
- Using voice runtime events as canonical chat history: conflates interface telemetry with communication truth.

## Verification

- two-agent broadcast in deterministic order;
- target-specific routing;
- offline agent skipped;
- failing agent emits system error without aborting the room;
- resume after sequence;
- voice transcript shares room/session history.

## Rollback

Additive repository-only change. Discard the branch before merge or revert the merge commit after merge.
