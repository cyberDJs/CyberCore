# CyberCore Nextcloud R1 governed transfer candidate

Status: repository-only candidate for issue #113. This directory is not a deployment authorization.

## Fixed scope

The candidate has one source recovery point and one off-host destination:

- source host: `162.250.126.107`
- source account: `eimyherr`
- source archive: `/home/eimyherr/softaculous_backups/nextcloud.586_28528.2026-10-07_18-30-01.tar.gz`
- expected size: `13,259,294,576` bytes
- execution target: `cyberskills-vps` / `162.35.186.106`
- destination: `/var/backups/cybercore/nextcloud-r1-113/2026-10-13/`

No hostname, user, source path, destination path, executable, shell text, or SSH option is supplied by the MCP caller.

## Runtime contract

The target-side `cybercore-exec` subsystem is configured with the exact target id `cyberskills-vps`.

Supported operations are:

- `nextcloud.r1.offhost.transfer` — mutating; starts the fixed static systemd service with `--no-block`;
- `nextcloud.r1.offhost.status` — read-only systemd state;
- `nextcloud.r1.offhost.verify` — read-only checksum/gzip/tar component verification.

Mutating execution requires an exact short-lived approval manifest on both sides of the transport.
The raw authorization reference is never stored in the manifest; only its SHA-256 is bound to the
exact `operation_id + operation + target + plan_id + plan_revision` tuple. Missing, malformed,
expired, overly long, wrong-owner, writable, symlinked, or mismatched manifests fail closed.

Fixed manifest paths:

- Johnny Work client side: `/etc/cyberdjs-room/approvals/nextcloud-r1.json`
- CyberSkills server side: `/etc/cybercore-exec/approvals/nextcloud-r1.json`

The default verifier remains deny-all for every other target.



## Exact approval manifest

The manifest is an integrity/authority artifact, not a credential or secret. A deployment run may
create it only after a fresh operator approval bound to the exact action. The parent directory and
file must be owned by root and not writable by group or others. Maximum approval lifetime is one
hour.

Schema:

```json
{
  "schema_version": 1,
  "approval_id": "<audit identifier>",
  "operation_id": "<exact operation id>",
  "operation": "nextcloud.r1.offhost.transfer",
  "target_id": "cyberskills-vps",
  "plan_id": "<exact plan id>",
  "plan_revision": "<exact revision>",
  "authorization_reference_sha256": "<sha256 of raw approval reference>",
  "issued_at": "<UTC Z timestamp>",
  "expires_at": "<UTC Z timestamp, max +1h>"
}
```

No raw approval text belongs in this file. The server entrypoint automatically selects this
file-bound verifier only for `cyberskills-vps`; `tasks.cyberdjs.org` remains deny-all unless
its own separately reviewed verifier exists.

## Credential boundary

The repository does not contain or create a private key.

Before deployment, a separate approved credential-provisioning step must create a dedicated transfer identity at:

`/var/lib/cybercore-exec-nextcloud-r1/credentials/source_ed25519`

a pinned source host-key file at:

`/var/lib/cybercore-exec-nextcloud-r1/credentials/known_hosts`

and a pre-transfer source checksum evidence file:

`/var/lib/cybercore-exec-nextcloud-r1/credentials/source_archive.sha256`

All three files must be owned by `cybercore-exec`, mode `0600`. The checksum file is not a secret,
but it must be produced from an independently observed SHA-256 of the exact fixed source archive
before transfer. The transfer fails closed if it is absent, malformed, or does not match the
off-host bytes.

The source-side public key should be constrained to file transfer only (for example an OpenSSH `restrict,command="internal-sftp"` authorized-key restriction) and the deployment must verify that the shared-hosting SSH implementation actually enforces the restriction. If it cannot be proved, deployment is BLOCKED.

Private-key bytes, host-key material, passwords, tokens and raw authorization references must never be returned through MCP, GitHub evidence or logs.

## Installation plan

A separate deployment approval must:

1. verify current target identity and drift;
2. install the common governed dispatcher/authorization/protocol/operations artifacts;
3. install `nextcloud_r1_transfer.py` as `/usr/local/libexec/cybercore-exec-nextcloud-r1/transfer.py`;
4. install `nextcloud_r1_verify.py` as `/usr/local/libexec/cybercore-exec-nextcloud-r1/verify.py`;
5. create credential/state/backup directories as `cybercore-exec:cybercore-exec`, mode `0700`;
6. install the static systemd unit and the narrow Polkit rule;
7. install the target-bound sshd snippet;
8. provision the dedicated restricted source credential through an approved secret channel;
9. independently compute the exact source archive SHA-256 and provision `source_archive.sha256`;
10. create a dedicated positive non-root Unix identity for the Johnny Work frontend and grant only
    that UID the minimum socket ACL needed to reach `johnny-work.sock`;
11. after a fresh exact operator approval, create matching root-owned short-lived approval manifests
    at the fixed client/server paths without storing raw approval text;
12. validate sshd, Polkit, Unix peer UID enforcement, socket ACLs and approval-file ownership/modes;
13. independently verify Eimy, Johnny Moderator and the broker UID cannot reach the governed handler;
14. keep mutation disabled if peer credentials, narrow socket ACLs, approval provenance or manifest
    integrity cannot be proven.

## Rollback / credential revocation

Rollback is fail-closed and requires separate deployment authority. Order:

1. remove/expire both Nextcloud R1 approval manifests so no new mutating start can authorize;
2. stop/wait for `cybercore-nextcloud-r1-transfer.service`;
3. revoke the dedicated public key on the source host;
4. verify the revoked key can no longer authenticate;
5. remove the target-side private key and dedicated known-hosts file;
6. remove the Nextcloud R1 Polkit rule and verify privilege revocation;
7. remove the static unit and helper scripts;
8. remove the target-specific sshd snippet, validate sshd, then reload;
9. remove the MCP handler and dedicated Johnny Work socket ACL/runtime identity binding;
10. preserve the completed off-host archive and non-secret transfer receipt as recovery evidence unless a separate backup-retention decision authorizes deletion;
11. verify no temporary approval, credential or transfer process remains.

Rollback never deletes the only known-good backup as a cleanup side effect.
