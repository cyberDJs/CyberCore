# WB-0035 Runtime First-Write Operation Contract

Date: 2026-08-29
Status: `CODE PATH ONLY — NO REMOTE WRITE AUTHORITY`

## Runtime components

- `cybercore.first_write_runtime.execute_first_write_ftps` — authoritative same-process packet-to-uploader runner.
- `cybercore.first_write_runtime.upload_first_write_ftps` — bounded FTPS transport implementation.
- `cybercore.first_write_keychain.load_interserver_staging_ftps_credential` — macOS Keychain adapter for the existing WB-0034 aliases.
- `cybercore.first_write_effect.verify_first_write_effect` — independent HTTPS effect verifier.

## Required invocation sequence for a future authorized write

1. Run the code from the exact approved canonical `main` checkout.
2. Build the concrete WB-0034 manifest/readiness/evidence packet and local two-file artifact directory.
3. Call `execute_first_write_ftps(...)` in that same process.
4. Pass `remote_write_authorized=true` only when a fresh approval exists for the exact packet.
5. Pass the exact authorization reference bound into that packet.
6. Supply `load_interserver_staging_ftps_credential` as the credential loader.
7. If the runner returns `executed=false`, stop. Do not retry with a broader credential or alternate protocol.
8. If the runner returns `executed=true`, require `result.upload_input` to be non-null and call `verify_first_write_effect(result.upload_input)` directly; do not reopen packet or artifact paths.
9. Store only sanitized receipt fields and hashes in evidence.
10. If effect verification fails, preserve remote state and use only a separately authorized exact-run-directory rollback.

## Explicitly forbidden

- calling `upload_first_write_ftps(...)` from an unvalidated ad-hoc artifact set in production operations;
- loading the password before packet readiness and fresh authorization gates pass;
- using plain FTP, implicit FTPS, `--insecure`, disabled hostname verification, or a non-21 port;
- changing the endpoint away from the sealed `endpoint_hostname`;
- using the production-capable `eimyherr` SSH/SFTP credential as fallback;
- writing any destination other than the exact `cybercore-canary-<run_id>/` direct child;
- adding extra files;
- automatic delete/rollback without explicit rollback authority;
- serializing `FirstWriteUploadInput` or reopening packet/artifact source paths between final validation and upload.

## Current state

This document describes a future execution path only. WB-0035 development and tests must not set `remote_write_authorized=true` against InterServer and must not perform any staging mutation.
