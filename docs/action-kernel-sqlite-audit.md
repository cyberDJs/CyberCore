# WB-AK-009: local SQLite audit sink (candidate)

Tracking: #127. Scope: opt-in single-host synthetic Action Kernel only.

`SQLiteAuditSink` implements the existing injected `evidence_sink` callable.
Each event is bounded to 8192 UTF-8 bytes, written in a SQLite transaction
using a hash of its canonical JSON payload and the previous event hash.
`verify_chain()` detects in-place payload edits and deletion of interior
rows, including after reopening the database.

## Boundaries

- The chain is **tamper-evident only against partial modifications**. It is not
  signed, anchored externally or cryptographically authentic against a database
  administrator rewriting all hashes; truncation of the tail (including all
  records) cannot be detected without an externally retained checkpoint.
- Database files and parent directories require operator-managed restrictive
  permissions and local filesystem semantics. Do not use a distributed mount.
- Do not treat the sink as ADR-0013's canonical CyberDJs Room ledger writer.
  A future adapter must preserve its single-writer ownership and provenance.
- Inject the sink via `ActionKernel(evidence_sink=SQLiteAuditSink(path))`.
  There is no automatic deployment, existing configuration change, or schema
  migration of other databases.
- SQLite write failures raise exceptions; the current Action Kernel denies
  on failed audit callback. Execution cannot be considered independently
  verified solely because the method returned.
- Before production: external hash anchoring, trusted authenticated identity,
  deletion/truncation detection, retention and backup/recovery procedures,
  permission hardening and independent security review are required.

## Rollback

Stop using the sink; **retain** the database and checkpoints. Do not delete
audit records to reset state. No live node operations are enabled in this PR.
