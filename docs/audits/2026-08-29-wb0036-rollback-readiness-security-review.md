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

## Final WB-0036 control

`execute_first_write_ftps(...)` now fails closed after validating:

- final sealed packet readiness;
- literal `remote_write_authorized is True`;
- exact authorization reference;
- `FTPS_EXPLICIT` protocol;
- run id, destination, artifact set and sealed artifact digests.

It then returns `ATOMIC_NO_OVERWRITE_BLOCKER` before invoking the credential loader or FTPS factory. Therefore the current first-write path performs no credential read, network connection, `MKD`, `STOR`, rename, delete, or other remote mutation.

This gate is unconditional. No public boolean, capability token, or caller-supplied exclusivity claim can enable the old mutation sequence.

## Evidence

Regression tests require an otherwise authorized valid packet to remain blocked while proving:

- credential loader call count is zero;
- FTPS factory call count is zero;
- `executed=False`;
- `remote_mutation_possible=False`;
- no mutation receipt or partial mutation state exists;
- sealed-input validation and authorization gates still fail closed before the blocker when invalid.

The read-only recovery tests separately prove zero remote mutation across present, absent, interrupted and malformed target states.

## Future writer requirement

Live first-write readiness requires a separately reviewed mechanism that supplies either:

1. atomic create-if-absent semantics for the approved artifact contract, or
2. independently verified exclusive mutation access for the complete write interval.

Ordinary MLSD checks, policy assertions, or human statements are insufficient. FTP `STOU` is a possible research direction because it creates a server-selected unique file, but it does not preserve the current exact pre-authorized filename/directory contract and therefore is not adopted in this block.

## Readiness conclusion

WB-0036 can become repository-safe and merge-ready once tests, CI, CodeQL and fresh exact-head review are green. It does **not** make the staging canary executable.

After merge, a new engineering block must solve the atomic/exclusive writer problem before any fresh staging-write authority is requested. Production scope remains untouched.
