# Security review — WB-0036 recovery and first-write safety

Date: 2026-08-29
Scope: repository implementation only
Remote staging mutation during review: `NONE`

## Security objective

Remove destructive rollback races and prevent the first-write runtime from claiming no-overwrite when FTP semantics do not provide it atomically.

## Recovery result

Automated rollback is logical and read-only. It performs no `DELE`, `RMD`, `RNFR`, `RNTO`, upload, chmod, chown, or directory-listing operation. Any created canary is preserved for evidence and later separately authorized maintenance.

Recovery inspection is bounded to exactly three sealed metadata paths:

- the canary directory via `MLST /cybercore-canary-<run_id>` with required `type=dir`;
- `cybercore-version.json` via exact-path `MLST` with required `type=file`;
- `index.html` via exact-path `MLST` with required `type=file`.

The runtime performs no `MLSD`, parent enumeration, canary enumeration, or discovery of unrelated entries. A positive logical-recovery receipt is produced only when all three exact metadata proofs succeed.

MLST failure is never translated into proof of absence. FTP `550` is ambiguous because it can indicate both a missing object and insufficient access. WB-0036 therefore fails closed on every MLST command error. Missing approved artifacts, permission errors, malformed metadata, wrong paths, non-literal path variants, wrong types, non-completed replies, duplicate facts, malformed separators, invalid protocol indentation, invalid fact characters, and unterminated fact lists all block inspection without remote mutation.

Each MLST proof must now satisfy all of these parser invariants:

- the control response is exactly a leading `250-` line, one metadata line, and a terminating `250` line;
- the metadata line starts with exactly one protocol-required leading space because this recovery contract requires facts;
- exactly one metadata fact record is accepted;
- the reported pathname is preserved literally after consuming only the required facts/path delimiter and must equal the requested sealed path byte-for-byte at the Python string level;
- the fact list ends in exactly the protocol terminator `;` and contains no empty component before it;
- fact names contain only RFC 3659 `RCHAR` characters and are non-empty;
- fact values contain only RFC 3659 `SCHAR` characters; empty values remain syntactically permitted;
- duplicate case-insensitive fact keys are rejected;
- malformed facts are rejected;
- the single `type` fact must positively equal the required object type.

## Upload TOCTOU finding

The WB-0035 uploader previously performed an absence check followed by ordinary FTP `STOR`. By FTP semantics, `STOR` replaces a pathname that exists when the command is applied. A concurrent actor can therefore create or replace the pathname after the absence check. The same class of race can affect the directory pathname between `MKD` and later operations.

Consequently the prior "no-overwrite" claim was not proven under concurrency, and non-destructive rollback alone cannot make that writer safe: an overwrite may already have altered pre-existing content.

A later Codex pass identified a second boundary issue: `validate_first_write_packet(...)` can execute `git fetch origin`, so a blocker after validation can still create network activity and invoke configured Git credential helpers.

A ready-triggered review identified a recovery-scope issue: bare parent `MLSD` materialized unrelated staging-root metadata. Recovery was first narrowed to target-specific metadata and was subsequently tightened further to exact-path `MLST` only, eliminating directory listing entirely.

A subsequent exact-head review identified that treating every `MLST 550` as missing was unsafe because `550` can also mean no access. WB-0036 accepts only positive exact metadata as proof and treats both missing-looking and permission-denied `550` replies as blocked inspection.

A later exact-head review identified that normalizing both requested and reported MLST paths with `rstrip("/")` weakened the exact-path contract: a reported artifact path such as `/index.html/` could compare equal to the sealed `/index.html`. WB-0036 now requires literal string equality between the requested MLST path and the single reported metadata path; any trailing slash or other pathname variation blocks recovery.

The next exact-head review identified three parser-level fail-open edges: `sendcmd()` may return non-250 replies, trimming the reported pathname can hide meaningful whitespace, and duplicate `type` facts can silently overwrite each other in a dictionary. WB-0036 now requires a completed `250` reply, preserves the reported pathname literally, and rejects duplicate case-insensitive fact keys before accepting metadata.

The subsequent exact-head review identified one remaining malformed-separator edge: an empty fact component (`type=file;;`) or a missing final `;` terminator (`size=1;type=file`) could still be accepted. WB-0036 now requires one terminal `;`, rejects empty components before that terminator, and keeps malformed MLST metadata fail-closed.

The final grammar-focused review then identified two broader parser gaps: the RFC-required leading space on an MLST fact record was optional in the parser, and control characters could appear inside fact names or values. WB-0036 now validates the complete three-line MLST control-response shape, requires exactly one leading metadata indentation space, and restricts fact names/values to the RFC 3659 `RCHAR`/`SCHAR` character classes before any type evidence is accepted.

## Final WB-0036 control

`execute_first_write_ftps(...)` returns `ATOMIC_NO_OVERWRITE_BLOCKER` as its first operational action, before packet validation and therefore before any validator-side Git remote access.

The blocked first-write entry point performs no:

- packet validation or `git fetch`;
- Git credential-helper activity caused by packet validation;
- staging credential read;
- FTPS factory invocation or network connection;
- `MKD`, `STOR`, rename, delete, or other remote mutation.

The gate is unconditional. No public boolean, authorization reference, capability token, packet contents, FTPS factory, or caller-supplied exclusivity claim can enable the old mutation sequence.

Pure sealed-input validation remains available separately through `validate_first_write_upload_input(...)`; it is not part of the blocked execution path.

## Evidence

Regression tests prove the blocked writer has zero packet-validator, credential-loader, and FTPS-factory calls and produces no remote mutation state.

Read-only recovery tests prove:

- exactly the sealed canary directory and two approved artifact paths are probed;
- no `MLSD` or directory listing occurs;
- unrelated sibling and canary-entry paths are not inspected;
- only structurally complete three-line `250` MLST control responses are accepted;
- the metadata line must carry exactly one protocol-required leading space;
- MLST-reported paths must equal the requested sealed paths literally, including slash and whitespace semantics;
- duplicate case-insensitive facts are rejected;
- empty fact components and unterminated fact lists are rejected;
- control characters and other characters outside RFC 3659 `RCHAR`/`SCHAR` are rejected from fact names/values;
- missing target, missing approved artifact, permission-denied `550`, metadata transport failure, malformed type evidence, malformed facts, malformed separators, and non-literal path reports all fail closed;
- no delete, rename, upload, or other remote mutation occurs;
- secret material is excluded from result representation.

## Future writer requirement

Live first-write readiness requires a separately reviewed mechanism that supplies either:

1. atomic create-if-absent semantics for the approved artifact contract, or
2. independently verified exclusive mutation access for the complete write interval.

Ordinary metadata checks, policy assertions, or human statements are insufficient. FTP `STOU` is a possible research direction because it creates a server-selected unique file, but it does not preserve the current exact pre-authorized filename/directory contract and therefore is not adopted in this block.

## Readiness conclusion

WB-0036 can become repository-safe and merge-ready once tests, CI, CodeQL and fresh exact-head review are green. It does **not** make the staging canary executable.

After merge, a new engineering block must solve the atomic/exclusive writer problem before any fresh staging-write authority is requested. Production scope remains untouched.
