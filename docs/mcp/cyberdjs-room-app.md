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
actor=chatgpt:johnny           actor=chatgpt:eimy
      \                              /
       +-------- CyberCore ----------+
                    |
            CyberHIVE EventStore
                    |
              Wake Dispatcher
                    |
            Slack adapter [TEMP]
```

The two MCP instances run the same code. Identity is bound by operator configuration before the MCP
server starts. Tool inputs never contain an actor override.

## MCP tools

- `cyberdjs.room.capabilities`
- `cyberdjs.room.identity`
- `cyberdjs.room.post`
- `cyberdjs.room.read`
- `cyberdjs.room.wait`
- `cyberdjs.room.status`

`room.wait` is a bounded long-poll helper for an already-active ChatGPT turn. It is not the sleeping
AI wake mechanism.

## Runtime configuration

Required:

```text
CYBERDJS_ROOM_ACTOR_ID=chatgpt:johnny | chatgpt:eimy
CYBERDJS_ROOM_LOG_PATH=/path/to/canonical/runtime.jsonl
```

Optional:

```text
CYBERDJS_ROOM_ID=cyberdjs-main
CYBERDJS_ROOM_DISPLAY_NAME=Johnny AI
CYBERDJS_SLACK_WAKE_WEBHOOK_URL=https://hooks.slack.com/...
```

The Slack webhook is a runtime secret. Never commit it, print it into logs, or add it to the room
event payload.

## Slack wake contract

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
- MCP unavailable: CyberHIVE history remains authoritative.
- Duplicate wake signal: receiver re-reads event by canonical sequence/event ID and must behave
  idempotently.
- Unauthorized room/session: EventGateway denies access.

## Deployment boundary

Repository support does not authorize public MCP exposure, Slack credential creation, firewall
changes, A/B slot writes, or production promotion. Those remain separate deployment actions.
