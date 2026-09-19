# WB-0038F — Active Wrapper Rollback Repair

Status: IMPLEMENTED_IN_BRANCH / VERIFICATION_PENDING

## Provenance

- Repository: cyberDJs/CyberCore
- Branch: wb-0038f-rollback-active-wrapper-repair
- Exact base: 3884f6b605a1fb3b0003b142044485cb9ba6ecce
- Trigger: post-merge P1 review finding on PR #95
- Authority: repository-only repair under the operator's continuing CyberCore repair scope
- Remote deployment authority: false
- VPS mutation authority: false
- Merge authority: false

## Confirmed defect

PR #95 correctly revoked the managed Polkit rule before removing static wrapper unit files, but rollback did not stop an already-running governed wrapper. Revoking Polkit prevents new starts; it does not terminate a root oneshot already in progress. A concurrent authorized installer or backup wrapper could therefore continue mutating after rollback had begun.

Fresh review of the first WB-0038F repair found two additional boundary requirements:

- stopping `cybercore-vikunja-backup-run.service` alone does not cancel an already-submitted `vikunja-backup.service` job;
- rollback must not stop an arbitrary locally replaced, transient, shadowed, or drop-in-modified unit merely because it occupies a managed wrapper name.

## Repair invariant

Rollback ordering is now:

1. remove the managed Polkit rule if exact;
2. verify effective privilege revocation;
3. verify the loaded/effective identity of both wrapper units against their exact repository source of truth, rejecting transient occupation, shadowing, drop-ins, or drift;
4. stop and wait for `cybercore-vikunja-backup-install.service`;
5. stop and wait for `cybercore-vikunja-backup-run.service`;
6. only then remove either static wrapper unit file;
7. reload systemd after both wrapper files are removed.

`VERIFY_SYSTEMD_UNIT_MANAGED_EXACT` is fail-closed by contract: rollback must halt before controlling a wrapper whose loaded fragment/effective configuration cannot be proven to match the managed static unit.

`STOP_SYSTEMD_UNIT_AND_WAIT` is fail-closed by contract: rollback must not advance to wrapper-file removal unless the verified managed wrapper is inactive and no start job remains active.

The generated `vikunja-backup.service` includes `PartOf=cybercore-vikunja-backup-run.service`, binding an in-flight backup service to the governed run wrapper so stopping that wrapper also stops the spawned mutation rather than only killing the waiting `systemctl start` client.

## Regression coverage

`tests/test_bootstrap_manifest.py` asserts:

- both exact managed-wrapper identity checks exist and carry repository source-of-truth bindings;
- verified privilege revocation precedes both identity checks;
- each identity check precedes its stop-and-wait action;
- both stop-and-wait actions exist with exact static wrapper names;
- each stop action precedes removal of its wrapper;
- both wrappers are stopped before either wrapper file is removed;
- the generated backup service is lifetime-bound to the governed run wrapper with `PartOf=`.

## Scope boundary

This repair changes repository artifacts only. It does not stop any live service, deploy the bootstrap, mutate a VPS, modify credentials, or authorize production execution.

## Required verification

- exact-head CI;
- exact-head CodeQL;
- fresh independent exact-head review;
- zero unresolved valid P0/P1/P2 findings before merge readiness.

Merge remains separately approval-gated.
