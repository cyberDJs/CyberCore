# WB-0036 — Non-destructive first-write rollback operation

Date: 2026-08-29
Status: `RUNTIME DEFINED — REMOTE MUTATION NOT PART OF ROLLBACK`

## Purpose

Recover safely from the first WB-0034 staging canary write without deleting, renaming, overwriting, or otherwise mutating remote content.

The first write is isolated in a unique no-overwrite directory and does not replace existing staging content. Therefore immediate rollback means **stop and do not promote**, while preserving the canary for evidence.

## Inputs

The rollback runner consumes the original sealed `FirstWriteUploadInput` from the first-write flow. The destination is not accepted as an independent free-form argument.

Required runtime gates:

1. sealed upload input passes `validate_first_write_upload_input`;
2. protocol is exactly `FTPS_EXPLICIT`;
3. sealed endpoint is exactly `staging.eimyherrer.com`;
4. `rollback_authorized is True` literally;
5. authorization reference equals `rollback_authorization_reference(upload_input)`;
6. credential endpoint is exactly `staging.eimyherrer.com`;
7. credential username equals `ccwb34@eimyherrer.com`;
8. port equals `21`;
9. TLS certificate and hostname verification remain enabled;
10. effective FTPS root is `/` for the path-scoped account;
11. when present, the target is positively proven by MLSD as `type=dir`;
12. every present approved artifact is positively proven by MLSD as `type=file`;
13. target contents contain no names outside the two approved canary artifacts.

## Authorization string

For a sealed run, derive the exact rollback reference with:

```python
rollback_authorization_reference(upload_input)
```

Its form is:

```text
approval:wb0036:rollback:<run_id>:<source_commit>
```

A human/operator approval must explicitly cover that exact run before the recovery procedure is entered with `rollback_authorized=True`.

This authorization does **not** authorize physical cleanup. Automated cleanup is intentionally unavailable in WB-0036.

## Recovery sequence

The runtime performs only this read-only sequence:

1. connect only to `staging.eimyherrer.com`;
2. enforce explicit TLS + protected passive mode;
3. prove root `/`;
4. list the root and locate the exact sealed destination as `type=dir`;
5. if absent, return idempotent logical rollback with `cleanup_required=False`;
6. if present, list the exact target by root-relative absolute path;
7. fail closed on any unexpected name or any entry not positively proven as `type=file`;
8. preserve the canary unchanged for evidence;
9. return logical rollback with `cleanup_required=True` and the observed approved artifact names;
10. disconnect.

The rollback runtime contains no `DELE`, `RMD`, `RNFR`, `RNTO`, upload, chmod, chown, or generic remote-path mutation operation.

## Why physical deletion is not automated

FTP/FTPS pathnames are resolved at command time. A second session can rename or replace a pathname after an MLSD inspection but before a subsequent delete/rename command. The protocol does not provide an atomic compare-and-delete operation bound to the inspected directory identity.

Therefore:

- an MLSD proof followed by `DELE`/`RMD` is not sufficient;
- absolute paths remove mutable-CWD escape but do not remove pathname replacement races;
- a policy token claiming exclusive access is not a technical exclusivity mechanism;
- first-write recovery must not perform destructive or availability-changing remote mutation.

Physical cleanup may be designed later as a separate maintenance operation only when real exclusive mutation access or an identity-preserving server-side primitive is available and independently verified.

## Effect-verification failure

If the first-write upload occurs but independent HTTPS effect verification fails:

1. stop the run;
2. perform no additional upload or promotion;
3. invoke the logical rollback inspection if fresh rollback authority is available;
4. preserve the isolated canary directory for evidence;
5. record whether later cleanup is required;
6. do not delete or rename anything automatically.

This leaves pre-existing staging content untouched because the first-write contract is additive and no-overwrite.

## First live canary sequence

After WB-0036 is merged, the final first-write packet must be regenerated from the new canonical `main` commit. Only then can a fresh first-write authorization be requested.

A first-write authorization does not automatically authorize rollback. A rollback authorization does not authorize physical cleanup.
