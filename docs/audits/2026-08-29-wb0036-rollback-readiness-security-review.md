# Security review — WB-0036 rollback runtime and first-write readiness

Date: 2026-08-29
Scope: repository implementation only
Remote staging mutation during review: `NONE`

## Security objective

Provide a recovery path for the WB-0034 first staging canary without turning CyberCore into a generic remote deletion client.

## Primary threats considered

### Endpoint substitution

Risk: a synthetic sealed input redirects a valid run-scoped rollback approval to another FTPS server.

Control: both `FirstWriteUploadInput.endpoint_hostname` and the loaded credential endpoint must equal the fixed approved hostname `staging.eimyherrer.com`. The runtime connects to that constant, not a caller-selected hostname.

### Path expansion or mutable-CWD escape

Risk: caller supplies a broader path, or another FTP session renames the target after inspection while relative `DELE` commands continue against the moved working directory.

Control: the rollback function receives the sealed `FirstWriteUploadInput`; there is no independent path argument. The runtime does not enter the target for deletion. It lists and mutates only root-relative absolute paths derived from the sealed destination, including `/cybercore-canary-<run_id>/<approved-artifact>`.

### Deleting unrelated or unclassified content

Risk: the canary directory contains content not created by the run, or MLSD metadata does not positively prove an approved-name entry is a regular file.

Control: the target listing must contain only the two approved canary names, and every present approved entry must have MLSD `type=file`. Missing, malformed or non-file type evidence blocks deletion before the first `DELE`. The target itself must be positively proven as MLSD `type=dir`.

### Reusing write authority as delete authority

Risk: a valid first-write approval is reused for rollback.

Control: rollback uses a distinct deterministic reference:

`approval:wb0036:rollback:<run_id>:<source_commit>`

and still requires literal boolean authorization. Endpoint pinning is enforced independently of this policy reference.

### Credential scope drift

Risk: rollback runs with a production-capable or different identity.

Control: endpoint, username and port are bound to the WB-0034 path-scoped FTPS identity. Credential loading occurs only after sealed-input endpoint and authorization validation.

### Ambiguous FTP outcomes

Risk: server applies `DELE` or `RMD` but the client loses the response and reports a clean failure.

Control: mutation possibility is set before mutating calls. Failures after a mutation attempt preserve a sealed-input-bound partial state. `RMD` reply loss additionally marks directory removal uncertain.

### Recursive/destructive API growth

Risk: rollback evolves into generic cleanup functionality.

Control: no recursive delete, free-form filename, free-form remote path, chmod, chown, rename, upload, production target, or provider operation is exposed.

## Codex security-review repairs

The exact-head security review identified three issues and the repair addresses all three:

1. fixed staging endpoint pinning prevents alternate-server rollback;
2. each `DELE` uses the root-relative absolute sealed path instead of mutable session CWD;
3. every present approved artifact requires positive MLSD `type=file` evidence.

Regression tests cover each repaired boundary.

## Residual risks

- FTPS does not provide transactional multi-file deletion; partial rollback is possible.
- A concurrent actor with write access to the exact same sealed pathname can still race same-name content between listing and deletion. Absolute paths prevent rename/CWD escape, while the dedicated path-scoped identity and unique run directory reduce exposure. Rollback is intended only for the controlled first-write canary.
- Authorization references are policy bindings, not cryptographic capabilities. Enforcement depends on the trusted orchestrator/operator boundary already used by WB-0035.

These risks are acceptable for the unique, path-scoped, first-write canary because the runtime fails closed on endpoint/path/type scope expansion and reports partial mutation conservatively.

## Readiness conclusion

Repository readiness can become PASS after focused tests, CI, CodeQL and fresh review are green on one exact repaired head. Live staging write authority remains a separate user gate after the final WB-0036 merge commit is known and a new exact packet is assembled.
