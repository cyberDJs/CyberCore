# CyberCloud DR Storage Runbook v0

Status: pilot-validated, not production-ready
Scope: CyberDJS Cloud and Eimy Cloud
Last evidence run: 2026-09-07 / session 20260907T134644Z

## Purpose

This runbook defines the safe CyberCloud disaster-recovery storage pattern for
CyberDJS Cloud and Eimy Cloud.

It exists to prevent unsafe direct mirroring of Nextcloud internal data
directories and to provide a tested path for asynchronous copy, drift detection,
and recovery verification.

## Current production components

- CyberDJS Cloud: https://cloud.cyberdjs.org
- Eimy Cloud: https://cloud.eimyherrer.com
- CyberDJS Nextcloud: 31.0.14
- Eimy Nextcloud: 33.0.5
- Federation trusted relationship: active
- Tailscale admin endpoint for CyberDJS Pi: cyberdjs-cloud / 100.69.185.74

## Core rule

Never directly sync, rsync, mirror, or repair by copying either server's
Nextcloud internal `data/` directory.

Allowed data movement must use supported Nextcloud application-layer access,
such as federation, WebDAV, OCS, or Nextcloud filesystem APIs.

## Authority model

Every namespace must have exactly one authoritative live side.

- CyberDJS-authoritative data is edited on CyberDJS.
- Eimy-authoritative data is edited on Eimy.
- The opposite side may hold an asynchronous DR copy.
- The DR copy is not a live collaboration surface unless promoted by an approved recovery step.

Mirror does not equal backup. Versioned backups remain separately required.

## Validated pilot pattern

The validated pilot pattern is:

1. Create an authoritative source folder on CyberDJS.
2. Share it to Eimy through Nextcloud federation.
3. Copy the federated source into an Eimy-local DR snapshot using `rclone copy`.
4. Verify all snapshot files by SHA256.
5. Modify the authoritative source and create a second snapshot.
6. Run a drift guard before any destination update.
7. Share the selected DR snapshot back to CyberDJS through federation.
8. Restore into a new CyberDJS local recovery folder.
9. Verify recovered files by SHA256.
10. Remove only disposable pilot objects.

The validated command class was copy-only. `rclone sync` was not used.

## Required preflight

Before any DR storage run, verify:

- Both `/status.php` endpoints return installed true.
- Both servers have `maintenance=false`.
- Both servers have `needsDbUpgrade=false`.
- Trusted federation is status 1 in both directions.
- The chosen source namespace is disposable or explicitly approved.
- The destination namespace does not contain unexpected data.
- The operator has a rollback plan for only the named test paths.

For production namespaces, additionally verify current backups and restore plan.

## Stop conditions

Stop immediately on any unexpected:

- HTTP 5xx from either cloud,
- Nextcloud maintenance or DB upgrade flag,
- failed SHA256 comparison,
- source or destination drift,
- permission mismatch,
- unexpected external share or mount,
- direct request to copy a Nextcloud `data/` directory,
- credential leakage risk,
- unknown production data in a pilot path.

If a stop condition fires, do not retry blindly. Capture evidence first.

## Drift guard

The DR destination must be checked before every update.

The guard must abort if a destination file differs from the expected snapshot
state or if unexpected destination files are present.

The 2026-09-07 pilot intentionally changed `alpha.txt` on the destination and
confirmed the correct result:

`DRIFT_GUARD=ABORT`

## Recovery rule

Recovery must restore into a new local recovery folder first.

Do not overwrite the original authoritative source during a first recovery
attempt. After recovery verification, promotion requires a separate approval.

Minimum recovery verification:

- list recovered files,
- compare recovered SHA256 values to the selected snapshot manifest,
- verify source cloud health after the copy,
- verify no leftover test mounts or folders remain after cleanup.

## Cleanup rule

Cleanup may remove only explicitly named pilot objects.

For the 2026-09-07 run, cleanup removed pilot shares, pilot folders, the empty
DR pilot root, and federated test mounts. The trusted federation relationship
was intentionally retained.

## Forbidden operations

The following are explicitly out of scope for this runbook:

- direct sync of `/opt/ncdata/data`, `/home/eimyherr/nextclouddata`, or any
  equivalent Nextcloud internal data directory,
- `rclone sync` into a production namespace without a dedicated retention and
  rollback design,
- active-active bidirectional sync,
- promotion of a DR copy into production without a separate recovery approval,
- using the Mac as permanent DR storage,
- changing DNS, mail, PHP, Nextcloud version, or branding during a DR pilot.

## Production rollout gates

Production storage readiness remains NOT READY until all gates below pass.
1. Select a persistent storage target.
2. Define retention, versioning, and delete policy.
3. Define service accounts and credential storage.
4. Define monitoring and alerting.
5. Define backup vs DR responsibilities.
6. Run a larger non-production namespace pilot.
7. Run a documented restore drill.
8. Approve production cutover separately.

## Current verdict

- Federation readiness: READY
- Federation acceptance: PASS
- DR storage pilot: PASS
- Production storage readiness: NOT READY

See `docs/evidence/2026-09-07-cybercloud-dr-storage-pilot.md` for the
validated pilot evidence.
