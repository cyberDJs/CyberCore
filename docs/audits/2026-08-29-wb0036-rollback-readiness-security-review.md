# Security review — WB-0036 rollback runtime and first-write readiness

Date: 2026-08-29
Scope: repository implementation only
Remote staging mutation during review: `NONE`

## Security objective

Provide a recovery path for the WB-0034 first staging canary without turning CyberCore into a generic remote deletion client.

## Primary threats considered

### Path expansion

Risk: caller supplies a broader path or parent directory.

Control: the rollback function receives the sealed `FirstWriteUploadInput`; destination is revalidated and reduced only by removing its required trailing slash. There is no independent path argument.

### Deleting unrelated content

Risk: the canary directory contains content not created by the run.

Control: the target listing must contain only the two approved canary names. Any unexpected name or non-file entry blocks deletion before the first `DELE`.

### Reusing write authority as delete authority

Risk: a valid first-write approval is reused for rollback.

Control: rollback uses a distinct deterministic reference:

`approval:wb0036:rollback:<run_id>:<source_commit>`

and still requires literal boolean authorization.

### Credential scope drift

Risk: rollback runs with a production-capable or different identity.

Control: endpoint, username and port remain bound to the WB-0034 path-scoped FTPS identity. Credential loading occurs only after input and authorization validation.

### Ambiguous FTP outcomes

Risk: server applies `DELE` or `RMD` but the client loses the response and reports a clean failure.

Control: mutation possibility is set before mutating calls. Failures after a mutation attempt preserve a sealed-input-bound partial state. `RMD` reply loss additionally marks directory removal uncertain.

### Recursive/destructive API growth

Risk: rollback evolves into generic cleanup functionality.

Control: no recursive delete, free-form filename, free-form remote path, chmod, chown, rename, upload, production target, or provider operation is exposed.

## Residual risks

- FTPS does not provide transactional multi-file deletion; partial rollback is possible.
- A concurrent actor with access to the same path could race between listings and deletes. Unexpected content introduced before the final `RMD` prevents directory removal, but a same-name file replacement cannot be cryptographically distinguished by this rollback path.
- Authorization references are policy bindings, not cryptographic capabilities. Enforcement depends on the trusted orchestrator/operator boundary already used by WB-0035.

These risks are acceptable for the unique, path-scoped, first-write canary because the runtime fails closed on scope expansion and reports partial mutation conservatively.

## Readiness conclusion

Repository readiness can become PASS after focused tests, CI, CodeQL and review are green on one exact head. Live staging write authority remains a separate user gate after the final WB-0036 merge commit is known and a new exact packet is assembled.
