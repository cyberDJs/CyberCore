# CyberCloud DR Storage Pilot Evidence - 2026-09-07

Status: PASS
Session: 20260907T134644Z
Scope: CyberDJS Cloud -> Eimy Cloud -> CyberDJS Cloud recovery

## Purpose

Validate the CyberCloud asynchronous DR storage pattern before any production
storage rollout or Google Drive replacement work.

The pilot was explicitly disposable and did not move production user data.

## Participants

- CyberDJS Cloud: https://cloud.cyberdjs.org
- Eimy Cloud: https://cloud.eimyherrer.com
- CyberDJS Nextcloud: 31.0.14
- Eimy Nextcloud: 33.0.5
- Orchestrator: Mac with rclone WebDAV remote to Eimy Cloud

## Safety boundaries

The pilot did not use direct filesystem mirroring of Nextcloud internal data.

Explicitly avoided:

- direct rsync/sync of `/opt/ncdata/data`,
- direct rsync/sync of `/home/eimyherr/nextclouddata`,
- `rclone sync`,
- production user namespace changes,
- DNS, mail, PHP, branding, or Nextcloud version changes.

The trusted federation relationship remained active after the run.

## Pilot objects

- Source folder: `CyberCloud-Storage-Pilot-Source-20260907T134644Z`
- DR root: `CyberCloud-DR-Pilot/20260907T134644Z`
- Recovery folder: `CyberCloud-Recovery-Pilot-20260907T134644Z`

## Source creation evidence

CyberDJS created a disposable authoritative source and federated it to Eimy.

- CyberDJS outgoing share ID: `3`
- Source v1 files:
  - `alpha.txt`
  - `beta.txt`
  - `manifest-v1.sha256`

Initial SHA256 values:

- `alpha.txt`: `ce201ade3b7eadad9e84c3150b426a48799ea13fb9846b870ae6220a9a96e2b3`
- `beta.txt`: `8c69fd67b1de025fda59827c102835c3e1f06128848da6f7b5cdd9a13525545c`
- `manifest-v1.sha256`: `a31d6e404b500740491a9ecf9d4119e416a2f45b8eed51bb8012e3aa8ea3d7ad`

## Snapshot 1 evidence

The federated source was copied to an Eimy-local DR snapshot using `rclone copy`.

Snapshot path:

`CyberCloud-DR-Pilot/20260907T134644Z/snap-1`

Verification result:

- `ASSERT_OK SNAP1:alpha.txt ce201ade3b7eadad9e84c3150b426a48799ea13fb9846b870ae6220a9a96e2b3`
- `ASSERT_OK SNAP1:beta.txt 8c69fd67b1de025fda59827c102835c3e1f06128848da6f7b5cdd9a13525545c`
- `ASSERT_OK SNAP1:manifest-v1.sha256 a31d6e404b500740491a9ecf9d4119e416a2f45b8eed51bb8012e3aa8ea3d7ad`

## Source update evidence

The authoritative CyberDJS source was changed and a second snapshot was created.

Source v2 SHA256 values:

- `alpha.txt`: `88c73792197570679e9df96730ebbaa8ee8e4b6978bf1047bfefd5cc32e93b01`
- `beta.txt`: `8c69fd67b1de025fda59827c102835c3e1f06128848da6f7b5cdd9a13525545c`
- `gamma.txt`: `f4122bc442507f135adcbacea9372d1102d9532ca02838d63ce80e4c10e322b7`
- `manifest-v2.sha256`: `0c848d97d60e3df2547ad5a8a190d79ff7fa277e996d6a8b77fe0bf968eeac36`

Snapshot path:

`CyberCloud-DR-Pilot/20260907T134644Z/snap-2`

## Snapshot 2 evidence

Verification result:

- `ASSERT_OK SNAP2:alpha.txt 88c73792197570679e9df96730ebbaa8ee8e4b6978bf1047bfefd5cc32e93b01`
- `ASSERT_OK SNAP2:beta.txt 8c69fd67b1de025fda59827c102835c3e1f06128848da6f7b5cdd9a13525545c`
- `ASSERT_OK SNAP2:gamma.txt f4122bc442507f135adcbacea9372d1102d9532ca02838d63ce80e4c10e322b7`
- `ASSERT_OK SNAP2:manifest-v2.sha256 0c848d97d60e3df2547ad5a8a190d79ff7fa277e996d6a8b77fe0bf968eeac36`

`manifest-v1.sha256` remained present in snapshot 2 because the run copied a
complete snapshot of the source folder, not a filtered export.

## Drift guard evidence

The destination was intentionally modified to validate that the pilot aborts
instead of blindly overwriting a drifted replica.

Observed result:

- `DRIFT_GUARD=ABORT`
- `DRIFT_CHANGED=alpha.txt`

This is the required safe behavior. Production copy jobs must retain this
behavior and must not overwrite drifted destinations without explicit recovery
approval.

## Recovery evidence

Eimy shared `snap-2` back to CyberDJS through federation.

- Eimy outgoing share ID: `30`
- CyberDJS recovery folder: `CyberCloud-Recovery-Pilot-20260907T134644Z`

Recovered SHA256 values:

- `alpha.txt`: `88c73792197570679e9df96730ebbaa8ee8e4b6978bf1047bfefd5cc32e93b01`
- `beta.txt`: `8c69fd67b1de025fda59827c102835c3e1f06128848da6f7b5cdd9a13525545c`
- `gamma.txt`: `f4122bc442507f135adcbacea9372d1102d9532ca02838d63ce80e4c10e322b7`
- `manifest-v1.sha256`: `a31d6e404b500740491a9ecf9d4119e416a2f45b8eed51bb8012e3aa8ea3d7ad`
- `manifest-v2.sha256`: `0c848d97d60e3df2547ad5a8a190d79ff7fa277e996d6a8b77fe0bf968eeac36`

## Cleanup evidence

Removed pilot objects:

- CyberDJS share ID `3`
- Eimy share ID `30`
- `CyberCloud-Storage-Pilot-Source-20260907T134644Z`
- `CyberCloud-Recovery-Pilot-20260907T134644Z`
- `CyberCloud-DR-Pilot/20260907T134644Z`
- empty root `CyberCloud-DR-Pilot`
- `snap-2` federated mount

Final leftover counts:

- CyberDJS node test count: `0`
- CyberDJS external test count: `0`
- Eimy node test count: `0`
- Eimy external test count: `0`

## Final health evidence

Final public state:

- CyberDJS: Nextcloud 31.0.14, maintenance false, needsDbUpgrade false
- Eimy: Nextcloud 33.0.5, maintenance false, needsDbUpgrade false

Trusted federation state remained active:

- CyberDJS -> Eimy: status 1, shared secret present
- Eimy -> CyberDJS: status 1, shared secret present

Relevant federation/files_sharing level >= 3 errors after cleanup:

- CyberDJS: none
- Eimy: none

## Verdict

DR storage pilot: PASS
Production storage readiness: NOT READY
