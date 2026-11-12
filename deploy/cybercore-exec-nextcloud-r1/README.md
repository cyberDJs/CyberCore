# CyberCore exec — Nextcloud R1 target candidate

This directory is documentation for a **separate deployment gate** on the
CyberSkills VPS target `162.35.186.106`. It intentionally does not modify the
existing Vikunja bootstrap manifest for `tasks.cyberdjs.org`.

A future approved deployment must install the normal `cybercore-exec` server
components plus these fixed helpers:

- `deploy/cybercore-exec/nextcloud-r1-offhost-transfer` ->
  `/usr/local/libexec/cybercore-exec/nextcloud-r1-offhost-transfer`, root-owned,
  mode `0755`;
- `deploy/cybercore-exec/nextcloud-r1-offhost-rollback` ->
  `/usr/local/libexec/cybercore-exec/nextcloud-r1-offhost-rollback`, root-owned,
  mode `0755`.

The execution identity must own a pre-created mode-`0700` target directory:

```text
/var/backups/cybercore/nextcloud-r1-113/2026-10-13
```

Temporary credential material is runtime state and MUST NOT come from Git:

```text
/etc/cybercore-exec/nextcloud-r1-113/id_ed25519   mode 0600
/etc/cybercore-exec/nextcloud-r1-113/known_hosts mode 0600
```

The private key is removed after a verified transfer. If source revocation fails,
the transfer fails and preserves the target private key only long enough for the
explicit governed rollback operation to retry revocation.

No deployment is performed by this repository candidate.
