# CXP-0002 — Runtime Specification v1

## Status

Proposed for WB-0006 design freeze.

## Responsibility

The runtime receives packages from a transport, validates them, stages them, exposes READY state and applies them only after explicit operator approval.

## Local state

```text
~/.local/share/cybercore/exchange/
├── inbox/
├── staged/
├── ready/
├── processed/
├── failed/
└── state/
```

The filesystem is the v1 queue and audit surface. State transitions use atomic rename on the same filesystem.

## State machine

```text
remote/incoming
      |
      v
    inbox
      |
      | validate package, schema, checksum, repository target
      v
    staged
      |
      | run non-destructive verify
      v
     ready
      |
      | explicit human approval
      v
  applying
    /   \
   v     v
processed failed
```

`applying` may be represented by an internal lock and journal rather than a public directory.

## Transition rules

1. A package enters `inbox` only after transport copy completes.
2. Validation failure moves one immutable copy to `failed` with a reason record.
3. `verify.sh` runs only in `staged` and must not mutate the target repository.
4. Successful verification moves the package to `ready`.
5. Apply requires the package ID and explicit confirmation.
6. Successful apply moves the package to `processed` and records result metadata.
7. Failed apply moves it to `failed`; partial repository changes must be reported and never hidden.

## Idempotency and duplicate delivery

The runtime keys packages by Work Block ID plus version and content digest. An already processed identical package is acknowledged without re-application. A reused ID with different content is rejected as a collision.

## Locking

- One global sync lock prevents concurrent transport ingestion.
- One package lock prevents concurrent verify/apply for the same package.
- Stale locks must be detectable and require explicit recovery; they are never silently ignored.

## Repository safety

Before verify or apply, the runtime must validate:

- target path is a Git repository,
- expected `origin` repository is present,
- repository root is not `$HOME`, `/`, or the exchange data directory,
- expected marker files are present,
- current branch satisfies the package contract,
- working tree cleanliness policy is satisfied.

## Failure record

Every failure creates machine-readable metadata containing:

- package ID and digest,
- failed transition,
- timestamp,
- exit code,
- concise reason,
- log path,
- whether the target repository may have been mutated.

## Runtime outputs

Commands must produce human-readable output and support structured JSON later. Tracebacks and raw command noise are not the primary interface.

## Recovery

The runtime must provide inspection and explicit retry. Automatic retries are permitted only for transport-level transient failures, never for apply failures.