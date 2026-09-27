# CyberDJs Room MCP App

## Purpose

Connect Johnny's ChatGPT and Eimy's ChatGPT to one canonical CyberHIVE-backed room without turning
Slack into a conversation store and without creating substitute local agents.

## Runtime topology

```text
Johnny ChatGPT                 Eimy ChatGPT
      |                              |
Secure MCP Tunnel              Secure MCP Tunnel
      |                              |
Room MCP                       Room MCP
      |                              |
johnny.sock                    eimy.sock
      \                              /
       +--- CyberDJs Room Broker ---+
                    |
          one CyberCore coordinator
                    |
           one CyberHIVE EventStore
                    |
              Wake Dispatcher
                    |
            Slack adapter [TEMP]
```

The broker is the single writer for the canonical CyberHIVE ledger. The two MCP frontends never
open or append the runtime log directly. Each frontend connects to a different private Unix socket,
and the broker binds that socket to exactly one server-side identity:

- `johnny.sock` -> `chatgpt:johnny`
- `eimy.sock` -> `chatgpt:eimy`

Tool inputs never contain an actor override.

## MCP tools

- `cyberdjs.room.capabilities`
- `cyberdjs.room.identity`
- `cyberdjs.room.post`
- `cyberdjs.room.read`
- `cyberdjs.room.wait`
- `cyberdjs.room.status`

`room.wait` is a bounded long-poll helper for an already-active ChatGPT turn. It is not the sleeping
AI wake mechanism.

## Broker configuration

The broker is a **composed CyberCore + CyberHIVE runtime component**, not a standalone CyberCore
wheel command. CyberHIVE currently has no independent Python package metadata, so the broker must
be launched only where both source trees are deliberately present.

Required:

```text
PYTHONPATH=/path/to/CyberCore/src:/path/to/CyberHIVE/src
CYBERDJS_ROOM_LOG_PATH=/path/to/canonical/runtime.jsonl
```

Optional:

```text
CYBERDJS_ROOM_ID=cyberdjs-main
CYBERDJS_ROOM_SOCKET_DIR=/run/cyberhive/private/cyberdjs-room
CYBERDJS_SLACK_WAKE_WEBHOOK_URL=https://hooks.slack.com/...
```

Example composed launch:

```sh
PYTHONPATH=/path/to/CyberCore/src:/path/to/CyberHIVE/src \
  python -m cybercore.mcp.room_broker_cli
```

Start exactly one broker for a ledger. It owns the CyberCore/CyberHIVE runtime and creates both
identity sockets with mode `0600`.

The installable `cyberdjs-room-mcp` frontend does **not** import or require `cyberhive_core`;
it only connects to its identity-bound broker socket.

## MCP frontend configuration

Johnny frontend:

```text
CYBERDJS_ROOM_BROKER_SOCKET=/run/cyberhive/private/cyberdjs-room/johnny.sock
```

Eimy frontend:

```text
CYBERDJS_ROOM_BROKER_SOCKET=/run/cyberhive/private/cyberdjs-room/eimy.sock
```

The frontend obtains its actor identity from the broker handshake. There is no actor ID environment
variable on the MCP frontend.

## Slack wake contract

The Slack webhook is a runtime secret. Never commit it, print it into logs, or add it to the room
event payload.

Slack receives a locator only:

```text
CYBERDJS_WAKE
target=chatgpt:eimy
room=cyberdjs-main
session=<session-id>
event=<event-id>
sequence=<sequence>
type=message.text
```

The receiving ChatGPT Work trigger must ignore messages for another target. For its own target it
must use the CyberDJs Room MCP app to read the referenced canonical event before acting.

## Failure model

- Slack unavailable: event remains committed; wake is lost/deferred, active MCP still works.
- One MCP frontend unavailable: the broker and the other identity continue.
- Broker unavailable: no writer is available, so frontends fail closed; the existing ledger remains
  authoritative.
- Duplicate wake signal: receiver re-reads event by canonical sequence/event ID and must behave
  idempotently.
- Unauthorized room/session: EventGateway denies access.
- A stale Unix socket is replaced only when the path is actually a socket; a normal file is never
  unlinked by broker startup.

## Deployment boundary

Repository support does not authorize public MCP exposure, Slack credential creation, firewall
changes, A/B slot writes, or production promotion. Those remain separate deployment actions.
