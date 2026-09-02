# WB-MCP0001 — CyberCore MCP Foundation v0.1

Date: 2026-09-02
Status: `CANDIDATE — READ ONLY — EXACT-HEAD VERIFICATION PENDING`
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
- bounded inputs/responses, per-tool timeout and sanitized structured errors;
- invocation audit metadata;
- MCP read-only tool annotations;
- CLI/module entrypoint and doctor/capabilities commands;
- unit, security and real stdio client integration tests;
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

Implemented in the candidate:

- [x] server entrypoint serves stdio only;
- [x] MCP SDK client integration test spawns the real stdio subprocess;
- [x] `tools/list` verifies the exact seven-tool allowlist;
- [x] `tools/call` exercises capabilities, repository verification, project context, status and plan-only behavior;
- [x] every registered tool advertises read-only/closed-world annotations;
- [x] no mutating or generic shell/filesystem tool exists;
- [x] unavailable world-model tools fail closed instead of being claimed available;
- [x] secret/path sanitization is tested at the serialized response boundary;
- [x] oversized input and response fail closed;
- [x] malformed JSON returns a stable sanitized error envelope;
- [x] per-tool timeout fails closed;
- [x] default stdio child environment does not inherit arbitrary parent secrets;
- [x] CLI doctor verifies protocol startup, tool registration, capability call, schemas and disclosure behavior;
- [x] docs describe the current tunnel-client stdio profile and secret split;
- [x] draft PR prepared; no merge without explicit approval.

Verification gates still required on the final exact head:

- [ ] full CyberCore test matrix passes;
- [ ] Ruff lint and format pass;
- [ ] Pyright passes;
- [ ] package/wheel smoke passes;
- [ ] CodeQL passes;
- [ ] tunnel-client local readiness can be exercised on an operator runtime with a real tunnel/runtime key without committing secrets.

## Rollback

Close the draft PR and discard the feature branch. No infrastructure, runtime secret, provider, DNS or production state is changed by this work block.
