# CyberCore MCP Architecture v0.2

## Flow

```text
ChatGPT / Codex                 Open WebUI
      |                            |
Secure MCP Tunnel          Streamable HTTP (local/internal)
      |                            |
      +--------- CyberCore MCP ----+
                    |
          thin transport adapter
                    |
            CyberCore services
                    |
            EventGateway boundary
                    |
            CyberHIVE runtime
```

MCP is an integration/tool transport. It does not own room history, agent selection,
workflow, policy or authorization truth.

## Transport

The same MCPServer supports:

- stdio for local process/tunnel composition;
- Streamable HTTP for deployable MCP clients.

Repository CLI permits Streamable HTTP only on loopback. Any LAN/public exposure,
TLS termination or OAuth deployment is a separate reviewed deployment action.

## Communication tools

- `cybercore.events.post`
- `cybercore.events.read`
- `cybercore.events.subscribe`
- `cybercore.presence.get`
- `cybercore.runtime.status`
- `cybercore.agent.invoke`
- `cybercore.tool.invoke`

The communication backend is injected. If absent, communication calls fail closed.

## Identity boundary

The runtime constructs `RoomCommunicationBackend` with a trusted actor.
MCP tool arguments never choose `actor_id` or `actor_type`.

## Tool invocation boundary

`cybercore.tool.invoke` is allowlist-only. MCP does not expose shell,
generic filesystem access, provider mutation or an approval bypass.
