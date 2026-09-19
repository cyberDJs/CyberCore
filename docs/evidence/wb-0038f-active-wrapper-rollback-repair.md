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

Fresh review of the first WB-0038F repair then found two additional requirements:

- stopping `cybercore-vikunja-backup-run.service` did not necessarily stop the separate `vikunja-backup.service` job it had already submitted;
- rollback must not stop a transient, shadowed, drop-in-modified, or otherwise locally replaced unit merely because it occupies a managed wrapper name.

An interim `PartOf=cybercore-vikunja-backup-run.service` binding in the generated backup unit was not sufficient as the primary safety mechanism. A host can still have an older already-loaded `vikunja-backup.service` without that dependency, or rollback can overlap installation before the new generated unit has been daemon-reloaded.

## Final repair invariant

Rollback ordering is:

1. remove the managed Polkit rule if exact;
2. verify effective privilege revocation;
3. verify the loaded/effective identity of both governed wrapper units against exact repository source of truth;
4. stop and wait for `cybercore-vikunja-backup-install.service`;
5. stop and wait for `cybercore-vikunja-backup-run.service`;
6. only then remove either static wrapper unit file;
7. reload systemd after both wrapper files are removed.

The governed run wrapper no longer launches a separate `vikunja-backup.service` through `systemctl start`. Its `ExecStart` is now the root-owned fixed executable `/usr/local/sbin/vikunja-backup`, so the backup process runs inside the verified wrapper's own systemd cgroup. `STOP_SYSTEMD_UNIT_AND_WAIT` therefore terminates and waits for the actual governed backup process rather than only a waiting systemctl client.

Because the wrapper retains `ProtectSystem=strict`, it explicitly grants only the required backup write surface with `ReadWritePaths=/opt/backups/vikunja`.

`VERIFY_SYSTEMD_UNIT_MANAGED_EXACT` is fail-closed by contract: rollback must halt before controlling a wrapper whose loaded fragment or effective configuration cannot be proven to match the managed static unit.

`STOP_SYSTEMD_UNIT_AND_WAIT` is fail-closed by contract: rollback must not advance to wrapper-file removal unless the verified managed wrapper is inactive and no start job remains active.

The generated `vikunja-backup.service` may retain `PartOf=cybercore-vikunja-backup-run.service` as defense-in-depth, but rollback correctness no longer depends on that generated unit being new, loaded, or carrying that relationship.

## TDD evidence

RED commit: `cfa382ef74bd8c586bebb087f6ac43cd9ef082a8`

The new regression test failed on GitHub Actions because the governed run wrapper still contained:

`ExecStart=/usr/bin/systemctl start vikunja-backup.service`

and did not contain:

`ExecStart=/usr/local/sbin/vikunja-backup`

GREEN commit: `3e6a491005932e3097eb218b4f544d58bc07f087`

Exact-head verification:

- CI #885: PASS
- CodeQL #886: PASS
- Python 3.11: PASS
- Python 3.12: PASS
- Python 3.13: PASS
- Python 3.14: PASS
- quality: PASS
- package: PASS

## Regression coverage

`tests/test_bootstrap_manifest.py` asserts:

- both exact managed-wrapper identity checks exist and carry repository source-of-truth bindings;
- verified privilege revocation precedes both identity checks;
- each identity check precedes its stop-and-wait action;
- both stop-and-wait actions exist with exact static wrapper names;
- each stop action precedes removal of its wrapper;
- both wrappers are stopped before either wrapper file is removed;
- the governed run wrapper directly executes `/usr/local/sbin/vikunja-backup`;
- it no longer delegates governed execution through `systemctl start vikunja-backup.service`;
- the strict wrapper sandbox explicitly permits writes only to `/opt/backups/vikunja`;
- the generated backup service retains the `PartOf=` relationship as defense-in-depth.

## Scope boundary

This repair changes repository artifacts only. It does not stop any live service, deploy the bootstrap, mutate a VPS, modify credentials, or authorize production execution.

## Remaining gate

- fresh independent exact-head Codex review;
- fresh exact-head security review;
- zero unresolved valid P0/P1/P2 findings before merge readiness.

Merge remains separately approval-gated.
