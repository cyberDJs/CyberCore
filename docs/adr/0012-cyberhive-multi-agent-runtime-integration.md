# ADR-0012 — CyberHIVE multi-agent runtime integration

- Status: Proposed
- Date: 2026-09-27

## Context

PR #105 defines CyberCore room orchestration against an `EventGateway` protocol. PR #32 defines
CyberHIVE's canonical communication `EventStore` over the existing RuntimeBus. The MVP needs a
real composition path without making CyberCore orchestration depend directly on CyberHIVE types or
making Open WebUI the source of truth.

## Decision

Add `CyberHIVEEventGateway` at the CyberCore integration boundary. It translates Core
`RoomEventDraft` / `TrustedActor` records to CyberHIVE `CommunicationEvent` /
`EventAccessContext` records and translates persisted events back to Core `RoomEvent`.

Add a loopback-only stdlib HTTP adapter with one endpoint:

`POST /v1/rooms/message`

The request body contains room/session/message routing data but not actor identity. The reviewed Open
WebUI Pipe provides its authenticated `__user__.id` in `X-CyberDJS-User-ID`; the endpoint derives
the canonical actor ID as `openwebui:<user-id>`.

The HTTP listener rejects non-loopback binding. This is an MVP local integration boundary, not a
claim of network authentication. Any LAN/public exposure requires a separate deployment/security
design with authenticated transport.

## Consequences

- one Open WebUI user turn and multiple agent replies share one HIVE ledger;
- restart/resume uses persisted communication sequence and hash chain;
- Core still owns routing/floor control;
- HIVE still owns runtime persistence;
- Open WebUI remains replaceable;
- no new web framework dependency is introduced.

## Verification

The integration smoke must prove:

1. HTTP user turn reaches Core;
2. Agent A and Agent B reply in deterministic order;
3. all three events are in one HIVE room/session ledger;
4. hash-chain verification passes;
5. a fresh runtime process resumes after persisted sequence;
6. new turns continue sequence without duplicate replay;
7. a voice transcript enters the same event stream.

## Residual risk

Loopback confinement is not cryptographic client authentication. The runtime currently trusts the
reviewed local adapter to supply `X-CyberDJS-User-ID`. This is acceptable only for the local MVP.
Non-local deployment remains explicitly out of scope.

## Rollback

The change is additive. Before merge, discard the feature branch. After merge but before deployment,
revert the integration commit(s). No existing runtime log format is migrated.
