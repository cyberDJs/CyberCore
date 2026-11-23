# CyberCore issue #113 — Phase-B active-runtime readiness gate

Status: **candidate only**. This change checks root-owned staged source integrity and existing destination collisions. It **does not activate** the runtime or authorize any root mutations.

## Ground truth (2026-11-23)

- Canonical CyberCore main at `59db348d5fe531158db0b0918b04b81de64ecf35`.
- Stage-A immutable root-owned release `/opt/cybercore-113/releases/1cbe25ffd941738c4cc0b157914daa74a95885a6` previously independently verified (12 staged files plus manifest SHA-256 `14138040ec7758f7b68c434198fa24c872a0da90ae109459d5a011d525e1b6fe`).
- Root offline SSH candidate parser test returned `OFFLINE_SSHD_CANDIDATE_VERIFIED` on real target, with preserved root and cybercore-deploy operator profiles. No live reload performed.
- Rechecked target through pinned nonroot SSH: `cybercore-exec` absent, active libexec absent, transfer systemd unit not found. Existing polkit directory root-only and not readable to broker.

## Gate provided by this PR

`scripts/nextcloud_r1_activation_readiness.py` is read-only. On an independently authorized root console it verifies:

1. Exact `source_commit`, target, issue and no-activation identity of the Phase-A release.
2. Root-owned 0700 release directory; each of the 12 files root-owned 0600 with digest exactly matching the recorded manifest; no extra symlinks/files.
3. Root-only manifest ownership/mode and computed SHA-256.
4. Presence or absence of a fixed list of active-path collisions, including libexec, SSH include, two systemd units, Polkit rule, and Nextcloud approval manifest.

It prints `READY_FOR_SEPARATE_ACTIVATION_DESIGN` only if every check passes and no listed active destination exists; otherwise `BLOCKED`. It never changes configuration or implies approval.

## Critical unresolved authority boundary

The target-side dispatcher runs as `cybercore-exec`, but `FileBoundExecutionAuthorizationVerifier` must **read** the short-lived root-owned approval manifest at `/etc/cybercore-exec/approvals/nextcloud-r1.json`. A directory with owner root and mode 0700 prevents the service user from traversing the path, so every governed mutation would be denied. The deployment candidate must specify and test a restricted owner/group readability design (e.g. root:cybercore-exec 0750 parent and root:cybercore-exec 0640 manifest), while keeping root-only creation, no group writes, fixed exact-action authorization, expiration, and rollback. Do not weaken the verifier's ownership or anti-symlink protections, and do not create manifests based only on this proposal.

The staged `libexec/*.py` files are root-owned 0600 inside a root-only 0700 release. They cannot be executed directly as the unprivileged dispatcher. The separately reviewed activation installer must copy exact pinned contents to root-owned non-writable importable paths with no unexpected aliases and permissions that allow only the intended service-user reads, while enforcing no generic shell or arbitrary command execution.

## Required next isolated implementation

Produce a separate, exact-head reviewed activation transaction with:

- explicit target identity and root authorization manifest binding exact SHA/action, TTL, expected live path absence and rollback evidence;
- locked noninteractive `cybercore-exec` UID with no sudo and a trusted key distribution procedure;
- minimal root-owned executable/readonly libexec layout with dispatcher imports and allowlisted operations only;
- root-owned/group-read-only approvals boundary and denied unauthorized requests;
- static systemd unit + polkit validation for only two fixed units; systemd `--no-block` must not start any transfer absent separate exact transfer approval;
- SSH subsystem early Include and fixed Match User end-of-file with full actual `sshd -t/-T`, operator session preservation and out-of-band console rollback;
- negative tests for other SSH identities, unknown targets/operations, missing/expired manifests and other unit starts;
- independent postflight and rollback/restore of *each exact prior file*, without removing completed backups.

The source-host fingerprint, restricted SFTP credential and independently observed 13.2 GB archive hash are **not yet verified** and block transfer/restore.

## Execution

Read-only targeted regression:

```sh
python3 -m unittest discover -s tests -p test_nextcloud_r1_activation_readiness.py -v
```

Root-console readiness gate (after exact script SHA review and authorization to run read-only diagnostics):

```sh
python3 -I scripts/nextcloud_r1_activation_readiness.py
```

The root gate is not claimable as completed until the operator reports its output. **Do not merge, activate, reload, provision credentials, transfer or restore solely based on this runbook.**
