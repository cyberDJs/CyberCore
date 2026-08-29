# WB-0036 — Bounded first-write rollback operation

Date: 2026-08-29
Status: `RUNTIME DEFINED — REMOTE ROLLBACK REQUIRES FRESH AUTHORITY`

## Purpose

Recover only the exact staging canary directory associated with one sealed first-write run. This is not a general FTPS cleanup tool.

## Inputs

The rollback runner consumes the original sealed `FirstWriteUploadInput` from the first-write flow. The destination is not accepted as an independent free-form argument.

Required runtime gates:

1. sealed upload input passes `validate_first_write_upload_input`;
2. protocol is exactly `FTPS_EXPLICIT`;
3. `rollback_authorized is True` literally;
4. authorization reference equals `rollback_authorization_reference(upload_input)`;
5. credential endpoint equals the sealed endpoint;
6. credential username equals `ccwb34@eimyherrer.com`;
7. port equals `21`;
8. TLS certificate and hostname verification remain enabled;
9. effective FTPS root is `/` for the path-scoped account;
10. target contents contain no names outside the two approved canary artifacts.

## Authorization string

For a sealed run, derive the exact rollback approval reference with:

```python
rollback_authorization_reference(upload_input)
```

Its form is:

```text
approval:wb0036:rollback:<run_id>:<source_commit>
```

A human/operator approval must explicitly cover that exact run before the runtime may be called with `rollback_authorized=True`.

## Deletion sequence

The runtime performs only this bounded sequence:

1. connect to the sealed FTPS endpoint;
2. enforce explicit TLS + protected passive mode;
3. prove root `/`;
4. list the root and locate the exact sealed destination;
5. if absent, return idempotent success with no mutation;
6. enter the exact destination;
7. list contents and fail closed on any unexpected entry or non-file entry;
8. delete present approved artifacts in deterministic order;
9. prove the directory is empty;
10. return to `/`;
11. remove only the exact sealed destination;
12. prove the destination is absent from the parent listing.

The runtime never recursively removes a directory and never accepts a caller-selected filename to delete.

## Partial or ambiguous outcomes

FTP acknowledgements can be lost after a server has already applied `DELE` or `RMD`.

If a failure occurs after a delete attempt, the result must set:

```text
remote_mutation_possible = True
```

and preserve:

- the same sealed `upload_input`;
- already-confirmed deleted artifact names;
- the active artifact whose delete outcome is ambiguous;
- whether directory removal was attempted;
- whether directory removal is uncertain.

Do not retry blindly after an ambiguous result. Re-inspect the exact run directory first, then request any further remote mutation authority required by policy.

## First live canary sequence

After WB-0036 is merged, the final first-write packet must be regenerated from the new canonical `main` commit. Only then can a fresh first-write authorization be requested.

A first-write authorization does not automatically authorize rollback. If rollback becomes necessary, use the run-scoped rollback reference above.
