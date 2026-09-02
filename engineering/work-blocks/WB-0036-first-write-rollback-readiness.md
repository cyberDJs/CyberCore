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

A subsequent review also established that packet validation can run `git fetch origin`, so a blocker placed after packet validation still permits a network connection and Git credential-helper activity.

WB-0036 therefore changes `execute_first_write_ftps(...)` to return `ATOMIC_NO_OVERWRITE_BLOCKER` **before packet validation, credential loading, Git remote access, FTPS factory use, or any other network operation**.

The current runtime cannot perform a staging upload regardless of `remote_write_authorized`, authorization reference, packet contents, or caller-supplied FTPS factory. It remains blocked until CyberCore has either:

1. an atomic create-if-absent writer, or
2. independently verified exclusive mutation access implemented as a real technical mechanism.

A boolean, policy token, or operator assertion alone is not accepted as exclusivity evidence.

## Recovery runtime

The rollback runtime remains read-only and bounded to the sealed `FirstWriteUploadInput`. It verifies endpoint, identity and TLS/root scope, then probes only the exact sealed canary path with `MLST /cybercore-canary-<run_id>`. It never enumerates the staging parent. Only after `MLST` positively proves the exact target is a directory does it use `MLSD` inside that target to validate the approved artifact names and positive file-type evidence.

## Test requirements

Regression coverage proves:

- the blocked first-write runner does not call packet validation;
- therefore it cannot trigger validator-side `git fetch` or Git credential helpers;
- credential loader and FTPS factory are not invoked;
- the blocker is unconditional for write-authority arguments while the unsafe writer is disabled;
- sealed-input validation remains directly covered as a pure helper;
- logical rollback performs zero delete/rename/upload operations;
- rollback inspection uses exact-target `MLST` and target-only `MLSD`, never parent-root enumeration;
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
