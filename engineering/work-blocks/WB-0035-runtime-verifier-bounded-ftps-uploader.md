# WB-0035 — Runtime verifier + bounded FTPS uploader

Date: 2026-08-29
Status: `IMPLEMENTED IN CANDIDATE — REMOTE WRITE BLOCKED`
Parent: `WB-0034 — First Staging Deployment Preflight`
Decision basis: `ADR-0007`
Target: `interserver-shared-hosting-staging`

## Goal

Implement the missing runtime pieces required by WB-0034 without performing the first staging write:

- a same-process runner that consumes the sealed `FirstWriteUploadInput` returned by the final packet validator;
- a bounded `FTPS_EXPLICIT` write path enclosed inside that authorized runner and able to create only the approved direct-child canary directory and upload the two sealed artifacts;
- a macOS Keychain adapter for the already-provisioned WB-0034 aliases;
- an independent HTTPS effect verifier that checks the publicly served bytes and version marker after a future authorized write.

## Security invariants

The runner must fail closed unless all of these are true:

1. `validate_first_write_packet(...)` returns `ready=true` and a non-null sealed upload input in the same process.
2. The caller passes literal `remote_write_authorized is True` explicitly.
3. The caller-supplied authorization reference exactly equals the sealed packet authorization reference.
4. The sealed protocol is exactly `FTPS_EXPLICIT`.
5. The runtime credential endpoint exactly equals the sealed `endpoint_hostname`, username equals the verified dedicated identity `ccwb34@eimyherrer.com`, and port is exactly `21`.
6. TLS peer and hostname verification remain enabled through `ssl.create_default_context()`.
7. The control channel is upgraded with `AUTH TLS`; data protection uses `PROT P`; passive mode is enabled.
8. The authenticated FTPS root reports `PWD=/` and a protected `MLSD` data-channel operation succeeds before mutation.
9. Destination is exactly `cybercore-canary-<run_id>/`, is a direct child, and successful protected `MLSD` parent enumeration proves it absent before `MKD`; ambiguous `550` errors are never treated as proof of absence.
10. Destination creation is treated as potentially mutated before `MKD` is dispatched; a lost/failed `MKD` reply produces conservative partial state rather than a false no-mutation result.
11. The sealed artifact set is exactly `index.html` and `cybercore-version.json`, and their in-memory bytes still hash to their sealed SHA-256 values.
12. Each artifact is absent before `STOR` and is read back over FTPS after upload to verify the sealed SHA-256.
13. Credential values never enter ordinary receipts, exception text, repository files, command arguments, or effect-verifier requests.
14. No module-level mutating uploader or capability token exists; the mutating FTPS routine is enclosed inside `execute_first_write_ftps(...)` after the final authorization gates.

## Same-process boundary

`execute_first_write_ftps(...)` calls the canonical final packet validator first and retains the returned `FirstWriteUploadInput` object in memory. It does not reopen packet documents or local artifact paths after validation. The credential loader is invoked only after packet readiness, literal-True remote-write authority, exact authorization-reference matching, protocol validation, and sealed-input validation pass.

The Keychain adapter reads the four existing services under account `CyberCore-WB0034` only when the runner asks for the credential. The password is captured from the `security` subprocess stdout pipe and stored only in the in-memory credential object whose password field is excluded from `repr`.

The mutating FTPS implementation is a local closure of the runner rather than a module-level callable. No `_WRITE_CAPABILITY_GUARD`-style token is exported for another module to obtain and replay.

## Bounded write behavior

The enclosed FTPS write path is not a general filesystem client. It can only:

1. connect to the sealed endpoint on port 21;
2. verify TLS/protected passive data-channel behavior;
3. prove the session root is `/`;
4. prove the exact canary destination is absent;
5. mark the destination creation attempt as potentially mutating, then issue one `MKD`;
6. enter that directory after a confirmed reply;
7. upload exactly the two sealed artifact byte strings;
8. read those two files back and verify their SHA-256 values;
9. disconnect.

It does not implement remote delete, rename, chmod, chown, traversal, production-path access, DNS changes, provider changes, or automatic rollback.

## Failure behavior

If the destination exists, the runner stops before `MKD`. Once `MKD` is dispatched, any transport failure is treated conservatively as a possible remote mutation because the server may have applied the command before the reply was lost. The result preserves the same sealed `upload_input` plus partial state; `destination_creation_uncertain=true` distinguishes an unknown `MKD` outcome from a confirmed created destination.

If a later failure happens after confirmed `MKD`, the runtime does not broaden authority by deleting or repairing the remote directory. The partial state is preserved for a separately authorized exact-path rollback procedure.

Individual file `STOR` is preceded by a successful protected parent-directory `MLSD` absence check and occurs only inside a newly created unique directory. The directory-level `MKD` is the primary fail-if-exists boundary. The post-upload FTPS hash check detects byte drift but is not the independent effect verifier.

## Independent HTTPS effect verifier

`verify_first_write_effect(...)` uses the fixed origin `https://staging.eimyherrer.com`, rejects redirects/URL drift, requires HTTP 200, caps response size, and verifies:

- served `index.html` SHA-256 equals the sealed artifact SHA-256;
- served `cybercore-version.json` SHA-256 equals the sealed artifact SHA-256;
- the marker has exactly the six approved keys;
- repository, commit, branch, environment, and run id match the sealed packet;
- `built_at` is a valid UTC timestamp.

The verifier does not use the FTPS credential and therefore provides an independent observation path for the deployed effect.

## Evidence and tests

WB-0035 unit tests use an in-memory fake FTPS server and fake HTTPS fetcher. They prove:

- no direct module-level mutating uploader or capability token is exposed;
- only sealed bytes are uploaded;
- endpoint, username, and port drift block before connection;
- existing destination blocks before mutation;
- sealed digest drift blocks before connection;
- the Keychain credential password is excluded from representation;
- the runner does not load the secret before literal-True fresh authorization;
- authorization-reference mismatch blocks execution;
- a lost reply after server-side `MKD` is reported with `remote_mutation_possible=true`, the same sealed upload input, and uncertain destination-creation state;
- interrupted `STOR` preserves partial-mutation state and the same sealed upload input;
- valid same-process execution invokes the credential loader exactly once and returns the same sealed in-memory `upload_input` for effect verification;
- HTTPS verification passes only for exact served bytes/marker;
- redirects, hash drift, and marker drift fail closed.

No test in this block performs an InterServer write.

## Remaining gates

WB-0035 does not authorize the first canary write. Before that write:

- canonical `main` must include this implementation after review and merge;
- CI and CodeQL must pass on the exact candidate head;
- rollback runtime behavior must be proven separately or explicitly included in the final authorization packet;
- a concrete final WB-0034 evidence bundle/readiness packet must bind the verified FTPS identity, this runtime verifier, exact source commit, exact run id, destination, artifact hashes, and rollback permission;
- fresh explicit operator authorization for the exact first staging write is required.
