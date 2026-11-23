# CyberCore #113 — locked service identity root gate (candidate)

## Purpose

Allow safe decision-making before any root operator provisions `cybercore-exec` on the pinned VPS. This is **read-only**. The merged code transaction (PR #176) requires an already-existing locked, noninteractive service user; it must never silently create an identity or silently reuse a colliding UID/GID.

## Read-only operation

On the exact pinned host `vps3665015.trouble-free.net`, execute:
```sh
python3 scripts/nextcloud_r1_identity_preflight.py
```

The script checks hostname, root-owned parents, absence of active target paths, account and group identity, shell, password marker, home and privileged supplementary groups. A missing account and missing group returns `IDENTITY_ABSENT_READY_FOR_SEPARATE_ROOT_PROVISIONING`. That means **no collision found**, not an authorization to create the account.

A partial account/group collision, unexpected permissions, wrong host or active deployment paths produces `BLOCKED` (exit 2). Existing locked identity produces `IDENTITY_PRESENT_RESTRICTED`, but still does not prove its effective Linux ACL/sudo/SSH authorization.

## Future separately authorized root procedure (not executed by this PR)

1. Require exact hostname, current release SHA and an interactive root console with tested recovery access.
2. Review the proposed `groupadd --system cybercore-exec` and `useradd --system --no-create-home --home-dir /nonexistent/cybercore-exec --gid cybercore-exec --shell /usr/sbin/nologin cybercore-exec` commands; never use predetermined numeric UID/GID.
3. Root operator must explicitly approve exact action, expected absence of both identity records and intended rollback.
4. After creation, lock password, verify `getent passwd`, `getent group`, `id` and restricted group membership. Do not install SSH keys or grant broad sudo, Docker or Polkit membership.
5. On failure, preserve evidence. Only remove an identity if the operator can prove it was newly created by that exact transaction, has no processes/files/resources outside the transaction and separate rollback authorization exists.
6. Then independently verify root-owned Stage-A release, tested code-only installer and its action-bound approval. SSH, systemd, Polkit and transfer still require further gated steps.

### Important boundary

No production command above is executed by this PR. Preflight status is not approval. Archive/SFTP source integrity remains unresolved. Real root execution remains unavailable through the connected nonroot `cybercore-deploy` SSH channel.

## Test plan

`python3 -m unittest discover -s tests -p test_nextcloud_r1_identity_preflight.py -v`

Check exact-head CI plus independent `eimyroot` review; keep Draft until verified. Never merge or change the live account/host without explicit authorization.
