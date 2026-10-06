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

Runtime masks protect only the current boot. The first R2 persistent-mask design
then exposed two additional failure modes in exact-head review:

1. a partial rollback could create the first persistent mask and fail before the
   second, after which replay would encounter that mask at the managed wrapper
   path and could fail before protecting the second wrapper;
2. a normal persistent mask in `/etc/systemd/system` does not override a main
   unit fragment emitted into higher-priority `/run/systemd/generator.early`.

The repaired design therefore separates the managed wrapper path from a
persistent name-specific tombstone drop-in.

## Repair invariants

1. Revoke the managed CyberCore Polkit rule and verify effective revocation.
2. Runtime-mask both CyberCore wrapper names and verify those masks before stopping either wrapper.
3. Stop and verify inactive-or-absent for both wrappers, `vikunja-backup.timer`, and `vikunja-backup.service`.
4. Remove managed wrapper files only after all quiescence gates pass; replay accepts the exact managed file or absence.
5. While runtime masks are still active, install an exact tombstone drop-in for each wrapper under its `.service.d/` directory.
6. Tombstone installation accepts only absence or the exact canonical tombstone; any conflicting file fails closed.
7. Each tombstone sets an always-false start condition and `RefuseManualStart=yes`, so it augments any future main unit fragment of the same name, including an ordinary `generator.early` main fragment.
8. Verify both tombstone files exactly, reload systemd, and keep the runtime masks for the current boot.
9. Future install must verify both tombstone paths are absent before claiming either wrapper name and must never remove them implicitly.
10. Local root or a deliberately conflicting drop-in is outside the threat model; this boundary is not claimed to defend against an administrator who can rewrite systemd policy.
11. This work block is declarative and repository-only; no systemd, SSH, VPS, credential, provider, DNS, billing, or production action is executed.

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
