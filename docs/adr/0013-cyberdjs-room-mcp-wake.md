# ADR-0013 — CyberDJs Room MCP and Event-Driven ChatGPT Wake

- Status: Proposed
- Date: 2026-09-27

## Context

CyberCore and CyberHIVE already provide a canonical room/event boundary with trusted actor
identity, durable sequence/resume, and a private MCP transport path. The target is not to create
local substitute agents. The target is to let Johnny's ChatGPT and Eimy's ChatGPT participate in
the same CyberHIVE-backed room under separate identities, while still allowing a sleeping ChatGPT
session to be nudged when a room event targets it.

ChatGPT does not currently accept arbitrary CyberHIVE events as a native wake source. Slack is
therefore used only as a temporary wake adapter. Slack must never become conversation storage or
an authorization source.

## Decision

Add a dedicated `CyberDJs Room` MCP surface and an event-driven wake boundary.

One CyberDJs Room Broker owns the CyberCore coordinator and the canonical CyberHIVE EventStore.
It is the only process that opens the room ledger for writes.

Two lightweight MCP frontends connect to identity-specific private Unix sockets exposed by that
broker:

- `johnny.sock` is bound to `chatgpt:johnny`;
- `eimy.sock` is bound to `chatgpt:eimy`.

The MCP tool arguments cannot select or override actor identity. The frontend learns its identity
from the broker socket handshake. Each identity is authorized only for configured CyberDJs room
IDs.

The room app exposes only the minimum conversation surface:

- capabilities;
- identity;
- post;
- read;
- bounded wait for an already-active session;
- runtime status.

A `WakeAwareEventGateway` decorates the canonical `EventGateway`. It dispatches a wake request only
after the room event has been persisted successfully. Wake delivery is best-effort and cannot make
a committed room event fail.

`WakeDispatcher` is adapter-neutral. The first adapter is Slack Incoming Webhook. Slack receives
only event locators (`target`, `room`, `session`, `event`, `sequence`, `type`) and never receives
message text, attachments, prompts, credentials, or the canonical history.

The Slack adapter receives its webhook URL only from runtime configuration. No webhook or token is
stored in source control, the room ledger, or MCP responses.

## Wake semantics

- Explicit `target=chatgpt:johnny` wakes Johnny only.
- Explicit `target=chatgpt:eimy` wakes Eimy only.
- `target=*` wakes all configured AI participants except the event author.
- Non-conversational events are ignored by the wake dispatcher.
- The woken ChatGPT instance must re-read the canonical event through the MCP room app before
  deciding whether or how to respond.

This makes Slack a replaceable interrupt transport rather than a source of truth.

## Security consequences

- Model-supplied arguments cannot impersonate another ChatGPT identity.
- No generic shell or filesystem tool is added.
- No public listener is authorized by this ADR.
- Slack sees locators only, reducing data exposure if the wake channel is compromised.
- Slack outage degrades wake behavior but does not affect room persistence or active MCP sessions.

## Operational consequences

- One codebase serves both ChatGPT identities.
- One broker owns the ledger writer; identity-specific MCP frontends are stateless proxies.
- The broker is launched only in an explicitly composed CyberCore + CyberHIVE source runtime;
  it is not exposed as a standalone CyberCore wheel entrypoint.
- The installable MCP frontend has no direct `cyberhive_core` runtime dependency.
- Each identity uses its own MCP frontend/tunnel while sharing the broker-owned runtime.
- Active ChatGPT sessions use MCP directly; they do not depend on Slack polling.
- Slack is required only for sleeping-session wake until a more direct ChatGPT event trigger exists.

## Rejected alternatives

- Local Ollama/LM Studio agents: they are not the requested Johnny/Eimy ChatGPT participants.
- Polling CyberHIVE from both ChatGPT instances: wasteful and adds avoidable latency.
- Making Slack the canonical room: duplicates CyberHIVE state and weakens provenance.
- Allowing `actor_id` in MCP tool payloads: enables impersonation.
- Adding NATS/MQTT/Redis only for wake: unnecessary additional infrastructure for one interrupt edge.
- Two independent MCP processes opening the same append-only ledger: rejected because the current
  CyberHIVE log store has no cross-process writer lock and therefore requires a single writer.

## Verification

1. Each MCP frontend reports the identity fixed by its broker Unix socket.
2. Johnny cannot post as Eimy and Eimy cannot post as Johnny.
3. Both frontends use one broker-owned CyberHIVE writer and the same room ledger.
4. Explicit targeting emits one wake locator to the intended sink.
5. Broadcast wakes the other configured AI participant(s), not the author.
6. Wake failure does not roll back or corrupt the persisted room event.
7. Slack payload contains no room message text or secret-bearing fields.
8. Ledger integrity remains valid after MCP posts and wake attempts.

## Rollback

Disable the wake adapter and stop the MCP frontends and single room broker. Revert this additive change if
necessary. The canonical CyberHIVE room history remains valid and requires no migration.
