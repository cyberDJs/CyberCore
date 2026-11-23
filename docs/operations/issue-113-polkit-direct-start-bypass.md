# CyberCore #113 — direct Polkit unit-start bypass blocks runtime activation

Status: security finding; no production deployment approval. Source evidence revalidated against main b6f0d686d32a7abf842063aea2fc9d7ec126acc7; the Polkit policy and governed-operation mapping blobs are unchanged from the original finding baseline.

## Source-level mechanism

The candidate file deploy/cybercore-exec-nextcloud-r1/cybercore-exec.policy returns polkit.Result.YES for user cybercore-exec, action org.freedesktop.systemd1.manage-units, verb start, and either cybercore-nextcloud-r1-transfer.service or cybercore-nextcloud-r1-rollback.service.

The dispatcher src/cybercore/execution/server/dispatcher.py separately checks an exact short-lived authorization with FileBoundExecutionAuthorizationVerifier before running an allowlisted systemctl start operation. A process running as cybercore-exec can request direct systemd start without going through dispatcher approval, because the Polkit rule checks only UID/action/unit/verb, not the approval. Noninteractive nologin shell does not prevent local D-Bus calls by an existing process of this UID.

This source-level bypass design is not evidence of a live compromise. On the target, Polkit and systemd activation candidates are not installed. Still, do not activate this policy.

## Security impact and remediation design

Direct unit start bypasses dispatcher approval checks and their audit binding. Transfer wrapper's private source key, host pin, source checksum and directory checks do not replace start authorization. Direct rollback invocation could remove credential/partial transfer artifacts without exact dispatcher approval.

Require a separately reviewed privilege boundary with explicit approval validation, fixed allowed units and operations, peer UID verification and protection against replay. Do not grant the service Unix identity unconditional systemd manage-units start through Polkit. Either use a very narrow root-owned authorization broker or an equivalent reviewed launcher, with direct service UID start denied.

Tests required: unapproved direct systemd transfer start DENY, direct rollback DENY, wrong/missing/expired/action-mismatched approval DENY, approved exact action allow only once, replay DENY, unrelated unit DENY; preserve operator SSH and root recovery. No generic shell or broad sudo.

## Diagnostic gate

scripts/nextcloud_r1_privilege_bypass_preflight.py is a conservative read-only static checker. Current bundled policy returns BLOCKED_DIRECT_UNIT_START with exit 2. A future no-match result is only STATIC_CANDIDATE_REQUIRES_RUNTIME_PROOF; it is never activation permission and exits non-zero. Exit 0 is reserved for a future explicit RUNTIME_VERIFIED_PASS state that this static checker cannot currently produce. This tool is not a complete JavaScript/Polkit parser.

## Other blockers

Eight modules are installed and root-verified, while runtime credential/state directories remain absent. Current final backup path is root:root 0700, which the nonroot transfer User=cybercore-exec cannot use without another approved ownership design. SSH has early Include and requires offline root sshd -t/-T tests with rollback before any reload. Source SFTP fingerprint, constrained identity and archive SHA-256 remain unverified; no transfer or restore is authorized.

No production mutations in this PR. Independent exact-head review, CI and explicit deployment authority are required for any activation.
