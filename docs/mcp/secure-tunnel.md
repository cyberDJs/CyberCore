# CyberCore MCP transport notes

## Secure MCP Tunnel

The stdio transport remains suitable for the existing private tunnel composition:

```text
CyberCore MCP stdio
  -> tunnel-client child process
  -> outbound secure tunnel
  -> ChatGPT / Codex
```

Tunnel authentication transports MCP traffic. It does not grant CyberCore room,
tool or mutation authorization.

## Open WebUI

Current Open WebUI MCP integration expects Streamable HTTP. CyberCore therefore exposes
the same MCPServer over a loopback-only Streamable HTTP CLI mode for local integration
testing. No network exposure is authorized by this repository change.

## Local commands

```bash
cybercore-mcp capabilities
cybercore-mcp serve
cybercore-mcp serve-http --host 127.0.0.1 --port 8766
```
