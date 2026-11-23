# CyberCore #113 — inert root bootstrap candidate

**Status:** Draft candidate only. No production deployment authorization.

## Why this phase exists

The repository's older `deploy/cybercore-exec/install.py` prints a *proposed manifest*; it is not an executable installer. Applying the source candidate's sshd `Match User` configuration via an early `Include` is not safe without proving the full configuration parse and access rollback. The actual target has working pinned, non-root SSH, but no governed `cybercore-exec` runtime.

To preserve the authorized boundary, the new `scripts/nextcloud_r1_inert_bootstrap.py` performs **phase A only**: content-verified staging of code/config *as inactive data*, not activation.

## Fixed, bounded behavior

- Expected source is the verified, already-merged source tree `1cbe25ffd941738c4cc0b157914daa74a95885a6`. This is a source baseline for a **candidate**, not a substitution for the earlier approved production deployment payload. Any actual use still requires a new exact approval.
- Target identifier `cyberskills-vps`.
- Staged destination `/opt/cybercore-113/releases/<source-sha>/`.
- Only the 12 exact listed files are staged, with root ownership and mode 0600. Directory modes 0700.
- Staged bytes are compared with their exact Git objects; collisions, symlinks, unexpected files, mode/owner drift, or changed SHA fail closed.
- `plan` prints file paths and SHA-256 without writes.
- `apply` requires root **and** a root-owned, mode-0600 approval manifest `/etc/cybercore-exec/approvals/bootstrap-stage-113.json` with exact target/action/source binding and UTC validity not greater than one hour.
- `verify` rechecks the installed content and manifest.
- `rollback` requires a **separately action-bound** short-lived root-owned approval manifest and removes *only* this unchanged inert release. Drift or unknown files stop removal, preventing deletion of unrecognized content.
- No existing file is overwritten; staged release is committed by single directory rename.

## NOT performed by this phase

**No** `useradd`, `authorized_keys`, `sshd` modification/reload, Polkit activation, systemd install/start/enable/reload, socket ACL, source SFTP key/host pinning, approval for transfer, source archive checksum proof, archive transfer, restore, or backup deletion.

Staged config files must never be copied into active paths without an independently reviewed phase-B activation plan.

## Review and verification requirements

1. Run the stdlib isolated test suite: `python3 -m unittest discover -s tests -p test_nextcloud_r1_inert_bootstrap.py -v`.
2. Confirm `plan` works against an **unchanged** checkout of the pinned source commit, not the new PR head.
3. Run full GitHub CI and independent security review on the exact PR head.
4. Before any root action, independently verify host identity, current runtime state, approval provenance, root-owned release parent paths, and rollback/recovery path. Root ownership alone does not create authorization.
5. For future activation, design the SSH restriction so a `Match` block cannot accidentally capture global directives through the early include. Validate the complete final SSH config and prove existing operator access survives. Do not use a generic sudo/shell endpoint.
6. Future transfer remains blocked until independently trusted source SSH key, restricted dedicated source SFTP identity, and externally observed SHA-256 of the exact source archive are available.

## Approval manifest example (illustrative only — never deploy)

```json
{
  "schema_version": 1,
  "issue": 113,
  "target": "cyberskills-vps",
  "source_commit": "1cbe25ffd941738c4cc0b157914daa74a95885a6",
  "action": "stage-inert",
  "approval_id": "REPLACE_WITH_VERIFIABLE_OPERATOR_APPROVAL_REFERENCE",
  "issued_at": "2026-11-23T12:00:00Z",
  "expires_at": "2026-11-23T12:30:00Z"
}
```

For inert rollback, use `"action": "rollback-inert"` with its own fresh approval. An approval file is only a local enforcement artifact; it must be created from a real operator authorization, not minted by the program itself.

## Commands after explicit approval

```sh
python3 scripts/nextcloud_r1_inert_bootstrap.py plan --source-root /path/to/exact-1cbe25-checkout
# Do not invoke apply/rollback from an unreviewed draft.
```

A production deployment of the governed dispatcher remains a separate phase with its own exact commit approval, credential provisioning, negative access tests, independent verification and rollback.
