# CyberDJs Room MCP App

## Purpose

Connect Johnny's work ChatGPT, Johnny's personal moderator ChatGPT, and Eimy's ChatGPT to one
canonical CyberHIVE-backed room without turning Slack into a conversation store and without
creating substitute local agents.

## Runtime topology

```text
Johnny Work ChatGPT     Johnny Moderator       Eimy ChatGPT
       |                      |                     |
Secure MCP Tunnel       Secure MCP Tunnel      Secure MCP Tunnel
       |                      |                     |
Room MCP                Room MCP               Room MCP
       |                      |                     |
johnny-work.sock        johnny-mod.sock         eimy.sock
       \_____________________|_____________________/
                             |
                   CyberDJs Room Broker
                             |
                   one CyberCore coordinator
                             |
                    one CyberHIVE EventStore
                             |
                       Wake Dispatcher
                             |
                     Slack adapter [TEMP]
```

The broker is the single writer for the canonical CyberHIVE ledger. The three MCP frontends never
open or append the runtime log directly. Each frontend connects to a different private Unix socket,
and the broker binds that socket to exactly one server-side identity:

- `johnny-work.sock` -> `chatgpt:johnny-work` -> role `participant`
- `johnny-mod.sock` -> `chatgpt:johnny-mod` -> role `moderator`
- `eimy.sock` -> `chatgpt:eimy` -> role `participant`

The moderator role is semantic orchestration metadata. It does not grant additional room,
filesystem, network, or tool authorization. Tool inputs never contain an actor override.

The legacy `chatgpt:johnny` identity may remain in historical ledger events, but it is not an
allowed identity for new MCP sessions after the three-participant migration.

## MCP tools

- `cyberdjs.room.capabilities`
- `cyberdjs.room.identity`
- `cyberdjs.room.post`
- `cyberdjs.room.read`
- `cyberdjs.room.wait`
- `cyberdjs.room.status`

`cyberdjs.room.identity` also reports `participant_role`.

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
CYBERDJS_ROOM_SOCKET_DIR=/run/cyberdjs-room
CYBERDJS_SLACK_WAKE_WEBHOOK_URL=https://hooks.slack.com/...
```

Example composed launch:

```sh
PYTHONPATH=/path/to/CyberCore/src:/path/to/CyberHIVE/src \
  python -m cybercore.mcp.room_broker_cli
```

Start exactly one broker for a ledger. It owns the CyberCore/CyberHIVE runtime and creates all
three identity sockets with mode `0600`.

The installable `cyberdjs-room-mcp` frontend does **not** import or require `cyberhive_core`;
it only connects to its identity-bound broker socket.

## MCP frontend configuration

Johnny work frontend:

```text
CYBERDJS_ROOM_BROKER_SOCKET=/run/cyberdjs-room/johnny-work.sock
```

Johnny moderator frontend:

```text
CYBERDJS_ROOM_BROKER_SOCKET=/run/cyberdjs-room/johnny-mod.sock
```

Eimy frontend:

```text
CYBERDJS_ROOM_BROKER_SOCKET=/run/cyberdjs-room/eimy.sock
```

The frontend obtains its actor identity from the broker handshake. There is no actor ID environment
variable on the MCP frontend.

## Suggested loopback ports

The identity boundary is the Unix socket, not the TCP port. A practical local mapping is:

```text
chatgpt:johnny-work -> 127.0.0.1:8767/mcp
chatgpt:johnny-mod  -> 127.0.0.1:8768/mcp
chatgpt:eimy        -> 127.0.0.1:8769/mcp
```

Each endpoint then gets its own Secure MCP Tunnel and tunnel ID.

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

Broadcast wake targets all configured AI participants except the event author.

## Failure model

- Slack unavailable: event remains committed; wake is lost/deferred, active MCP still works.
- One MCP frontend unavailable: the broker and the other two identities continue.
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
