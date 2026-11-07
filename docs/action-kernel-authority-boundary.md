# Action Kernel authorization provenance boundary (WB-AK-007)

Status: **not authorized for production**. Tracking: #127.

## Threat: forged policy receipts

`ExecutionReceipt` and `PolicyVerdict` are Python dataclasses, not
cryptographically signed credentials. A caller capable of constructing those
objects can forge `status=EXECUTED`, `decision=ALLOW`, and matching task fields.
The current Hive bridge validates shape and correlation, but does not authenticate
the issuing authority. Therefore neither green unit CI nor real-class CyberHIVE
integration CI is evidence that arbitrary callers are authorized.

## Required integration boundary

- Trusted ingress authenticates actor and constructs `TaskRequest`; actor
  names in model-generated arguments are never identity claims.
- The same trusted backend owns policy evaluation, replay claim, and direct
  invocation of the local dry-run dispatcher. An external client must not be
  allowed to pass its own `ExecutionReceipt` object into a privileged bridge.
- For any split-process boundary, choose a verified authenticated transport
  with server-held authorization state and binding to task digest, expiry,
  capability, target and policy generation. Do not deserialize caller-supplied
  receipts as authority. Fail closed if the authority is unavailable.
- SQLiteReplayGuard is **single-host** atomic admission, not authentication.
  It also does not attest successful execution and does not permit safe
  automatic retry after a crash; consumed claims remain consumed.
- No change in this work block enables live operations, remote nodes, secrets
  or production integrations.

## Acceptance still outstanding for issue #127

An independent security review must verify the trusted caller/broker contract,
credential custody, persisted audit evidence and replay behavior under process
crash/restart. Production integration needs separate authorization and tests.


## Deadline semantics for the local dry-run MVP

The current CyberHIVE `NodeAgentRegistry.dispatch()` API is synchronous and
does not expose cancellation, a deadline parameter, or a safe way to terminate
an in-flight handler. CyberCore therefore does not claim to provide hard
execution cancellation in this MVP.

The bridge checks authorization expiry before claim, after replay claim, and
again immediately after synchronous dispatch returns. If dispatch crosses the
authorized deadline, its result is rejected fail-closed and both replay claims
remain consumed. This prevents a late result from becoming accepted evidence
or from being retried ambiguously.

Before the replay claim, the bridge also captures the remaining UTC\nauthorization interval and a monotonic timestamp. A result is rejected when\nmonotonic elapsed time across claim acquisition and dispatch reaches that interval, even if the wall clock moves\nbackward. The UTC check remains active for forward clock corrections.\n\nHard cancellation/deadline propagation belongs to a later CyberHIVE contract
change and requires its own reviewed API rather than a thread-based timeout
shim that cannot safely stop already-running work.
