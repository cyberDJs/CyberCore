# ADR-0016 candidate — CyberCore #113 privilege-boundary for off-host Nextcloud recovery

Status: PROPOSED; architecture only. No deployment or authority grant.
Source baseline: CyberCore main b6f0d686d32a7abf842063aea2fc9d7ec126acc7 (2026-11-23).
Dependent review: Draft PR #180 (the static detection of unsafe direct Polkit start) remains independent and is not merged by this design.

## Problem

Current candidate Polkit policy permits systemd manage-units/start by the low-privilege cybercore-exec UID for transfer and rollback. That permission is independent of the dispatcher FileBoundExecutionAuthorizationVerifier; a process running under that UID can request unit starts without passing dispatcher approval. Neither sshd ForceCommand nor a nologin shell is a local systemd authorization boundary. This candidate MUST NOT be installed.

## Decision proposal

1. Do not grant systemd manage-units to cybercore-exec in Polkit; reject any direct start/restart/stop of both fixed units by this account. Prefer no rule at all until a separately reviewed broker replaces the unit-start path.
2. Use a root-owned local privilege broker with a fixed Unix domain socket. Peer identity is checked using kernel SO_PEERCRED (not caller-supplied UID, PATH, command or environment). Socket access is restricted to the named service UID by a root-owned parent and exact ACL, never to broad groups.
3. The broker accepts exactly two action names: transfer and local-containment rollback. Status/verification are read-only, separate and do not require the broker. No arbitrary command, unit name, path, flags or shell input is accepted.
4. The broker independently validates a root-created, short-lived exact-action approval manifest and a supplied authorization reference digest with constant-time comparison. Bind issue=113, target=cyberskills-vps, action, plan ID/revision, operation ID, source release/commit identity and expiration. Manifest access MUST be fd-based: open a preconfigured root-owned parent directory once, resolve only a fixed leaf name with `openat`/`dir_fd` plus `O_NOFOLLOW|O_CLOEXEC`, then validate the already-open fd with `fstat` before reading. Require a regular file owned by root, no group/world write bits, expected link count, bounded size and no unexpected file type. Hash and parse bytes read from that verified fd; do not authorize from a pathname that is re-opened after validation. Apply the same dirfd/no-symlink discipline to receipts and journal state.
5. Prevent replay: under a root-only lock acquire the action authorization, check a durable operation-ID consumption journal, and persist PREPARED before dispatch. Journal writes MUST use the verified root-owned directory fd, create a fresh temporary regular file with `O_CREAT|O_EXCL|O_NOFOLLOW` and restrictive mode, fsync the file, atomically rename within the same directory, then fsync the directory. Never follow or replace attacker-controlled symlinks. Execute only the fixed systemctl start operation, then persist SUCCEEDED or FAILED plus invocation receipt with the same durable-write discipline. An interrupted PREPARED operation must never run twice automatically. Recovery is a separately authorized reconcile using verified systemd state.
6. Broker invokes systemctl under its root identity only after gate success; systemd static units themselves continue to run as cybercore-exec and maintain sandbox restrictions. The privileged broker cannot execute user-supplied commands. Avoid shell=True, sudo wildcard matching and command interpolation.
7. The broker may run as a fixed systemd socket/service pair, but start/enable these only in a separately approved transaction. Before activation, validate identities, socket ACL, root-owned code/content SHA, unit policy, Polkit effective denial, process privilege, and safe rollback. Record full unit and policy snapshots. Existing operator SSH and rescue console remain available.
8. Keep source keys, host trust, remote archive hash and transfer activation in a separate credential/transfer authorization gate. Never start transfer with synthetic or missing source evidence.

## Threat model and negative evidence requirements

| Threat | Required proof before deploy |
|---|---|
| Direct systemctl start by cybercore-exec | DENY for transfer and rollback with no broker |
| Unrelated uid or group reaches broker | DENY at filesystem ACL and SO_PEERCRED |
| Wrong or missing approval, mismatched source, expired TTL | DENY, no unit-start side effect |
| Wrong operation, unit, plan or target | DENY; fixed operation allowlist |
| Replay or concurrent duplicate | At most one dispatch, including after crash/restart |
| Partial write, manifest/journal symlink, path/owner/inode drift | DENY before dispatch; verified dirfd/open-fd evidence only |
| Broker loses power in PREPARED | No automatic repeat; independent reconciliation gate |
| Approved transfer or rollback | Exactly one dispatch with durable receipt and independent service state check |
| Unauthorized rollback or cleanup | DENY; never delete verified final archive |
| Existing operator SSH access | Continues to work after any later sshd change and rollback |

## Atomic activation phases and authority

A. Code-only install already verified: 8 files, root-owned directory ACLs; no live SSH/systemd/Polkit.
B. Candidate implementation and tests in an isolated branch: broker, static socket/units, denial tests and crash recovery with synthetic fixtures; requires independent security review and exact-head CI.
C. Separately authorized root-only staging on target: verify release hash, owner/ACL and unit syntax, perform read-only effective Polkit and sshd -t/-T tests, prove out-of-band access, record pre-state and rollback.
D. Explicit broker-only activation: install static code and protected state without enabling transfer; prove direct systemd starts denied, unapproved broker requests denied, one-shot approved synthetic action never launches a real transfer.
E. Source SFTP trust and constrained credential provisioning plus independently observed SHA-256 and exact archive size; separately approved transfer operation only after complete evidence.

Rollback for stage D: disable/remove the broker socket, restore exact prior unit/Polkit/SSH definitions and ACL state from verified receipt. Do not remove the 8 installed verified modules, historical receipts, existing final archive, or other backups. Any credential revocation is a separately evidenced source-side operation.

## Alternatives considered

- Retain current Polkit fixed-unit whitelist: REJECT, bypasses dispatcher approval.
- Use unrestricted sudo for systemctl start: REJECT, same authorization problem with a broader attack surface.
- Grant a root-owned setuid launcher: DEFER/REJECT as default; significant parsing and filesystem attack surface, difficult review.
- Root-owned SO_PEERCRED Unix socket broker: PREFERRED candidate; bounded protocol and replay-resistant root-side authorization, but adds a resident service and must be independently validated.

## Open gates

- Design still needs review of exact broker process/socket lifecycle, privilege separation, fd-based manifest/journal implementation and replay semantics.
- No root implementation or live activation is included in this ADR.
- Need documented ownership design for /var/backups/cybercore/nextcloud-r1-113/2026-10-13 currently root:root 0700; transfer User=cybercore-exec must not require broad chmod.
- Missing /var/lib/cybercore-exec-nextcloud-r1/credentials and /state directories.
- Independent source SFTP fingerprint, restricted source credential, and SHA-256 of the fixed 13,259,294,576-byte archive are outstanding.

Acceptance: this ADR may be merged as documentation only after independent review, but its merge NEVER authorizes production changes or bypasses further approvals.
