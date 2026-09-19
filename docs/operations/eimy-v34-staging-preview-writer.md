# EIMY v34 staging preview writer

Date: 2026-09-05
Status: candidate implementation; no live STOU write performed by this change
Target: `staging.eimyherrer.com`

## Purpose

Provide a narrowly bounded way to publish one self-contained HTML preview without weakening the
WB-0036 blocker on the legacy two-file `MKD + STOR` first-write path.

The preview writer is intentionally not a general deploy client. It accepts immutable HTML bytes in
memory and can create exactly one server-uniqued file in the already-scoped staging FTPS root.

## Safety mechanism

The writer uses FTP `STOU`, not `STOR`. RFC 959 defines `STOU` as creating a name unique to the
current directory, and RFC 1123 requires the server to return the generated pathname in the
pre-transfer `125 FILE:` or `150 FILE:` response.

CyberCore captures that response underneath `ftplib.storbinary()`, validates that it resolves to a
direct child of the staging root, and reads the generated file back over protected FTPS to verify its
SHA-256 against the sealed in-memory bytes.

The runtime exposes no `MKD`, `CWD`, `STOR`, rename, delete, chmod, chown, provider, DNS or production
mutation path. It does not accept a caller-selected final remote pathname.

Additional gates are fail-closed:

- endpoint must be exactly `staging.eimyherrer.com`;
- identity must be exactly `ccwb34@eimyherrer.com` on explicit FTPS port 21;
- TLS peer/hostname verification and `PROT P` remain enabled;
- authenticated `PWD` must be exactly `/`;
- a protected passive `MLSD` succeeds before mutation;
- content is non-empty immutable bytes, capped at 32 MiB and hash-bound;
- source commit, run id, protocol, staging identity scope, destination boundary and artifact digest/length are validated before credential loading;
- caller-provided booleans or reproducible strings are **not** authorization evidence;
- fresh operator approval must arrive as canonical JSON signed with Ed25519 by the independent approval issuer;
- the signed claims bind source commit, run id, exact artifact SHA-256 and byte length, endpoint, protocol, scope, STOU destination boundary, `rollback_authorized=false`, issuer, nonce, issue time and expiry;
- approval lifetime is capped at 15 minutes and expired/not-yet-active evidence fails closed;
- signature verification uses only the trusted public key at `/etc/cybercore/staging-preview-approval-ed25519.pub`;
- the trusted key directory and key file must be root-owned and not group/world writable; symlinked key files are rejected by `O_NOFOLLOW` where supported;
- no trusted approval public key is provisioned by this PR; when the trusted key is absent or invalid, execution stops before credential loading or network access;
- each signed approval nonce must be atomically consumed by the trusted local nonce service at `/run/cybercore/staging-preview-approval-nonce.sock` after read-only FTPS preflight and immediately before `STOU`;
- the nonce-service directory/socket and connected peer must be root-owned/trusted, and replay or service unavailability fails closed before mutation;
- the nonce service is responsible for durable shared replay state outside the governed user's writable namespace and is not provisioned by this PR;
- literal fresh write authority and exact signed authorization-reference match are still required;
- any failure after STOU begins is reported conservatively as `remote_mutation_possible=true`;
- there is no automatic cleanup or deletion authority.

## Read-only target evidence

A read-only probe on 2026-09-05 verified the existing dedicated staging credential can establish
explicit FTPS, reports `PWD=/`, identifies the server as Pure-FTPd through its HELP response, and
successfully performs protected `MLSD`. The probe observed four root entries but persisted no names
or secret values.

No `STOU`, `STOR`, `MKD`, rename, delete or production operation was executed by that probe.

## Scope boundary

This mechanism solves only a preview-specific single-file contract. It does **not** unblock
`execute_first_write_ftps(...)`; the exact-name WB-0034 two-file canary remains guarded by
`ATOMIC_NO_OVERWRITE_BLOCKER`.

A live preview write must use a self-contained HTML artifact and still requires independently
issued, Ed25519-signed approval evidence bound to the exact source commit, run id, artifact,
protocol, staging scope and STOU destination. Provisioning the trusted approval public key and
issuing a real approval token are separate governed operations and are not performed by this PR.
Production homepage takeover remains a separate operation with a separate production approval and
rollback plan.
