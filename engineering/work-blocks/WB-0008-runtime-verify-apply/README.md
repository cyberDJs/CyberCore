# WB-0008 — Runtime Verify + Apply

## Goal

Add the first controlled mutation boundary to CyberCore Runtime Alpha.

## Delivered

- `cybercore verify PATH`
- `cybercore apply PATH`
- explicit approval phrase or `--yes`
- non-mutating `--dry-run`
- CXP v1 manifest validation
- SHA-256 integrity verification
- path traversal and symlink rejection
- clean Git working-tree gate
- target branch gate
- `before_apply`, `after_apply`, and `rollback` hook support
- runtime lifecycle events
- verification and application tests

## Security boundary

A valid checksum proves integrity, not trust. Publisher signatures and encrypted
transport envelopes remain required future increments.

## Verification

```bash
pytest
cybercore verify /path/to/WB-XXXX
cybercore --repo "$PWD" apply --dry-run /path/to/WB-XXXX
```

## Rollback

Revert the WB-0008 commit. Applied Work Blocks remain responsible for their own
documented rollback procedure.
