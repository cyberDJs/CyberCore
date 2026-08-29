# WB-0036 — First-write rollback runtime and live-write readiness

Date: 2026-08-29
Status: `IMPLEMENTATION — REMOTE WRITE BLOCKED`
Parent: WB-0035 runtime verifier + bounded FTPS uploader
Canonical base at block start: `f12eb91ea8dd718f9f3c2d366d578859dab31132`
Branch: `wb-0036-rollback-runtime-readiness`

## Goal

Close the last repository-side safety gap before the first WB-0034 staging canary write:

1. provide a bounded rollback runtime for the exact sealed canary run directory;
2. preserve conservative partial-mutation evidence when FTP delete outcomes are ambiguous;
3. define the final evidence/readiness gates for the first staging canary write.

This work block does not perform a staging write or rollback.

## Bounded design

Rollback is allowed only for the destination already sealed in `FirstWriteUploadInput`:

`cybercore-canary-<run_id>/`

The runtime:

- requires `FTPS_EXPLICIT` and the existing path-scoped identity;
- pins both sealed input and credential to `staging.eimyherrer.com`;
- requires `rollback_authorized is True`;
- requires an exact run-scoped rollback authorization reference;
- loads the credential only after input, endpoint and authorization gates pass;
- verifies TLS, protected passive mode, and FTPS root `/`;
- requires the target to be positively proven as an MLSD `type=dir` entry;
- lists the exact sealed target using its root-relative absolute path;
- rejects every unexpected entry and every approved-name entry not positively proven as MLSD `type=file`;
- issues each `DELE` against the root-relative sealed absolute path, never against mutable session CWD;
- deletes only `index.html` and/or `cybercore-version.json` when present;
- allows missing approved artifacts so an interrupted upload can be cleaned up;
- removes only the exact root-relative sealed run directory after proving it empty;
- treats an already-absent exact directory as an idempotent successful rollback with no remote mutation;
- preserves partial state when a `DELE` or `RMD` outcome may already have mutated remote state.

There is no generic path, recursive delete, chmod, chown, rename, upload, or production operation in the rollback API.

## Fresh rollback authority

The exact authorization reference is derived from the sealed run:

`approval:wb0036:rollback:<run_id>:<source_commit>`

This reference is separate from the first-write authorization reference. A first-write approval never implicitly authorizes rollback, and a rollback approval never authorizes another run. The runtime additionally enforces the fixed approved staging endpoint independently of the authorization string.

## Test requirements

Focused tests cover:

- literal-boolean authority;
- exact run-scoped authorization reference;
- alternate sealed endpoint rejection before secret loading or connect;
- root-relative absolute artifact deletion and exact directory removal;
- interrupted upload with a missing approved artifact;
- idempotent already-absent target;
- unexpected-entry fail-closed behavior before deletion;
- missing MLSD file type fail-closed behavior before deletion;
- ambiguous `DELE` partial-state preservation;
- ambiguous `RMD` partial-state preservation;
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
- rollback runtime is available;
- fresh explicit first staging canary write authority names the exact run;
- no production/provider/DNS/TLS/firewall scope is added.

## Authority boundary

Allowed in this block: repository branch changes, tests, docs, PR/review repair.

Not authorized by this block:

- staging upload;
- staging delete/rollback;
- production access or mutation;
- provider/account/credential changes;
- DNS/TLS/firewall changes;
- canonical merge without a separate merge approval.
