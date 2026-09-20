# WB-0038H — Canonical Rollback Hardening Evidence

Status: IMPLEMENTED_IN_BRANCH / IMPLEMENTATION_GATES_PASSED / FINAL_EXACT_HEAD_REVIEW_PENDING

## Provenance

- Repository: cyberDJs/CyberCore
- Branch: wb-0038h-canonical-rollback-hardening
- Pull request: #103
- Exact canonical base: b6c350ef40d21a3939fd0d3d6c0187a934303d31
- Trigger: post-merge audit of canonical WB-0038G / PR #102 plus source evidence from PR #97, #98 and #100
- Authority: repository-only repair
- Merge authority: false
- Remote deployment authority: false
- VPS / SSH / credential / provider / DNS / billing authority: false

## Confirmed defect: asymmetric managed-file cleanup

Canonical bootstrap installs these root-owned generated-unit templates:

- /usr/local/libexec/cybercore-exec/vikunja-backup.service.template
- /usr/local/libexec/cybercore-exec/vikunja-backup.timer.template

The canonical WB-0038G rollback manifest did not remove them. A completed rollback could therefore leave managed CyberCore artifacts behind.

WB-0038H adds exact-or-absent removal actions for both templates and retains fail-closed drift handling.

## Canonical guard defect

WB-0038G used runtime systemd masks as the first barrier before wrapper quiescence. That is not a sufficiently portable canonical invariant while the managed wrapper fragment still exists under /etc/systemd/system.

The relevant systemd model is:

- main unit files are selected through the unit load path;
- early generator output can override administrator main unit files;
- name-specific drop-ins augment the selected main unit and are parsed after it;
- administrator drop-ins under /etc/systemd/system/<unit>.d/ are therefore the appropriate persistent name-bound policy surface for this rollback contract.

WB-0038H no longer relies on MASK_SYSTEMD_UNIT_RUNTIME or MASK_SYSTEMD_UNIT_PERSISTENT actions.

## Tombstone barrier

For each governed wrapper name rollback now requires:

1. managed Polkit authority removed and effective revocation verified;
2. wrapper identity verified as the exact canonical unit or absent;
3. canonical tombstone drop-in published at:
   - /etc/systemd/system/cybercore-vikunja-backup-install.service.d/90-cybercore-rollback-tombstone.conf
   - /etc/systemd/system/cybercore-vikunja-backup-run.service.d/90-cybercore-rollback-tombstone.conf
4. publication contract:
   - accept only destination absence or an exact canonical tombstone;
   - write a same-directory temporary file;
   - make file bytes durable;
   - atomically rename into the final destination;
   - make the containing directory durable;
   - fail closed on a conflicting or partially written destination;
5. exact tombstone bytes verified;
6. systemd daemon-reloaded;
7. tombstone effectiveness verified for the wrapper name;
8. only after that barrier may rollback stop or quiesce the wrapper.

The canonical tombstone is:

```ini
[Unit]
ConditionPathExists=/dev/null/cybercore-exec-wrapper-reactivation
RefuseManualStart=yes
```

The always-false condition blocks activation regardless of whether activation is manual or dependency-driven. RefuseManualStart is retained as defense in depth for explicit starts.

## Replay and reinstall boundary

Rollback cleanup uses exact-or-absent semantics for managed files, allowing a previously completed removal step to be replayed while still failing closed on drift.

The tombstone itself is intentionally not removed by rollback.

Future bootstrap now contains explicit VERIFY_SYSTEMD_TOMBSTONE_ABSENT gates before either wrapper name is claimed. Bootstrap must not remove a tombstone implicitly. Reactivation therefore requires a separate reviewed administrative action.

## Preserved WB-0038G invariants

WB-0038H does not weaken:

- installer quiescence before generated timer/service revalidation;
- queued systemd-job drain before backup script replacement;
- timer disable before manual run-wrapper stop;
- generated timer/service exact-or-absent identity checks;
- direct governed backup execution in the verified wrapper cgroup;
- shared O_NOFOLLOW flock serialization;
- Docker Requires/After ordering;
- bounded writable filesystem surface;
- repository-only / not-deployed status.

## Regression evidence

tests/test_bootstrap_manifest.py now asserts:

- future install refuses to claim wrapper names while rollback tombstones exist;
- tombstone publication is atomic/durable by action contract;
- exact tombstones are verified before daemon-reload;
- effective tombstone verification precedes wrapper stop;
- runtime and persistent mask action types are absent from rollback;
- wrapper removal occurs only after generated-service quiescence;
- tombstones survive wrapper removal and are re-verified after reload;
- both installed generated-unit templates are removed during rollback.

## Hosted verification

Implementation head bee4b87d3f6c64aa55e001349cd53819da0a7ef7:

- CI #980: PASS
- quality: PASS
- package: PASS
- Python 3.11: PASS
- Python 3.12: PASS
- Python 3.13: PASS
- Python 3.14: PASS
- CodeQL #981: PASS

This implementation head is followed by source-of-truth/evidence changes. Final readiness requires fresh CI, CodeQL, and correctness/security review on the final exact head.

## Scope boundary

WB-0038H does not:

- deploy the execution bridge;
- write tombstones to a live host;
- stop or reload live systemd units;
- mutate SSH, Polkit, credentials, DNS, provider or billing state;
- execute Vikunja backup operations;
- authorize production mutation;
- authorize merge.

Merge and deployment remain separately approval-gated.
