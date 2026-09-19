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

## Repair invariant

Rollback ordering is now:

1. remove the managed Polkit rule if exact;
2. verify effective privilege revocation;
3. stop and wait for `cybercore-vikunja-backup-install.service`;
4. stop and wait for `cybercore-vikunja-backup-run.service`;
5. only then remove either static wrapper unit file;
6. reload systemd after both wrapper files are removed.

`STOP_SYSTEMD_UNIT_AND_WAIT` is fail-closed by contract: rollback must not advance to wrapper-file removal unless the requested wrapper is inactive and no start job remains active.

## Regression coverage

`tests/test_bootstrap_manifest.py` asserts:

- both stop-and-wait actions exist with exact static wrapper names;
- verified privilege revocation precedes both stop actions;
- each stop action precedes removal of its wrapper;
- both wrappers are stopped before either wrapper file is removed.

## Scope boundary

This repair changes repository artifacts only. It does not stop any live service, deploy the bootstrap, mutate a VPS, modify credentials, or authorize production execution.

## Required verification

- exact-head CI;
- exact-head CodeQL;
- fresh independent exact-head review;
- zero unresolved valid P0/P1/P2 findings before merge readiness.

Merge remains separately approval-gated.
