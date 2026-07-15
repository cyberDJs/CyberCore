# Decisions — WB-0006

## D-001 — Package representation

A CXP v1 package is a directory, never a tar archive.

## D-002 — State machine

`incoming -> staged -> ready -> processed | failed`

State transitions are explicit and auditable.

## D-003 — Verification boundary

`verify` must be read-only and may not modify the target repository.

## D-004 — Human gate

`apply` requires explicit user confirmation. No automatic mutation