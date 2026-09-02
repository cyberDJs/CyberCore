# CyberCore MCP v0.1

Read-only MCP interface for CyberCore. v0.1 exposes OBSERVE / UNDERSTAND / VERIFY / PLAN only.

## Quick start

```bash
python -m pip install -e .
cybercore-mcp capabilities
cybercore-mcp doctor
cybercore-mcp serve
```

Equivalent module entrypoint:

```bash
python -m cybercore.mcp serve
```

`serve` uses MCP stdio. Stdout is reserved for the MCP protocol; audit logs use normal logging/stderr.

## v0.1 tools

- `cybercore.capabilities`
- `cybercore.status`
- `cybercore.project_context`
- `cybercore.verify.repository`
- `cybercore.verify.runtime`
- `cybercore.ccl.validate`
- `cybercore.plan.change`

The canonical main branch currently defines CCL schemas for Entity, Evidence, Finding and related records, but does not yet contain the complete integrated runtime search engine. Those search/get tools are therefore advertised as unavailable rather than emulated.

See `architecture.md`, `security.md`, and `secure-tunnel.md`.
