# CyberCore MCP through OpenAI Secure MCP Tunnel

Verified against the current OpenAI Secure MCP Tunnel guide and the current `openai/tunnel-client` operator documentation.

## Topology

```text
CyberCore MCP (stdio)
  -> tunnel-client child process binding
  -> outbound HTTPS to OpenAI tunnel service
  -> ChatGPT / Codex / Responses API
```

No inbound MCP port is required.

## Local MCP smoke

```bash
cybercore-mcp doctor
cybercore-mcp capabilities
cybercore-mcp serve
```

## tunnel-client setup

Use the CLI as source of truth before hand-editing YAML:

```bash
tunnel-client help quickstart
tunnel-client profiles samples list
tunnel-client init \
  --sample sample_mcp_stdio_local \
  --profile cybercore-local-stdio \
  --tunnel-id tunnel_0123456789abcdef0123456789abcdef \
  --mcp-command "cybercore-mcp serve"
tunnel-client doctor --profile cybercore-local-stdio --explain
tunnel-client run --profile cybercore-local-stdio
```

The runtime API key belongs in the runtime environment/secret store as `CONTROL_PLANE_API_KEY`; do not commit it. `OPENAI_ADMIN_KEY` is for tunnel administration only and must not be reused as the long-lived daemon credential.

The tunnel ID is created/selected in OpenAI Tunnels management. Runtime users need tunnel Read + Use permission; tunnel managers need the corresponding management permission.

## Readiness

Do not test ChatGPT/Codex discovery until `tunnel-client doctor --profile cybercore-local-stdio --explain` is healthy or the tunnel-client `/readyz` endpoint reports readiness.

## Trust boundary

The tunnel authenticates and transports MCP traffic. It does not grant CyberCore authorization. CyberCore v0.1 still registers only its read-only allowlist and continues to apply its own disclosure and repository identity policy.

## Responses API / ChatGPT / Codex

The OpenAI-hosted product targets the tunnel associated with the same `tunnel_id`; the product never needs a direct route to the private stdio server. Product-side MCP approvals and connector permissions remain separate from the tunnel runtime key and from CyberCore authorization.
