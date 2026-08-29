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
3. sealed endpoint is exactly `staging.eimyherrer.com`;
4. `rollback_authorized is True` literally;
5. authorization reference equals `rollback_authorization_reference(upload_input)`;
6. credential endpoint is exactly `staging.eimyherrer.com`;
7. credential username equals `ccwb34@eimyherrer.com`;
8. port equals `21`;
9. TLS certificate and hostname verification remain enabled;
10. effective FTPS root is `/` for the path-scoped account;
11. the target is positively proven by MLSD as `type=dir`;
12. every present approved artifact is positively proven by MLSD as `type=file`;
13. target contents contain no names outside the two approved canary artifacts.

## Authorization string

For a sealed run, derive the exact rollback approval reference with:

```python
rollback_authorization_reference(upload_input)
```

Its form is:

```text
approval:wb0036:rollback:<run_id>:<source_commit>
```

A human/operator approval must explicitly cover that exact run before the runtime may be called with `rollback_authorized=True`. The runtime independently pins the endpoint, so a synthetic packet cannot redirect an otherwise valid run approval to another FTPS server.

## Deletion sequence

The runtime performs only this bounded sequence:

1. connect only to `staging.eimyherrer.com`;
2. enforce explicit TLS + protected passive mode;
3. prove root `/`;
4. list the root and locate the exact sealed destination as `type=dir`;
5. if absent, return idempotent success with no mutation;
6. list the exact target by root-relative absolute path;
7. fail closed on any unexpected name or any entry not positively proven as `type=file`;
8. issue `DELE` for present approved artifacts using root-relative absolute sealed paths such as `/cybercore-canary-<run_id>/index.html`;
9. list the same absolute target path and prove it empty;
10. issue `RMD` only for `/cybercore-canary-<run_id>`;
11. prove the destination is absent from the root listing.

The runtime never relies on a mutable session working directory for deletion, never recursively removes a directory and never accepts a caller-selected filename to delete.

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
