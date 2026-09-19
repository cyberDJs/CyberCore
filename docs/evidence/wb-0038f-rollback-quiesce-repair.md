# WB-0038F — Rollback Quiesce Repair Evidence

Status: IMPLEMENTED_IN_BRANCH / VERIFICATION_PENDING

## Provenance

- Repository: cyberDJs/CyberCore
- Branch: wb-0038f-rollback-quiesce-repair
- Exact base: 3884f6b605a1fb3b0003b142044485cb9ba6ecce
- Trigger: post-merge Codex P1 on PR #95 exact head 4dbb0202cf959443f768871fa299e2d370ce680f
- Authority: `APPROVE START WB-0038F REPO-ONLY ROLLBACK QUIESCE REPAIR @ 3884f6b`
- Merge authority: false
- Deployment / SSH / VPS mutation authority: false

## Confirmed defect

The WB-0038E rollback revoked new Polkit starts before deleting static wrapper files, but it did not quiesce work that had already started. A running `cybercore-vikunja-backup-install.service` could therefore continue privileged installation after rollback began, and `cybercore-vikunja-backup-run.service` could already have handed execution to `vikunja-backup.service`. The first WB-0038F repair also left the already-enabled `vikunja-backup.timer` active, allowing it to re-trigger the downstream service after a one-time inactivity check. A later exact-head review identified a second race: a `StartUnit` authorization already in flight before Polkit revocation could complete after revocation and enqueue a wrapper start after the wrapper inactivity gate. A subsequent review found that unmasking after managed-wrapper removal could reveal a lower-priority or generated unit definition with the same name; merely proving that revealed unit inactive would still allow a late pre-revocation `StartUnit` to start it.

## Repair invariants

1. Remove the managed CyberCore Polkit rule and verify effective revocation first.
2. Apply runtime masks to both CyberCore wrapper unit names and verify the masks before stopping either wrapper; any late completion of a previously authorized `StartUnit` must therefore fail closed.
3. Stop each CyberCore wrapper if present and verify it is inactive or absent while the runtime masks remain active.
4. Stop `vikunja-backup.timer` if present and verify it is inactive or absent so it cannot re-trigger the downstream backup service during rollback.
5. Stop `vikunja-backup.service` if present and verify it is inactive or absent, covering work already handed off by the run wrapper.
6. Any failed mask, unverifiable mask, failed stop, or unverifiable inactive state is a hard stop; static wrapper files remain installed.
7. Remove static wrapper files only after all quiescence gates pass, then reload systemd while the runtime masks are still active.
8. Retain both runtime masks for the remainder of the current boot and verify they are still active after wrapper-file removal and systemd reload; rollback must not unmask them.
9. Runtime masks may disappear only with reboot. Because the managed Polkit authority is already revoked and in-flight systemd transactions do not survive reboot, no pre-revocation `StartUnit` can cross that boundary.
10. Rollback remains declarative and repository-only; this work block executes no systemd, SSH, VPS, credential, provider, DNS, billing, or production action.

## Required verification

- focused rollback-manifest tests;
- full CI on exact head;
- CodeQL on exact head;
- fresh independent exact-head review focused on rollback races and quiescence;
- zero unresolved valid P0/P1/P2 correctness or security findings.

Merge remains separately approval-gated.
