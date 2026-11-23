# CyberCore #113 Phase B — service-user permission boundary (candidate)

**Status: isolated proposal; no production activation or authorization.**

The existing dispatcher executes as locked nonroot `cybercore-exec`. It must read short-lived root-owned exact-action approval manifests while being unable to edit them. The current inert Stage-A release is root:root 0700 with files 0600, so it cannot be used directly as a nonroot executable tree. These are separate trust and availability problems.

## Proposed minimum permissions

| Path | Owner | Mode | Purpose |
|---|---|---|---|
| `/etc/cybercore-exec` | root:root | 0755 | Non-writable traversal only |
| `/etc/cybercore-exec/approvals` | root:cybercore-exec | 0750 | Group-traversable, not group-writable |
| `/etc/cybercore-exec/approvals/nextcloud-r1.json` | root:cybercore-exec | 0640 | Exact-action root-created manifest |
| `/usr/local/libexec/cybercore-exec` | root:root + named UID ACL | 0750 effective | Named-user traverse, no group access |
| `/usr/local/libexec/cybercore-exec/*.py` | root:root + named UID ACL | 0640 effective | Named-user read-only, no group access |
| `/usr/local/libexec/cybercore-exec-nextcloud-r1` | root:root + named UID ACL | 0750 effective | Named-user traverse, no group access |
| `/usr/local/libexec/cybercore-exec-nextcloud-r1/*.py` | root:root + named UID ACL | 0640 effective | Named-user read-only code |

Real UID/GID **must be discovered on target after account creation**, never use synthetic model UID 996/GID 996. Group membership must be the minimum possible; no service account in sudo, wheel, adm, docker or other privileged groups. Any existing path, group or ownership collision stops installation.

The effective mode includes ACL mask group-class bits, but `group::---` and `other::---` deny all unnamed users. The sole named `user:<real service UID>` ACL entry grants `r-x` on directories and `r--` on source modules. This is narrower than a group-readable file. Validation uses `getfacl -n -c` and rejects extra entries or unexpected masks.

## Security invariants

- Only root writes the approval manifest, with atomic file placement and exact expiry and authorization reference binding. No service/group/other write access.
- Approval parent and file must have root ownership and non-group-writable permissions, matching the current `FileBoundExecutionAuthorizationVerifier` assumptions.
- `cybercore-exec` can traverse approvals and read only the manifest; unrelated user cannot traverse the approval directory or read the manifest.
- Dispatcher, operation allowlist, authorization verifier and Nextcloud wrappers are root-owned and not writable by service user.
- Existing root-only Phase-A release stays immutable; installation copies verified bytes to distinct active paths, never `chmod -R` the staged source.
- No generic sudoers entry, unrestricted Polkit `manage-units`, interactive shell or arbitrary targets.
- Keep source-host SFTP credentials *unprovisioned* until independently verified source fingerprint and archive digest.
- Successful model check means `PROPOSED_PERMISSION_CONTRACT_VERIFIED`, **not** live filesystem assurance.

## Verification and rollback gates

Run: `python3 scripts/nextcloud_r1_service_permission_contract.py` and `python3 -m unittest discover -s tests -p test_nextcloud_r1_service_permission_contract.py`.

Before any actual installation: root preflight must compare UID/GID assignment and effective permissions in a root-only staging namespace, run denial tests under both service and unrelated identities, validate `FileBoundExecutionAuthorizationVerifier` against missing, expired and forged manifests, capture fixed-path rollback evidence, and provide exact-HEAD review plus separate root activation approval. Actual rollback must restore prior SSH and unit state, leave backup archives untouched and independently prove operator SSH access.

This candidate only addresses the **permission-model contract**; it is not a transactional deployment script, rollback implementation or permission-granting authority.
