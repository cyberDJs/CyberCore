# CyberCore MCP Security v0.1

## Mandatory boundary

v0.1 is read-only. It contains no arbitrary shell tool, sudo/SSH/deploy/DNS/cloud mutation, generic filesystem reader, or production write capability.

## Controls

- deny-by-default explicit tool registry;
- every registered MCP tool advertises `readOnlyHint=true` and `openWorldHint=false` as client hints; these annotations are never treated as authorization;
- plan-only change tool with `execution_authorized=false`;
- canonical CyberCore disclosure sanitization for text, URLs, paths and secret-like values;
- recursive response sanitization redacts secret-bearing output keys before serialization;
- unknown/unintegrated domain capabilities are not registered;
- bounded text input (16 KiB) and bounded serialized response (256 KiB);
- 10 second per-tool response timeout; blocking CyberCore reads run in a worker thread, and because v0.1 exposes no mutation a timed-out read cannot create a write side effect;
- CCL validation accepts JSON data, not client-controlled file paths;
- no arbitrary filesystem read API;
- structured sanitized error envelopes with stable error codes and request IDs;
- per-invocation audit metadata includes UTC timestamp, tool, request_id, result, status and duration;
- stdout is reserved for MCP protocol when serving over stdio;
- stdio clients should use the MCP SDK default child-process environment allowlist; secrets are passed explicitly only when a future capability actually requires them;
- secrets must remain in runtime secret mechanisms and never in repository config or audit output.

## Path boundary

The MCP client cannot supply a filesystem path to a file-reading tool because no such tool exists. The repository root is process startup configuration supplied by the local operator (`--repo` / `CYBERCORE_REPO`), not an MCP tool argument. Text such as `../../etc/passwd` passed to `cybercore.plan.change` remains inert plan text and is never interpreted as a path.

## Fail-closed rules

A request outside the registered capabilities has no corresponding tool. A requested canonical capability that is not implemented on current `main` remains unavailable. Missing evidence, missing provenance or missing authority is not converted into PASS.

Malformed JSON, oversized input/output, timeout, unknown tool name and unsupported capability all fail closed. Tool errors never grant fallback execution through a generic shell, filesystem or provider operation.

## Future mutation phase

Any future mutating MCP release requires a separate architecture/work block and the sequence:

```text
PLAN -> explicit APPROVAL -> APPLY -> VERIFY -> OUTCOME
```

OpenAI authentication, tunnel access, MCP tool annotations, or an MCP tool call is not CyberCore mutation approval.
