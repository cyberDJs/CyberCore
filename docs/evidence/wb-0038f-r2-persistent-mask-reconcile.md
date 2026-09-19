# WB-0038F-R2 — Persistent-Mask Rollback Reconciliation

Status: IMPLEMENTED_IN_BRANCH / VERIFICATION_PENDING

## Provenance

- Repository: cyberDJs/CyberCore
- Branch: wb-0038f-r2-persistent-mask-reconcile
- Exact base: 1a22865747d0d8ea2bf97d3b455534b610a66a90
- Supersedes repair candidate: PR #98 / WB-0038F on stale base 3884f6b605a1fb3b0003b142044485cb9ba6ecce
- Trigger: Codex P1 on PR #98 exact head 91ee764b7292e3258a8995d3963079a41eb9e2dd
- Authority: `APPROVE START WB-0038F-R2 PERSISTENT-MASK RECONCILE @ 1a228657`
- Merge authority: false
- Deployment / SSH / VPS / credential / provider authority: false

## Confirmed defect

Runtime masks protect only the current boot. If a lower-priority or generated unit
fragment exists under either CyberCore wrapper name, reboot removes the runtime
mask and may expose an enabled root unit without requiring a new Polkit-authorized
request. Therefore reboot is not a safe implicit unmask boundary.

## Repair invariants

1. Revoke the managed CyberCore Polkit rule and verify effective revocation.
2. Runtime-mask both CyberCore wrapper names and verify those masks before stopping either wrapper.
3. Stop and verify inactive-or-absent for both wrappers, `vikunja-backup.timer`, and `vikunja-backup.service`.
4. Remove managed wrapper files only after all quiescence gates pass.
5. While runtime masks are still active, create persistent masks for both wrapper names.
6. Persistent-mask creation is idempotent only for the exact existing mask; a conflicting path fails closed.
7. Verify both persistent masks before systemd reload, then reload and verify both names remain masked.
8. Rollback never un-masks either wrapper name. Persistent masks survive reboot and shadow hidden lower-priority/generated fragments.
9. Future install must treat a persistent mask as an unsafe occupied wrapper name and must not remove it automatically.
10. This work block is declarative and repository-only; no systemd, SSH, VPS, credential, provider, DNS, billing, or production action is executed.

## Reconciliation

The R2 branch starts directly from current canonical `main@1a22865747d0d8ea2bf97d3b455534b610a66a90`. It does not
carry forward PR #98's stale `.cybercore/project.yaml` edits, avoiding regression
of the PR #96 source-of-truth closeout.

## Required verification

- focused rollback-manifest tests;
- full exact-head CI;
- exact-head CodeQL;
- fresh exact-head Codex review and security review;
- zero unresolved valid P0/P1/P2 correctness or security findings.

Merge remains separately approval-gated.
