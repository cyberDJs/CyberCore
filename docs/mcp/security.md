# CyberCore MCP Security v0.1

## Mandatory boundary

v0.1 is read-only. It contains no arbitrary shell tool, sudo/SSH/deploy/DNS/cloud mutation, generic filesystem reader, or production write capability.

## Controls

- deny-by-default explicit tool registry;
- plan-only change tool with `execution_authorized=false`;
- canonical CyberCore disclosure sanitization for text, URLs, paths and secret-like values;
- unknown/unintegrated domain capabilities are not registered;
- bounded text input (16 KiB) and bounded serialized response (256 KiB);
- CCL validation accepts JSON data, not file paths;
- no arbitrary filesystem read API;
- structured sanitized error envelopes with request IDs;
- per-invocation audit metadata: tool, request_id, status and duration;
- stdout reserved for MCP protocol when serving over stdio;
- secrets must remain in runtime secret mechanisms and never in repository config or audit output.

## Fail-closed rules

A request outside the registered capabilities has no corresponding tool. A requested canonical capability that is not implemented on current `main` remains unavailable. Missing evidence, missing provenance or missing authority is not converted into PASS.

## Future mutation phase

Any future mutating MCP release requires a separate architecture/work block and the sequence:

```text
PLAN -> explicit APPROVAL -> APPLY -> VERIFY -> OUTCOME
```

OpenAI authentication, tunnel access, or an MCP tool call is not CyberCore mutation approval.
