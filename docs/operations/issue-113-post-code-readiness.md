# CyberCore #113 — post-code-only readiness gate

Status: isolated read-only candidate. It applies after code-only installation (CODE_ONLY_INSTALLED / CODE_ONLY_VERIFIED). The pre-install collision check is obsolete after that installation, because code paths are now supposed to exist.

## Evidence and scope

On 2026-11-23 the root operator's apply and verify reported success for eight modules. Independently, nonroot target SSH observed directories root:root 0750 with service UID 995 r-x ACL, root:root 0600 receipt, no journal or approval, and neither transfer nor rollback unit installed. Nonroot cannot independently hash private code; root installer's verify was used for SHA validation.

The new scripts/nextcloud_r1_post_code_readiness.py requires root and performs read-only checks of exact hostname, noninteractive service identity and primary group, eight fixed code names/no extras, root owner and ACL metadata, root-only receipt metadata, missing journal or install approval, and collisions at future SSH/systemd/Polkit/operation-approval destinations. Missing credential/state directories are reported only for next phase; no directories are created.

It does not validate receipt contents or independently hash code. Root code-only installer's verify remains authoritative for that step. It neither installs nor starts services, modifies sshd, creates authorizations or transfers backups.

## Gate and execution

Test with: python3 -m unittest discover -s tests -p test_nextcloud_r1_post_code_readiness.py -v

Require exact-head CI and independent reviewer. Root must not execute any user-writable checkout as root. When authorized for read-only root inspection, pin reviewed Git commit and exact SHA-256 of this script, materialize to a private root-owned path at mode 0500, rehash independently and run only that root-owned copy. Abort on any mismatch.

Passing the post-code readiness gate is not permission to activate anything. SSH early Include and primary Match tail, two systemd units, restricted Polkit, state and credential directories and source SFTP host-key / archive hash still require independent approvals and rollback validation. Preserve existing operator SSH access and out-of-band recovery.
