# WB-0036 — First-write recovery and upload safety gate

Date: 2026-08-29
Status: `IMPLEMENTATION — REMOTE WRITE BLOCKED`
Parent: WB-0035 runtime verifier + bounded FTPS uploader
Canonical base at block start: `f12eb91ea8dd718f9f3c2d366d578859dab31132`
Branch: `wb-0036-rollback-runtime-readiness`

## Goal

Close repository-side recovery hazards and make unsafe first-write behavior fail closed.

This work block does not perform a staging write, delete, rename, or production mutation.

## Recovery decision

Immediate rollback is logical and non-destructive:

- stop the run;
- do not promote or broaden scope;
- inspect only the exact sealed canary path read-only;
- preserve any isolated canary for evidence;
- report whether later cleanup is required;
- perform no `DELE`, `RMD`, `RNFR`, or `RNTO` operation.

Physical cleanup is outside the automated first-write recovery contract and requires a separately reviewed concurrency-safe maintenance mechanism.

## Upload safety finding

Fresh Codex review identified that the merged WB-0035 FTPS uploader cannot truthfully guarantee no-overwrite under concurrent access. FTP `STOR` replaces an existing pathname, so an absence check followed by `STOR` has a TOCTOU window. The directory can likewise be replaced between `MKD` and later pathname-based operations.

WB-0036 therefore changes `execute_first_write_ftps(...)` to fail closed after packet, authority, protocol, and sealed-input validation but **before credential loading or any network operation**.

The current runtime cannot perform a staging upload even when `remote_write_authorized=True`. It returns `ATOMIC_NO_OVERWRITE_BLOCKER` until CyberCore has either:

1. an atomic create-if-absent writer, or
2. independently verified exclusive mutation access implemented as a real technical mechanism.

A boolean, policy token, or operator assertion alone is not accepted as exclusivity evidence.

## Recovery runtime

The rollback runtime remains read-only and bounded to the sealed `FirstWriteUploadInput`. It verifies endpoint, identity, TLS/root scope, MLSD target type, approved artifact names and positive file-type evidence, then reports logical rollback state without remote mutation.

## Test requirements

Regression coverage proves:

- literal-boolean write and rollback authority gates;
- exact authorization-reference binding;
- sealed input validation before any credential or network use;
- an otherwise fully authorized first write is blocked by the atomic no-overwrite gate;
- credential loader and FTPS factory are not invoked by the blocked writer;
- logical rollback performs zero delete/rename/upload operations;
- effect verification and secret-exclusion behavior remain covered.

## Readiness

After this PR merges, CyberCore will be **safe but not live-write ready**.

The next engineering block must implement and independently verify a concurrency-safe first-write mechanism. Only after that mechanism has code, tests, docs, CI, CodeQL and review evidence may a concrete first staging canary packet and fresh write authority be requested.

## Authority boundary

Allowed: repository branch changes, tests, docs, PR/review repair.

Not authorized:

- staging upload;
- staging delete or rename;
- physical cleanup;
- production access or mutation;
- provider/account/credential changes;
- DNS/TLS/firewall changes;
- canonical merge without separate merge approval.
