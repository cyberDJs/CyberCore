# WB-0036 — Non-destructive first-write recovery

Date: 2026-08-29
Status: `RECOVERY RUNTIME DEFINED — FIRST WRITE BLOCKED`

## Authority and supersession

For the WB-0034 first staging canary, this document supersedes the destructive rollback procedure in `docs/operations/wb-0034-first-staging-deployment-mop.md`.

It also supersedes any earlier claim that the current FTPS `MKD` + `STOR` sequence provides a proven no-overwrite first write under concurrent access.

## Recovery model

The recovery runtime is read-only. It may inspect only the three exact sealed canary paths and report whether cleanup is required, but it performs no delete, rename, upload, chmod, chown, directory listing, or other remote mutation.

For recovery inspection:

1. stop;
2. do not promote;
3. preserve evidence;
4. probe `MLST /cybercore-canary-<run_id>` and require `type=dir`;
5. probe `MLST /cybercore-canary-<run_id>/cybercore-version.json` and require `type=file`;
6. probe `MLST /cybercore-canary-<run_id>/index.html` and require `type=file`;
7. for each probe require a completed `250` reply, exactly one metadata record, literal pathname equality, no duplicate case-insensitive facts, and the expected positive type;
8. if and only if all three positive proofs succeed, record the canary as present and physical cleanup as required;
9. perform no automated cleanup.

The runtime performs no `MLSD`. It never enumerates the staging parent or canary contents, and it never probes unrelated sibling paths or unrelated canary entries.

An MLST error does not prove absence. FTP `550` can mean either a missing pathname or insufficient access, so WB-0036 treats every MLST command error as an inspection failure. Non-250 replies, missing approved artifacts, permission failures, malformed or duplicate facts, pathname whitespace/slash changes, and path/type mismatches all fail closed without remote mutation.

## Current first-write blocker

FTP `STOR` replaces an existing pathname. An absence check followed by `STOR` is therefore not an atomic create-if-absent operation. Another session can create or replace the pathname between proof and mutation. Similar pathname races exist around `MKD` and subsequent operations.

Packet validation is also not guaranteed offline because it can consult the Git remote. Therefore `execute_first_write_ftps(...)` now returns `ATOMIC_NO_OVERWRITE_BLOCKER` immediately, **before packet validation, `git fetch`, Git credential helpers, staging credential loading, or FTPS connection setup**.

No current approval string or caller-supplied parameter can bypass this technical gate.

## What can unblock first write

A later engineering block must provide one of these and prove it independently:

- an atomic server-side create-if-absent mechanism compatible with the exact approved deployment artifact contract; or
- real exclusive mutation access covering the exact staging scope for the complete mutation interval.

A boolean, policy token, operator statement, prior metadata probe, or ordinary path check is not enough.

Pure FTP `STOU` may be investigated as a future primitive because it creates a server-selected unique filename, but adopting it would require a separately reviewed artifact/destination contract; it is not silently substituted here.

## Rollback authorization

The run-scoped rollback reference remains:

`approval:wb0036:rollback:<run_id>:<source_commit>`

It authorizes entry into read-only recovery inspection only. It does not authorize physical cleanup.

## Live canary status

**BLOCKED.** Do not request or execute the first staging canary write until a concurrency-safe writer has been implemented, tested, reviewed, and merged. Once that exists, regenerate the final packet from the then-current canonical `main` commit and request fresh exact write authority.
