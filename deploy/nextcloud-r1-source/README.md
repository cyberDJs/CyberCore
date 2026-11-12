# Nextcloud R1 source exporter — deployment candidate

This directory contains a **repository-only candidate** for issue #113. Nothing in
this directory deploys itself.

## Required authorized_keys shape

A deployment must create a fresh temporary Ed25519 key and install only its public
key with a forced command:

```text
restrict,command="/home/eimyherr/.local/libexec/cybercore-nextcloud-r1-source-export" ssh-ed25519 <TEMP_PUBLIC_KEY> cc-r1-113-temp
```

The private key must never be stored in Git, chat, logs or evidence. On the target
it is expected at `/etc/cybercore-exec/nextcloud-r1-113/id_ed25519` with mode
`0600` and ownership matching the execution identity.

## Allowed requests

The forced command reads `SSH_ORIGINAL_COMMAND` and accepts exactly:

- `metadata` — returns archive name, size and SHA-256;
- `stream` — emits only the fixed archive bytes, then self-revokes the temporary key;
- `revoke` — removes exactly one matching temporary key entry.

Anything else exits non-zero.

## Deployment boundary

Installing the exporter or public key changes production SSH trust and therefore
requires a separate deployment approval. The Draft PR that contains this file does
not grant that authority.
