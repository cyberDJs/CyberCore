# Security review — WB-0036 rollback runtime and first-write readiness

Date: 2026-08-29
Scope: repository implementation only
Remote staging mutation during review: `NONE`

## Security objective

Provide a safe recovery path for the WB-0034 first staging canary without turning CyberCore into a generic remote deletion or rename client.

## Final recovery model

The first canary write is additive, unique, and no-overwrite. It does not replace existing staging content and is not itself a promotion action.

Immediate rollback is therefore **logical and non-destructive**:

- stop;
- do not promote;
- inspect only the exact sealed canary path;
- preserve any created canary for evidence;
- report whether later cleanup is required;
- perform no remote delete or rename.

Physical cleanup is excluded from the automated first-write rollback contract.

## Primary threats considered

### Endpoint substitution

Risk: a synthetic sealed input redirects a valid run-scoped rollback approval to another FTPS server.

Control: both `FirstWriteUploadInput.endpoint_hostname` and the loaded credential endpoint must equal the fixed approved hostname `staging.eimyherrer.com`. The runtime connects to that constant, not a caller-selected hostname.

### Path expansion

Risk: caller supplies a broader path or different destination.

Control: the rollback function receives the sealed `FirstWriteUploadInput`; there is no independent path argument. Inspection is restricted to the exact direct-child `cybercore-canary-<run_id>/` path already validated by the first-write contract.

### Path-identity TOCTOU

Risk: after MLSD validates a directory, another FTPS session renames/replaces that pathname before a later `DELE`, `RMD`, or rename command, causing mutation of a different object.

Control: the final rollback runtime performs no `DELE`, `RMD`, `RNFR`, or `RNTO` command. There is therefore no mutation whose target can be swapped between proof and effect.

This removes the race class instead of attempting to paper over it with a policy-only exclusive-access token.

### Unexpected or unclassified content

Risk: the canary pathname contains content not created by the run, or MLSD metadata is insufficient to classify an approved-name entry.

Control: inspection requires the target to be positively proven as MLSD `type=dir`; contents may contain only the two approved canary names; every present approved entry must be positively proven as MLSD `type=file`. Any mismatch fails closed with zero remote mutation.

### Reusing write authority as rollback authority

Risk: a valid first-write approval is reused for rollback.

Control: rollback uses a distinct deterministic reference:

`approval:wb0036:rollback:<run_id>:<source_commit>`

and requires literal boolean authorization. The reference authorizes entry into the recovery procedure only; it does not authorize physical cleanup.

### Credential scope drift

Risk: recovery connects using a different or production-capable identity.

Control: endpoint, username and port remain bound to the WB-0034 path-scoped FTPS identity. Credential loading occurs only after sealed-input endpoint and authorization validation.

### Secret disclosure

Risk: password or credential material leaks through receipts, errors, reprs, docs, or review evidence.

Control: credentials are used only inside the runtime connection path; result objects retain the sealed upload input but never the credential; regression tests assert the password does not appear in result representations.

### Destructive API growth

Risk: rollback evolves into generic cleanup functionality.

Control: the final `_RollbackFtpsClient` protocol exposes no delete, remove-directory, rename, upload, chmod, chown, or generic mutation primitive. Physical cleanup requires a separate future design and authority boundary.

## Codex security-review evolution

The review sequence found four substantive issues in the destructive prototype:

1. alternate endpoint substitution;
2. mutable-CWD deletion escape;
3. missing positive MLSD file-type proof;
4. unavoidable pathname TOCTOU between inspection and deletion even with absolute paths.

The first three were repaired directly. The fourth changed the architecture: automated physical deletion was removed entirely from first-write rollback.

Regression coverage now proves that logical rollback invokes no `DELE`, `RMD`, or rename primitive under success, interrupted-upload, already-absent, unexpected-entry, malformed-type, and listing-failure paths.

## Residual risks

- The isolated canary may remain reachable at its unique staging URL until later maintenance cleanup.
- Logical rollback restores the pre-existing staging application's behavior because the first-write contract never overwrites or promotes existing content, but it does not restore byte-for-byte filesystem pre-state while the isolated canary remains.
- A future physical-cleanup design will need a real exclusive-access or identity-preserving server-side mechanism; policy assertions alone are insufficient.
- Authorization references remain policy bindings, not cryptographic capabilities.

These residual risks are preferable to automated destructive cleanup with an unclosable FTP pathname race.

## Readiness conclusion

Repository readiness can become PASS after focused tests, CI, CodeQL and fresh Codex review are green on one exact repaired head.

Live staging write authority remains a separate user gate after the final WB-0036 merge commit is known and a new exact packet is assembled. A failed first-write verification must stop and preserve the isolated run; it must not automatically delete or rename remote content.
