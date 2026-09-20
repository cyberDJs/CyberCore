# WB-0038F — Active Wrapper Rollback Repair

Status: IMPLEMENTED_IN_BRANCH / FINAL_REVIEW_PENDING

## Provenance

- Repository: cyberDJs/CyberCore
- Branch: wb-0038f-rollback-active-wrapper-repair
- Pull request: 97
- Exact base: 3884f6b605a1fb3b0003b142044485cb9ba6ecce
- Trigger: post-merge P1 review finding on PR #95
- Authority: repository-only repair under the operator's approved hotfix scope
- Remote deployment authority: false
- VPS mutation authority: false
- Merge authority: false

## Confirmed defect chain

PR #95 revoked the managed Polkit rule before removing static wrapper unit files, but rollback did not stop an already-running governed wrapper. Revoking Polkit prevents new starts; it does not terminate a root oneshot already in progress.

Fresh review of WB-0038F then exposed five related rollback-boundary requirements:

1. stopping `cybercore-vikunja-backup-run.service` did not necessarily stop the separate `vikunja-backup.service` job it had already submitted;
2. rollback must not stop a transient, shadowed, drop-in-modified, or otherwise locally replaced unit merely because it occupies a managed wrapper name;
3. an enabled `vikunja-backup.timer` can independently start `vikunja-backup.service` during or after rollback, so wrapper-only quiescing is insufficient;
4. rollback must stop and wait for an already-running installer wrapper before quiescing the generated timer/service, otherwise the installer can re-enable the timer after quiescence;
5. direct backup execution must preserve the former Docker startup dependency and ordering.

An interim `PartOf=cybercore-vikunja-backup-run.service` edge in the generated backup service was retained only as defense-in-depth. Rollback safety must not depend on that edge being present in an older already-loaded unit.

## Final repair invariant

Rollback ordering is now:

1. remove the managed Polkit rule if exact;
2. verify effective privilege revocation;
3. verify the loaded/effective identity of `cybercore-vikunja-backup-install.service`;
4. stop and wait for the installer wrapper, preventing it from re-materializing or re-enabling generated backup units during rollback;
5. verify `vikunja-backup.timer` is either absent or exactly the managed canonical template;
6. verify `vikunja-backup.service` is either absent or exactly the managed canonical template;
7. disable and wait for `vikunja-backup.timer` if present;
8. stop and wait for `vikunja-backup.service` if present;
9. verify the loaded/effective identity of `cybercore-vikunja-backup-run.service`;
10. stop and wait for the run wrapper;
11. only then remove either static wrapper unit file and reload systemd.

The optional generated units are fail-closed: absence is a safe no-op, an exact managed unit may be quiesced, and any drift/mismatch aborts rollback before unit control or wrapper teardown.

## Canonical generated-unit templates

The generated units now have explicit repository sources of truth:

- `deploy/cybercore-exec/vikunja-backup.service`
- `deploy/cybercore-exec/vikunja-backup.timer`

Bootstrap deploys these templates root:root mode 0600 to:

- `/usr/local/libexec/cybercore-exec/vikunja-backup.service.template`
- `/usr/local/libexec/cybercore-exec/vikunja-backup.timer.template`

The root-owned installer reads those templates when materializing `/etc/systemd/system/vikunja-backup.service` and `vikunja-backup.timer`. This gives rollback an exact identity source rather than relying on embedded text or unit names alone.

## Governed run lifetime

The governed run wrapper directly executes the fixed root-owned executable:

`ExecStart=/usr/local/sbin/vikunja-backup`

The backup therefore runs inside the verified wrapper's own systemd cgroup. `STOP_SYSTEMD_UNIT_AND_WAIT` stops and waits for the actual governed backup process rather than only a waiting `systemctl start` client.

The wrapper preserves Docker startup semantics with:

`Requires=docker.service`
`After=docker.service`

It keeps `ProtectSystem=strict` and grants only the required write surface:

`ReadWritePaths=/opt/backups/vikunja`

The generated backup service retains `PartOf=cybercore-vikunja-backup-run.service` as defense-in-depth, but rollback correctness no longer depends on it.

## TDD evidence

### Wrapper lifetime regression

RED: `cfa382ef74bd8c586bebb087f6ac43cd9ef082a8`

The regression test failed because the wrapper delegated to:

`ExecStart=/usr/bin/systemctl start vikunja-backup.service`

instead of directly executing the backup.

GREEN behavior was introduced at `3e6a491005932e3097eb218b4f544d58bc07f087`.

### Scheduled backup rollback regression

RED: `6e69aa06c2b30efd86c2fd6be6c53519fbeb1867`

GitHub Actions failed on the new regression coverage with the expected missing-contract failures:

- missing `vikunja-backup-service-template`;
- missing `verify-vikunja-backup-timer-managed-or-absent`.

The test-only contract was further tightened at `38098b0e74372ebbf9798f95bdf1de02bd611966` before production implementation.

GREEN final implementation head before this evidence-only update:

`1b7b057f584c9ee52d47f7ef102feab65d427338`

Exact-head verification:

- CI #900: PASS
- CodeQL #901: PASS
- Python 3.11: PASS
- Python 3.12: PASS
- Python 3.13: PASS
- Python 3.14: PASS
- quality: PASS
- package: PASS

### Installer race and Docker ordering regression

RED: `bdc85dc6cedb1e0af35a653ed4d691a59ac8be26`

GitHub Actions failed with the expected missing-contract evidence:

- `Requires=docker.service` was absent from the direct run wrapper;
- rollback still placed `stop-vikunja-backup-install-wrapper` after generated timer/service quiescence.

GREEN production changes:

- `06a6e30d0124ea018ab973844a9f486f2b285e55` — installer wrapper moved ahead of generated-unit quiescence;
- `dd63e841569ba06145b27b54e4301d155951efce` — Docker `Requires=` / `After=` restored for direct backup execution;
- `812a8e2279f598d33a539d6c9f4e6de42b0312d3` — stale superseded test-ordering assertion removed after the production contract changed.

Exact-head verification at `812a8e2279f598d33a539d6c9f4e6de42b0312d3`:

- CI #962: PASS
- CodeQL #963: PASS
- Python 3.11: PASS
- Python 3.12: PASS
- Python 3.13: PASS
- Python 3.14: PASS
- quality: PASS
- package: PASS

## Regression coverage

`tests/test_bootstrap_manifest.py` verifies:

- root-owned canonical service/timer template deployment;
- installer consumption of those templates;
- optional generated timer/service identity checks before control;
- timer disable-and-wait before service stop;
- exact install-wrapper identity verification and stop before generated timer/service quiescence;
- timer disable-and-wait before generated service stop;
- generated service stop before run-wrapper identity verification/teardown;
- exact wrapper identity verification before each wrapper stop;
- wrapper stop before wrapper file removal;
- direct governed backup execution inside the run wrapper cgroup;
- preserved Docker startup dependency and ordering for the direct runner;
- strict backup write-surface confinement.

## Scope boundary

This repair changes repository artifacts only. It does not stop any live service, deploy the bootstrap, mutate a VPS, modify credentials, or authorize production execution.

## Remaining gate

- exact-head CI and CodeQL after this evidence/SOT-only update;
- fresh independent exact-head Codex review;
- fresh exact-head security review;
- zero unresolved valid P0/P1/P2 findings before merge readiness.

Merge remains separately approval-gated.
