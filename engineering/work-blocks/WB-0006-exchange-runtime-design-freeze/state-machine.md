# State Machine — WB-0006

## States

```text
remote/incoming
      |
      v
    inbox
      |
      | package + schema + checksum + target validation
      v
    staged
      |
      | non-destructive verify
      v
     ready
      |
      | explicit operator approval
      v
   applying
    /    \
   v      v
processed failed
```

## Invariants

- A package exists in exactly one local public state at a time.
- State changes use atomic rename on one filesystem.
- `ready` means integrity, compatibility and preconditions were verified; it does not mean applied.
- `processed` means apply completed successfully and result metadata was recorded.
- `failed` is terminal until an explicit operator retry creates a new attempt.
- Duplicate identical deliveries are acknowledged idempotently.
- The same Work Block identity with different content is rejected.

## Transition journal

Every transition records:

- package identity and digest,
- source and destination state,
- RFC3339 timestamp,
- runtime version,
- exit code,
- concise reason,
- repository mutation status.

## Recovery

A stale lock or interrupted `applying` state is never silently resumed. The operator inspects the journal and chooses retry, rollback when supported, or manual recovery.