# WB-0036 — First-write rollback runtime and live-write readiness

Date: 2026-08-29
Status: `IMPLEMENTATION — REMOTE WRITE BLOCKED`
Parent: WB-0035 runtime verifier + bounded FTPS uploader
Canonical base at block start: `f12eb91ea8dd718f9f3c2d366d578859dab31132`
Branch: `wb-0036-rollback-runtime-readiness`

## Goal

Close the last repository-side safety gap before the first WB-0034 staging canary write:

1. provide a bounded recovery runtime for the exact sealed canary run;
2. make immediate rollback non-destructive so FTP path races cannot delete or rename unrelated content;
3. define the final evidence/readiness gates for the first staging canary write.

This work block does not perform a staging write, delete, rename, or production mutation.

## Recovery decision

The first WB-0034 write is additive and isolated:

`cybercore-canary-<run_id>/`

It never overwrites the existing staging root and is not a promotion step. Therefore the immediate safe rollback is **logical rollback**:

- stop the run;
- do not promote or broaden scope;
- inspect the exact sealed canary path read-only;
- preserve the isolated canary for evidence when it exists;
- report `cleanup_required=True` for later maintenance;
- perform no `DELE`, `RMD`, `RNFR`, or `RNTO` operation.

Physical cleanup is intentionally outside the automated first-write recovery contract. It requires a separately designed and authorized maintenance path with a real concurrency/exclusive-access guarantee. A policy token alone is not accepted as proof of exclusive access.

This decision supersedes the earlier WB-0036 destructive-delete prototype after Codex identified an unavoidable FTP pathname TOCTOU race between inspection and mutation.

## Bounded runtime

The runtime:

- consumes only the sealed `FirstWriteUploadInput`;
- requires `FTPS_EXPLICIT` and the existing path-scoped identity;
- pins both sealed input and credential to `staging.eimyherrer.com`;
- requires `rollback_authorized is True`;
- requires an exact run-scoped rollback authorization reference;
- loads the credential only after input, endpoint and authorization gates pass;
- verifies TLS, protected passive mode, and FTPS root `/`;
- requires the target to be positively proven as MLSD `type=dir` when present;
- lists the exact sealed target using its root-relative absolute path;
- rejects every unexpected entry and every approved-name entry not positively proven as MLSD `type=file`;
- allows missing approved artifacts so interrupted uploads can be inspected;
- returns idempotent logical rollback when the exact directory is already absent;
- reports whether later physical cleanup is required;
- contains no remote mutation primitive in the rollback protocol surface.

There is no generic path, recursive delete, chmod, chown, rename, upload, production operation, or automated physical cleanup in the rollback API.

## Fresh rollback authority

The exact authorization reference is derived from the sealed run:

`approval:wb0036:rollback:<run_id>:<source_commit>`

This reference is separate from the first-write authorization reference. A first-write approval never implicitly authorizes rollback, and a rollback approval never authorizes another run.

The authorization gates entry into the recovery procedure. It does not grant physical cleanup authority.

## Test requirements

Focused tests cover:

- literal-boolean authority;
- exact run-scoped authorization reference;
- alternate sealed endpoint rejection before secret loading or connect;
- present canary logical rollback with zero remote mutation;
- interrupted upload preservation for evidence with zero remote mutation;
- idempotent already-absent target;
- unexpected-entry fail-closed behavior;
- missing MLSD file type fail-closed behavior;
- protected-listing failure with `remote_mutation_possible=False`;
- explicit proof that `DELE`, `RMD`, and rename primitives are never invoked;
- secret exclusion from result representations.

## Final live-write readiness after merge

WB-0036 can only make the repository side ready. A concrete first-write packet must be regenerated from the final canonical merge commit after this block lands.

The first live staging write remains blocked until all of these are current and exact:

- final canonical `main` commit selected as `source_commit`;
- final packet validates READY against that exact commit;
- two artifact hashes match the sealed packet;
- endpoint is exactly `staging.eimyherrer.com`;
- protocol is `FTPS_EXPLICIT`;
- identity is `ccwb34@eimyherrer.com` on port 21;
- deploy identity scope evidence is current;
- effect verifier is available;
- non-destructive logical rollback runtime is available;
- fresh explicit first staging canary write authority names the exact run;
- no production/provider/DNS/TLS/firewall scope is added.

A failed first-write effect verification must stop promotion and preserve the isolated run for evidence. It must not trigger automated deletion.

## Authority boundary

Allowed in this block: repository branch changes, tests, docs, PR/review repair.

Not authorized by this block:

- staging upload;
- staging delete or rename;
- physical cleanup;
- production access or mutation;
- provider/account/credential changes;
- DNS/TLS/firewall changes;
- canonical merge without a separate merge approval.
