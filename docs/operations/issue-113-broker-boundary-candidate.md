# CyberCore #113 — SO_PEERCRED + fd-bound approval candidate

Status: CODE-ONLY SECURITY CANDIDATE. No listener, daemon, systemd socket/service, Polkit/SSH mutation, credential provisioning, SFTP access or real transfer/restore.

This successor builds on the merged inert transaction core and ADR-0016.

Implemented boundary:

- one already-accepted AF_UNIX SOCK_SEQPACKET request only;
- peer UID comes from kernel SO_PEERCRED and is checked before approval lookup;
- request schema contains only short action + SHA-256 approval-reference digest; caller cannot choose operation ID, target, plan, source or unit;
- approval manifest is opened through a trusted directory fd using O_NOFOLLOW/O_CLOEXEC and validated with fstat for owner/type/write bits/link count/size;
- manifest binds issue 113, target, action, plan/revision, operation ID, source identity, boot ID and monotonic issued/deadline values;
- one approval-store instance latches monotonic provider failure/regression and supplies the same sampler to the core for pre-PREPARED and post-PREPARED effect-boundary checks;
- approval manifest SHA-256 may be persisted, but no raw approval reference is accepted on the wire or written to broker transaction state;
- fixed operation argv remains owned by the inert core and regression-tested there against canonical server operation specs.

Synthetic/offline tests cover SO_PEERCRED success and mismatch, SOCK_STREAM denial, extra/duplicate request keys, manifest symlink/mode rejection, symlinked approval directory, boot/source/plan/reference mismatch, monotonic expiry/TTL/regression, deadline crossing after PREPARED, duplicate manifest keys and oversized requests.

Remaining deployment blockers:

1. Broker state journal is still the inert core's path-based root-private directory implementation; ADR-0016 requires final dirfd/no-symlink parent-chain hardening and atomic journal replacement semantics before privileged activation.
2. There is still no listener/CLI/systemd service or socket unit. Nothing in this candidate can bind a production endpoint by itself.
3. No direct systemd denial test under the real cybercore-exec UID has been executed.
4. No production approval manifest, credential, SFTP trust, source archive hash, transfer or restore is authorized.
5. PREPARED reconciliation remains a separately authorized operation; no automatic retry is introduced.

Merge of this candidate means only that the code boundary is available for further reviewed integration. It is not deployment approval.
