# ADR-0015 — Governed Nextcloud R1 off-host transfer for issue #113

Status: **PROPOSED / Draft PR only**

Date: 2026-11-12

## Context

Issue #113 has verified the database recovery path but still lacks a verified full
application/data archive in a separate failure domain. Manual transfer attempts were
bounded by workstation throughput, and creating a temporary SSH credential through
the available remote-control tool was blocked by its safety layer.

CyberCore already has a fail-closed governed execution bridge. It uses an SSH
subsystem, fixed operation allowlists, exact target binding, `shell=False`, approval
verification and receipts. The bridge must be extended without turning MCP into a
remote shell.

## Decision

Add one fixed target:

```text
target_id: cyberskills-vps-nextcloud-r1
hostname: 162.35.186.106
ssh_user: cybercore-exec
subsystem: cybercore-exec
```

Add two fixed operations:

```text
nextcloud.r1.offhost.transfer
nextcloud.r1.offhost.rollback
```

Neither operation accepts free-form arguments.

The transfer operation invokes only:

```text
/usr/bin/python3 /usr/local/libexec/cybercore-exec/nextcloud-r1-offhost-transfer
```

The rollback operation invokes only:

```text
/usr/bin/python3 /usr/local/libexec/cybercore-exec/nextcloud-r1-offhost-rollback
```

## MCP boundary

The room MCP exposes an explicit
`cyberdjs.room.nextcloud_r1_offhost_transfer` tool. It accepts only:

- `operation_id`;
- `plan_id`;
- `plan_revision`;
- `authorization_reference`.

It does not accept a host, username, path, command, port, key path or arbitrary
environment value.

The MCP handler constructs the fixed governed action itself. A model-supplied
authorization reference is only binding metadata. The handler is usable only when
the runtime injects a trusted `ExecutionAuthorizationVerifier`; the existing
deny-all behavior remains the default when no verifier is configured.

## Source boundary

The source side uses a dedicated temporary Ed25519 public key whose
`authorized_keys` entry MUST be restricted to the fixed exporter, for example:

```text
restrict,command="/home/eimyherr/.local/libexec/cybercore-nextcloud-r1-source-export" ssh-ed25519 <TEMP_PUBLIC_KEY> cc-r1-113-temp
```

The exporter accepts only the exact `SSH_ORIGINAL_COMMAND` values:

- `metadata`;
- `stream`;
- `revoke`.

It never evaluates the original command as shell text.

The source archive is fixed to:

```text
/home/eimyherr/softaculous_backups/nextcloud.586_28528.2026-10-07_18-30-01.tar.gz
```

After a complete stream, the exporter atomically removes exactly one matching
temporary key entry from `authorized_keys`. A broken stream does not report
success.

## Target boundary

The target destination is fixed to:

```text
/var/backups/cybercore/nextcloud-r1-113/2026-10-13/
```

The target helper requires:

- target directory mode `0700`, owned by the execution identity;
- private key mode `0600`, owned by the execution identity;
- known-hosts mode `0600`, owned by the execution identity;
- strict host-key checking;
- no existing final archive;
- no stale partial archive.

The helper first obtains source metadata with SHA-256, then streams the archive
through the restricted key while computing the target digest. Only exact size and
SHA-256 equality permits atomic promotion from the hidden partial file to the final
archive. The directory entry is fsynced.

On success the source key self-revokes and the target private key is removed.

## Rollback

The governed rollback operation may only:

- request source-key revocation when the temporary target credential still exists;
- remove the temporary target private/public key;
- remove the exact hidden partial archive.

It MUST NOT delete or overwrite the verified final archive.

A separately reviewed deployment rollback must also remove the installed helper
files and source exporter only after verifying no active transfer uses them.

## Explicit non-goals

This ADR does not authorize or implement:

- generic shell execution;
- arbitrary SSH;
- caller-selected hosts, users, paths or ports;
- credential disclosure;
- reuse of existing production SSH keys;
- production restore;
- DNS, PHP, Nextcloud app or cron changes;
- merge or deployment.

## Verification requirements

Before merge readiness:

1. exact-target policy tests pass;
2. protocol defers target identity only to the operation-specific allowlist;
3. dispatcher uses fixed argv with `shell=False`;
4. MCP rejects host/path/cmd expansion;
5. helper static security tests pass;
6. full repository CI and CodeQL pass;
7. independent code/security review finds no approval bypass, credential leak,
   symlink overwrite, arbitrary command path or verified-backup deletion.

Before any deployment:

1. current main and target inventory must be re-read;
2. source forced-command deployment must be separately approved;
3. target helper deployment must be separately approved;
4. a real trusted authorization verifier must be configured;
5. rollback must be rehearsed without deleting a valid archive.

Before #113 can close, the deployed operation must produce independent evidence of
the full archive copy, checksum/readability, isolated restore validation and final
credential revocation.
