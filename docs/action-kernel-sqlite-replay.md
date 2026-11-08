# Action Kernel: single-host replay claims (WB-AK-005)

Tracking: #127. Status: candidate, feature disabled by default.

## Scope
`SQLiteReplayGuard` implements `claim_once(key)` with a SQLite primary-key
constraint and transaction commit. Reopening the database preserves claims;
multiple cooperating processes pointing at **the same local database file**
cannot both claim one key. No automatic expiration or cleanup is provided,
because deleting the only replay record would reauthorize an old receipt.

## Security and operational boundaries
- Local single-host file only, on a trustworthy filesystem with an operator-owned,
  restricted parent directory and regular database file. Do not use NFS,
  object storage, replicated files, or multiple independent database copies.
- Caller supplies the absolute database path. This class does not own database
  provisioning, symlink validation, directory permissions or backup/restore.
- Database unavailable/locked/corrupted raises an exception; the CyberHIVE bridge
  catches guard errors and refuses dispatch.
- A claim is committed **before** calling the in-process dispatcher. A crash
  after commit means the task cannot be retried using the same authorization.
- This is *at-most-once admission*, **not** proof of exactly-once completion.
  It cannot authenticate a model-created receipt; a trusted transport,
  receipt provenance and a durable audit source are still required.
- There is no live execution, shell, remote transport or production rollout.
- Rollback: disable bridge use and retain the database and its claims. Never
  erase the claim database just to retry a rejected request.

## CI
`tests/test_action_kernel_sqlite_replay.py` covers process-reopen persistence,
concurrent claims via independent connections, and invalid/unavailable storage.
Further acceptance for issue #127 requires separate-process verification,
real CyberHIVE classes and independently authenticated authorization.
