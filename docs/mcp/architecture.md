# CyberCore MCP Architecture v0.1

## Flow

```text
ChatGPT / Codex / Responses API
        |
        v
OpenAI Secure MCP Tunnel
        |
        v
tunnel-client
-------- TRUST BOUNDARY --------
        |
        v
CyberCore MCP (stdio, read-only)
        |
        v
CyberCore runtime / CCL / repository context
```

The MCP layer is an interface module over existing CyberCore application/domain services. It is not a second evidence engine, provider framework, or mutation engine.

## Authorization layers

1. OpenAI product authentication.
2. Secure MCP Tunnel authentication and tunnel permission.
3. MCP tool allowlist/capability authorization.
4. CyberCore repository/runtime authorization and disclosure policy.
5. Future mutation approval bound to an exact plan/revision.

Passing one layer never implies passing a later layer.

## v0.1 architectural decisions

- stdio only;
- no listener and no inbound port;
- official MCP Python SDK v2;
- explicit capability manifest;
- small domain-specific tool allowlist;
- read-only operations plus plan-only change envelopes;
- canonical disclosure sanitization reused for output and errors;
- unavailable canonical runtime capabilities are reported as unavailable rather than reimplemented inside MCP.

## Canonical integration point

`src/cybercore/mcp/` belongs to the Presentation/Application interface boundary and depends inward on existing CyberCore runtime, CCL validation, repository identity, trusted operation context, status, and doctor services.

It must not introduce provider-specific mutation paths or own domain truth.
