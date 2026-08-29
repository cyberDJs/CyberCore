# Security review — WB-0036 recovery and first-write safety

Date: 2026-08-29
Scope: repository implementation only
Remote staging mutation during review: `NONE`

## Security objective

Remove destructive rollback races and prevent the first-write runtime from claiming no-overwrite when FTP semantics do not provide it atomically.

## Recovery result

Automated rollback is logical and read-only. It performs no `DELE`, `RMD`, `RNFR`, `RNTO`, upload, chmod or chown operation. Any created canary is preserved for evidence and later separately authorized maintenance.

## Upload TOCTOU finding

The WB-0035 uploader previously performed an absence check followed by ordinary FTP `STOR`. By FTP semantics, `STOR` replaces a pathname that exists when the command is applied. A concurrent actor can therefore create or replace the pathname after the absence check. The same class of race can affect the directory pathname between `MKD` and later operations.

Consequently the prior "no-overwrite" claim was not proven under concurrency, and non-destructive rollback alone cannot make that writer safe: an overwrite may already have altered pre-existing content.

A later Codex pass identified a second boundary issue: `validate_first_write_packet(...)` can execute `git fetch origin`, so a blocker after validation can still create network activity and invoke configured Git credential helpers.

## Final WB-0036 control

`execute_first_write_ftps(...)` now returns `ATOMIC_NO_OVERWRITE_BLOCKER` as its first operational action, before packet validation and therefore before any validator-side Git remote access.

The blocked first-write entry point performs no:

- packet validation or `git fetch`;
- Git credential-helper activity caused by packet validation;
- staging credential read;
- FTPS factory invocation or network connection;
- `MKD`, `STOR`, rename, delete, or other remote mutation.

The gate is unconditional. No public boolean, authorization reference, capability token, packet contents, FTPS factory, or caller-supplied exclusivity claim can enable the old mutation sequence.

Pure sealed-input validation remains available separately through `validate_first_write_upload_input(...)`; it is not part of the blocked execution path.

## Evidence

Regression tests replace the packet validator with a function that raises if called and require the blocked runner to return normally while proving:

- packet-validator call count is zero;
- credential loader call count is zero;
- FTPS factory call count is zero;
- `executed=False`;
- `remote_mutation_possible=False`;
- no upload receipt, sealed upload input, or partial mutation state is produced;
- the same blocker is returned even with false or mismatched write-authority arguments.

Direct helper tests separately preserve coverage for sealed-input protocol and artifact-digest validation. The read-only recovery tests prove zero remote mutation across present, absent, interrupted and malformed target states.

## Future writer requirement

Live first-write readiness requires a separately reviewed mechanism that supplies either:

1. atomic create-if-absent semantics for the approved artifact contract, or
2. independently verified exclusive mutation access for the complete write interval.

Ordinary MLSD checks, policy assertions, or human statements are insufficient. FTP `STOU` is a possible research direction because it creates a server-selected unique file, but it does not preserve the current exact pre-authorized filename/directory contract and therefore is not adopted in this block.

## Readiness conclusion

WB-0036 can become repository-safe and merge-ready once tests, CI, CodeQL and fresh exact-head review are green. It does **not** make the staging canary executable.

After merge, a new engineering block must solve the atomic/exclusive writer problem before any fresh staging-write authority is requested. Production scope remains untouched.
