# WB-0038G — Consolidated Rollback Repair Evidence

Status: IMPLEMENTED_IN_BRANCH / POST-READY P1 REPAIRED / FINAL_EXACT_HEAD_REVERIFY_PENDING

## Provenance

- Repository: cyberDJs/CyberCore
- Branch: wb-0038g-consolidated-rollback-repair
- Pull request: #102
- Exact canonical base: 1a22865747d0d8ea2bf97d3b455534b610a66a90
- Source evidence: PR #97 and PR #98 review findings
- Authority: repository-only repair
- Merge authority: false
- Remote deployment authority: false
- VPS mutation authority: false
- Production execution authority: false

## Confirmed defect chain

The PR #95 / WB-0038E rollback contract correctly revoked future Polkit authority before removing wrapper unit files, but post-merge review exposed concurrency and lifecycle gaps:

1. an already-running governed wrapper could outlive rollback;
2. a run wrapper that delegated to another systemd service did not necessarily own the actual backup process;
3. an enabled backup timer could independently activate privileged backup work;
4. an in-flight installer could recreate or re-enable that timer after an earlier quiescence check;
5. a pre-revocation asynchronous StartUnit could complete after policy revocation;
6. runtime-only masks did not protect wrapper names across reboot if a lower-priority or generated unit existed;
7. direct wrapper execution initially dropped Docker startup ordering;
8. a generated service with `PartOf=` could receive propagated stop control before its identity gate;
9. direct manual and timer-triggered execution could run the same backup script concurrently;
10. the strict manual-run sandbox did not provide a writable path for the shared `/run` lock.

PR #97 and PR #98 each solved only part of this chain. WB-0038G consolidates the required invariants on current canonical main.

## Consolidated invariant

Rollback is declarative and fail-closed:

1. remove the exact managed Polkit rule;
2. verify effective privilege revocation;
3. verify both governed wrapper identities against canonical repository units;
4. runtime-mask both wrapper names and verify those masks;
5. stop-and-wait the installer wrapper first;
6. only after the installer is quiescent, verify the generated timer and service are absent or exact canonical units;
7. disable-and-wait the timer if present, closing the scheduled activation path;
8. stop-and-wait the governed manual run wrapper;
9. stop-and-wait the generated backup service if present;
10. remove the exact managed wrapper unit files;
11. reload systemd while runtime masks still protect the names;
12. establish persistent masks for both wrapper names;
13. reload systemd and verify both persistent masks before cleanup continues.

Any failed identity, mask, stop, disable, or verification action is a hard stop for the future governed executor.

## Governed backup lifetime

The manual governed backup wrapper now directly executes:

`/usr/local/sbin/vikunja-backup`

The backup process therefore lives inside the verified wrapper cgroup rather than behind a waiting `systemctl start` client.

The canonical generated service deliberately has no `PartOf=cybercore-vikunja-backup-run.service` relationship. Generated-unit identity is verified before any run-wrapper stop, so rollback never relies on unverified stop propagation.

Manual and timer-triggered executions share a root-only advisory lock at `/run/cybercore-vikunja-backup/backup.lock`. Both unit entry paths declare `RuntimeDirectory=cybercore-vikunja-backup`, mode `0700`, with preservation across unit stop, so the strict manual-run sandbox receives only the dedicated writable runtime directory rather than a broad `/run` exception. The backup script opens the lock with `O_NOFOLLOW`, mode `0600`, and an exclusive `flock`, serializing both entry paths while keeping the manual process inside the governed wrapper cgroup.

The wrapper preserves:

- `Requires=docker.service`
- `After=docker.service`
- `ProtectSystem=strict`
- `ReadWritePaths=/opt/backups/vikunja`

This keeps Docker startup ordering while bounding the writable filesystem surface.

## Canonical generated units

The generated backup service and timer now have repository sources of truth:

- `deploy/cybercore-exec/vikunja-backup.service`
- `deploy/cybercore-exec/vikunja-backup.timer`

Bootstrap deploys root-owned mode-0600 templates under `/usr/local/libexec/cybercore-exec/`. The root-owned installer consumes those templates when materializing the live generated units.

This lets rollback verify generated-unit identity before controlling them.

## Regression coverage

`tests/test_bootstrap_manifest.py` covers:

- wrapper process ownership and Docker ordering;
- canonical root-owned generated-unit templates;
- runtime mask-before-stop ordering;
- installer stop before generated timer/service revalidation;
- absence of generated-service `PartOf=` stop propagation;
- root-only shared backup locking with `O_NOFOLLOW` and a dedicated systemd-managed runtime directory;
- timer disable before manual run-wrapper stop and downstream service stop;
- generated service quiescence before wrapper-file removal;
- persistent mask installation and verification before the reboot boundary.

## Hosted verification

Implementation head `aca79cc0dacd8356b3b13877a7ce2ded65882f4a`:

- CI #926: PASS
- quality: PASS
- package: PASS
- Python 3.11: PASS
- Python 3.12: PASS
- Python 3.13: PASS
- Python 3.14: PASS
- CodeQL #927: PASS

Subsequent fresh review found and repaired two additional findings on the consolidated branch: pre-verification stop propagation through `PartOf=` and concurrent manual/timer backup execution. A later Ready-triggered review then found a P1 sandbox defect: the manual wrapper could not create the shared lock under `/run` while `ProtectSystem=strict` was active. That defect is repaired by a dedicated systemd-managed runtime directory shared by both backup entry paths. Final readiness therefore requires new CI, CodeQL, and fresh correctness/security review on the new exact head.

## Scope boundary

WB-0038G does not:

- deploy the execution subsystem;
- stop or mask any live systemd unit;
- mutate SSH, Polkit, credentials, or a VPS;
- run a Vikunja backup;
- grant production execution authority;
- grant merge authority.

Merge and deployment remain separately approval-gated.
