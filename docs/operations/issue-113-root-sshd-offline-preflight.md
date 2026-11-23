# CyberCore #113 — root-only offline SSH activation preflight

Status: isolated source candidate. **Not a deployment or activation authorization.**

## Reason

On VPS `162.35.186.106`, Ubuntu `/etc/ssh/sshd_config` includes `/etc/ssh/sshd_config.d/*.conf` at line 12. Included `50-cloud-init.conf` is `root:root 0600`, so the nonroot `cybercore-deploy` account cannot execute trustworthy `sshd -t` or `sshd -T`. The previously merged #172 templates split the CyberCore `Subsystem` declaration from the restricted `Match User` tail.

This candidate provides a **read-only production-state inspection plus root-owned temporary offline candidate simulation**. No active file is modified; no reload, root key, credential, firewall, Polkit or systemd mutation occurs.

## Preconditions

- Operator has independently established an active console recovery path.
- Exact candidate code is independently reviewed/pinned to an approved SHA, not simply copied from an untrusted working tree.
- Source branch's `sshd-subsystem-only.conf` and `sshd-match-tail.conf` match reviewed merge commit.
- Root runs the preflight from the system's SSH session, binding `--operator-addr` to the verified remote client address.
- Existing SSH main file must contain exactly one known include, no existing `Match` section, and no extra unexpected includes. All included `*.conf` files must be regular, root-owned, non-group/world-writable and free of nested `Include`, `Match` or existing CyberCore subsystem directives.

## Offline verification (requires root, does not activate)

```sh
python3 scripts/nextcloud_r1_root_sshd_dryrun.py \
  --operator-addr <VERIFIED_OPERATOR_IP> \
  --subsystem deploy/cybercore-exec-nextcloud-r1/sshd-subsystem-only.conf \
  --match-tail deploy/cybercore-exec-nextcloud-r1/sshd-match-tail.conf
```

The check copies existing included configuration into a root-only temporary directory under `/run`, introduces the proposed separate CyberCore subsystem, appends exactly the reviewed restricted service-user `Match` clause and executes `sshd -t -f` and `sshd -T -f -C` *against the temporary config*. Effective operator configuration is compared for `root` and `cybercore-deploy`, with `subsystem` as the only allowed difference. The service user must resolve all prescribed restrictions and the exact target-bound `ForceCommand`. Temporary configuration is cleaned automatically.

Expected JSON status is `OFFLINE_SSHD_CANDIDATE_VERIFIED`, `ssh_config_modified=false`, `sshd_reloaded=false`, `activation_performed=false`. Any other result blocks promotion.

## Limits and independent safety gates

This is a design-level parser proof, **not** the activation plan. It cannot prove future credential trust, source SFTP restrictions, SSH listen availability after reload, restored console access, systemd behavior or Polkit privilege boundaries. SSH `-T` results are sampled for two operator identities and one source client address, not for every possible `Match Address` condition. Changes between the preflight and actual deployment invalidate the evidence.

Actual Phase B must additionally deliver:

1. Exact root-owned deployment manifest with content SHA and preserved original SSH config/rollback resources.
2. Independent live full-config `sshd -t` and effective `sshd -T -C` on real root and service identities immediately before/after any config mutation.
3. Dedicated locked nonroot account, correct importable dispatcher and static systemd/Polkit placement with per-operation fail-closed tests.
4. Two independent active operator access paths, successful status-only subsystem smoke test, failed unauthorized mutation and tested rollback before closing activation.
5. Separately authorized source host fingerprint, constrained SFTP key, archive digest, transfer and backup recovery verification.

**No merge or production activation under this candidate without exact-head review and user authority.**
