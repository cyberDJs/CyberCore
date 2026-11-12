# CyberCore exec — Nextcloud R1 target candidate

This directory describes a **separate deployment gate** for the CyberSkills VPS
target `162.35.186.106`. It does not modify the canonical
`tasks.cyberdjs.org` Vikunja deployment.

## Physical target binding

The CyberSkills SSH subsystem must use the target-specific dispatcher:

```text
/usr/local/libexec/cybercore-exec/nextcloud_dispatcher.py
```

The supplied `cybercore-exec.subsystem.conf` forces that dispatcher for the
`cybercore-exec` identity and disables TTY, TCP forwarding, X11 forwarding and
agent forwarding.

The target-specific dispatcher parses requests with the compiled target id:

```text
cyberskills-vps-nextcloud-r1
```

It cannot use the Tasks/Vikunja operation resolver. Conversely, the existing
Tasks dispatcher keeps its original exact operation surface.

## Candidate files

A future approved deployment must install the common protocol/authorization
components plus:

- `src/cybercore/execution/server/nextcloud_dispatcher.py` ->
  `/usr/local/libexec/cybercore-exec/nextcloud_dispatcher.py`;
- `src/cybercore/execution/server/nextcloud_operations.py` ->
  `/usr/local/libexec/cybercore-exec/nextcloud_operations.py`;
- `deploy/cybercore-exec/nextcloud-r1-offhost-transfer` ->
  `/usr/local/libexec/cybercore-exec/nextcloud-r1-offhost-transfer`;
- `deploy/cybercore-exec/nextcloud-r1-offhost-rollback` ->
  `/usr/local/libexec/cybercore-exec/nextcloud-r1-offhost-rollback`.

Helpers must be root-owned and not writable by the execution identity.

The execution identity must own a pre-created mode-`0700` target directory:

```text
/var/backups/cybercore/nextcloud-r1-113/2026-10-13
```

Temporary credential material is runtime state and MUST NOT come from Git:

```text
/etc/cybercore-exec/nextcloud-r1-113/id_ed25519   mode 0600
/etc/cybercore-exec/nextcloud-r1-113/known_hosts mode 0600
```

## Authorization gate

Repository code intentionally retains the deny-all authorization default.
Deployment is forbidden until a separately reviewed trusted
`ExecutionAuthorizationVerifier` is wired on **both** the MCP/client side and
the CyberSkills server side. A non-empty authorization reference is binding
metadata, not proof of authority.

## Transaction cleanup

The source key self-revokes after a complete stream. The target private key is
removed only after successful source revocation. If source revocation cannot be
confirmed, rollback preserves the target private key so a later governed retry
can revoke the source trust entry.

No deployment is performed by this repository candidate.
