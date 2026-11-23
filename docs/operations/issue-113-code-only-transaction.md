# CyberCore #113 — Phase-B code-only transaction (draft)

This is a **narrow first executable transaction**, not activation. It copies exactly eight previously root-verified Stage-A Python modules into new root-owned, service-readable `/usr/local/libexec` directories. It never creates users, SSH/Polkit/systemd files, services, credentials, outbound connections, backup archives or restores.

## Why split this phase

The 12-file inert release is root-only (`0700` release, `0600` contents). A nonroot dispatcher cannot import its modules in place. Granting recursive read access to the release would unnecessarily expose approval evidence and staged code, so this change installs only eight pinned code files into distinct root-owned destinations. The root account must validate receipt and explicit action-bound approval before any write.

## Commands (not approved for live execution by this PR)

`python3 scripts/nextcloud_r1_code_transaction.py plan` — static plan, no root required.

`python3 scripts/nextcloud_r1_code_transaction.py apply` — root required, **explicit exact-source code-only approval file required**, checked for root 0600, UTC timestamp and TTL <= 1 hour. Reads pinned Stage-A SHA, copies eight verified files into two previously absent destinations. Writes root-only transaction receipt. On partial failure, compensates only paths newly created by its invocation.

`python3 scripts/nextcloud_r1_code_transaction.py verify` — root-only, compares active files against root receipt and rejects added/missing files, mode drift and content drift.

`python3 scripts/nextcloud_r1_code_transaction.py rollback` — root-only, requires **separate** root-created `code-only-rollback` approval; refuses to delete anything unless hashes/modes and exact file set still match the receipt.

## Exact live boundaries

- Stage-A source: `/opt/cybercore-113/releases/1cbe25ffd941738c4cc0b157914daa74a95885a6`; the source SHA is a compile-time constant.
- Destinations: `/usr/local/libexec/cybercore-exec` and `/usr/local/libexec/cybercore-exec-nextcloud-r1`; parent must already exist and be root-owned, non-group/world writable; **any destination collision blocks installation**.
- Root approval: `/etc/cybercore-exec/approvals/code-only-113.json` with root-only directory 0700 and file 0600; exact keys `issue`, `source_commit`, `action`, `approval_id`, `issued_at`, `expires_at`. Approval for apply has action `code-only-install`; rollback has `code-only-rollback`. The actual operator has to create the manifest using separate approved procedure. This proposal grants no approval itself.
- Receipt: `/var/lib/cybercore-113-code-only.json` root 0600 with exact file digests.
- Output `activation_performed=false` is literal: no SSH reload or service execution.

## Conditions before live use

Independent security review must evaluate transaction race/TOCTOU behavior, malicious symlink handling, SHA trust, root-owned parent path checks, approval creation, interrupted power recovery and rollback semantics. CI checks and at least one isolated nonroot fixture test are required; **do not execute apply on the production VPS or merge without a separately approved exact HEAD**.

An interruption after a successful directory rename but before writing the receipt may leave a partial code-only installation; operator must inspect and reconcile those paths manually rather than blindly delete. This is not yet an atomic full infrastructure activation mechanism. SSH access, systemd and Polkit still need their own separately verified activation transaction and interactive recovery channel. SFTP source fingerprint, restricted key and 13.26GB archive SHA remain unavailable; no transfer or restore is authorized.

The next improvement should address power-loss recovery with a durable root-only intent journal and explicit fail-closed reconciliation before promoting this code-only installer to live use.
