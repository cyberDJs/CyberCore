# CyberCore MCP Security v0.2

## Mandatory boundaries

- deny-by-default explicit tool registry;
- no generic shell or filesystem tool;
- no provider/cloud/deployment mutation;
- no approval bypass;
- model input cannot choose the trusted actor identity;
- communication backend must enforce room/session authorization;
- tool invocation is explicit allowlist only;
- secret-bearing response keys are recursively redacted;
- bounded input/output and per-tool timeout remain enforced;
- audit metadata records tool, request ID, result, status and duration.

## Communication writes

`events.post` and `agent.invoke` may append communication events. They are not
production infrastructure mutation authority. Canonical event authorization remains
behind the injected EventGateway/backend.

## HTTP exposure

The repository CLI rejects non-loopback Streamable HTTP binding. Network exposure,
TLS, OAuth, reverse proxies and credentials require a separate deployment/security review.

## Failure behavior

Missing backend, denied tool, malformed JSON, timeout, oversized payload and unavailable
runtime components fail closed with sanitized structured errors.
