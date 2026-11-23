# CyberCore #113 — Phase B activation preflight (candidate, no deploy)

## Evidence and boundaries

The 2026-11-23 Phase-A release is staged at `/opt/cybercore-113/releases/1cbe25ffd941738c4cc0b157914daa74a95885a6` (root-owned, mode 0700, 12 code/config files and manifest). The original bootstrap reported `INERT_STAGE_VERIFIED`; a recomputed manifest SHA matched the user's root receipt.

On the target `162.35.186.106`, `/etc/ssh/sshd_config` includes `/etc/ssh/sshd_config.d/*.conf` at line 12, ahead of global directives (`PermitRootLogin`, `PasswordAuthentication`, `Subsystem sftp`). The earlier candidate `cybercore-exec.subsystem.conf` includes `Match User` and `Match all`. **Do not copy it to the early include directory.** Its position can invalidate later global directives or change match scope.

Phase B must remain a separate, exact-head review and independent authorization. The current PR provides **only** a split config proposal and static, read-only preflight; it cannot activate sshd, Polkit or systemd.

## SSH design

- `sshd-subsystem-only.conf`: exact `Subsystem cybercore-exec` registration; no `Match` directives. Intended for an early included file only after offline and live config validation.
- `sshd-match-tail.conf`: dedicated `Match User cybercore-exec` block with only required transport restrictions and a fixed `ForceCommand`. **Append only to the end of primary sshd config**, after all global directives and any existing Match blocks. For any preexisting Match directive, stop and review the full policy — static checks intentionally fail closed.
- `scripts/nextcloud_r1_ssh_activation_preflight.py` compares these templates against the current primary config read-only. This is necessary, not sufficient, for safe deployment.
- The dispatcher must be tested under the exact `cybercore-exec` UID and target binding `cyberskills-vps`; invalid/unauthorized requests must be denied without side effects.

## Activation sequence (future separately authorized change)

1. Record current `sshd -T` outputs for normal operator and proposed service user, protect current SSH session, and ensure a separate console recovery path.
2. Verify host identity, source commit, release manifest file hashes and user/group collisions. Create locked noninteractive system identity `cybercore-exec` with no sudo; validate key restrictions and absence of alternate access.
3. Copy exact verified code to root-owned, readable-only libexec paths with expected Python flat-import structure. Staged mode-0600 files are **not** immediately executable by the service user; active copies need approved root:root 0644/0755 modes and safe parent ownership.
4. Create state, credential and backup paths with exact 0700 ownership. Do **not** provision source keys or enable transfer until independent source SSH host-key proof and archive SHA are available.
5. Install static unit definitions, validate with `systemd-analyze verify` and validate Polkit rule policy on the host; keep transfer disabled and do not start units.
6. Produce the complete proposed sshd config in a separate controlled test location. Run privileged `sshd -t -f <candidate>` and `sshd -T -f <candidate> -C user=...,host=...,addr=...` for both service and existing operator identities; check effective `forcecommand`, password/key policy, forwarding and preserve operator access.
7. Stage atomic, separately reversible config changes (never force restart). Validate full installed config again, then `systemctl reload ssh` only while existing root recovery session and console access are proven.
8. Independently prove intended subsystem works, unknown/mutating requests are denied absent exact approvals, operator SSH remains accessible, and privileged service cannot obtain generic shell/other unit privileges.
9. Remove staged activation artifacts or restore the exact prior SSH config and systemd/Polkit definitions on failed proof. **Do not erase completed archives or the Phase-A evidence.**

## Explicit blockers

- No trusted, independent fingerprint for source `162.250.126.107`.
- No dedicated, constrained source-side SFTP identity or remote revocation test.
- No independently observed SHA-256 of the 13,259,294,576-byte source archive.
- No approved root activation manifest bound to a reviewed exact phase-B payload.
- No tested end-to-end dispatcher negative/positive authorization matrix or completed rollback drill.

The source/archive transfer and production restore remain **BLOCKED**, regardless of Phase-B SSH plan status. This document does not grant operational authority.

## Test evidence and next review

Run: `python3 -m unittest discover -s tests -p test_nextcloud_r1_ssh_activation_preflight.py -v`. Then run all GitHub CI checks on the exact candidate head. Independent reviewer must inspect the full SSH parser result, privilege boundary, rollback and denial tests before requesting merge or root activation.
