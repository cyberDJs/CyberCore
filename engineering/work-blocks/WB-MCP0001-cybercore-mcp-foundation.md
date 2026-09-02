# WB-MCP0001 — CyberCore MCP Foundation v0.1

Date: 2026-09-02
Status: `CANDIDATE — READ ONLY`
Base: `main@f12eb91ea8dd718f9f3c2d366d578859dab31132`
Branch: `wb-mcp0001-cybercore-mcp-foundation`

## Goal

Add the smallest production-oriented MCP interface that exposes verified CyberCore read capabilities over stdio and can be attached to OpenAI Secure MCP Tunnel through `tunnel-client`.

## Scope

- official MCP Python SDK v2;
- stdio server;
- seven explicit read/plan-only tools;
- capability manifest and fail-closed unavailable capability reporting;
- CyberCore disclosure and repository identity reuse;
- bounded inputs/responses and sanitized structured errors;
- invocation audit metadata;
- CLI/module entrypoint and doctor/capabilities commands;
- unit/security tests;
- MCP architecture/security/tunnel documentation.

## Explicitly out of scope

- arbitrary shell or filesystem tools;
- SSH/sudo/deploy/DNS/provider/cloud mutation;
- production changes;
- generic proxy/VPN behavior;
- reimplementation of the unmerged PR #13 world-model runtime;
- canonical project-state reconciliation unrelated to MCP;
- merge to main.

## Reality/provenance note

At work-block start, actual `main` is `f12eb91...` (merged PR #64), while `.cybercore/project.yaml` still describes WB-0034/PR55 and `last_verified_main=d74497e...`. This work block preserves that inconsistency as a source-of-truth drift finding and does not silently rewrite it.

## Acceptance

- server starts over stdio;
- MCP tools are listed by the SDK;
- capabilities/status/context/repository/runtime/CCL-plan tools are callable;
- no mutating tool exists;
- secret/path sanitization remains enforced;
- oversized input fails closed;
- tests and existing suite pass on exact PR head;
- docs describe current tunnel-client setup;
- draft PR prepared; no merge without explicit approval.

## Rollback

Close the draft PR and discard the feature branch. No infrastructure, runtime secret, provider, DNS or production state is changed by this work block.
