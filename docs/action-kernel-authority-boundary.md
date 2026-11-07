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

For trusted in-process use, the Action Kernel now binds each successful authorization
to two independent limits: the immutable UTC `authorization_expires_at` policy
bound and a process-local absolute monotonic deadline. The monotonic anchor is
captured by the trusted kernel before its final UTC authorization observation,
so subsequent scheduler delays are charged against the same budget. The receipt
also carries the issuing process id; the bridge fails closed if the monotonic
deadline is missing, non-finite, or belongs to another process.

The bridge does not reconstruct a deadline from later UTC samples. At entry,
before replay claim, after replay claim, and after synchronous dispatch it checks
both the UTC upper bound and the kernel-issued monotonic deadline. Backward wall
clock corrections therefore cannot extend authorization after issuance; forward
UTC corrections may still terminate it earlier.

Hard cancellation/deadline propagation belongs to a later CyberHIVE contract
change and requires its own reviewed API rather than a thread-based timeout
shim that cannot safely stop already-running work.


## ADR: process-local monotonic authorization deadline

**Status:** candidate, not authorized for production  
**Date:** 2026-11-07

### Context

Repeated adversarial review found that deriving a monotonic budget inside the
Hive bridge from interleaved UTC/monotonic samples leaves unavoidable sampling
windows. A scheduler pause plus partial wall-clock rollback can hide real elapsed
time before the bridge establishes its anchor.

### Decision

The trusted Action Kernel captures a process-local monotonic anchor, UTC anchor,
and process id at the start of `execute()`, before any injected audit callback
can block. After policy evaluation/audit it derives the absolute monotonic
authorization deadline from that original clock pair and records the deadline in
the internally generated `ExecutionReceipt`. Any scheduler or audit-callback
delay therefore consumes the original budget even if wall time is partially
corrected backward during the delay. The UTC expiry remains the externally
meaningful policy/audit bound. The trusted local broker forwards this receipt
internally without accepting caller-supplied receipts. The Hive bridge requires
both bounds and fails closed when the monotonic authority is absent, invalid,
expired, or from another process.

### Consequences

- Scheduler delay, including delay inside request/policy audit callbacks, and
  later wall-clock rollback cannot restart authorization.
- The process-owned replay cache retains consumed claims against the same
  monotonic authorization deadline, so forward/backward wall-clock corrections
  cannot prune a live replay claim early.
- Receipts containing monotonic deadlines are explicitly process-local and are
  not valid authorization objects across process restarts or IPC boundaries.
- Cross-process composition still requires an authenticated server-side
  authorization state or a separately designed deadline propagation protocol.
- The bridge keeps UTC checks for forward clock corrections and audit clarity.

### Rejected alternatives

- Repeated UTC/monotonic sampling inside the bridge: rejected after multiple
  adversarial P2 findings exposed gaps between samples.
- Thread/future timeout wrappers: rejected because they cannot safely cancel an
  already-running synchronous CyberHIVE dispatch.
- Treating a serialized monotonic float as portable authority: rejected because
  monotonic epochs are process/boot local.

### Rollback

Stop using the trusted Hive broker/bridge path and preserve existing audit and
replay records. Removing the new receipt fields restores the prior local API,
but must not be interpreted as restoring a safe bridge deadline mechanism.


## Process-construction monotonic clock floor

The Action Kernel now establishes its process-local clock authority when the
kernel instance is constructed, before any task can receive authority. The
kernel records a monotonic anchor, a UTC anchor, and the process id. A task's
absolute monotonic authorization deadline is derived only from that construction
anchor and the task's bound UTC expiry; it is no longer minted from a fresh
sequential UTC/monotonic sample pair at `execute()` entry.

For authorization decisions, trusted current time is the maximum of the live
UTC clock and the UTC value projected forward from the construction anchor by
monotonic elapsed time. A backward wall-clock correction therefore cannot move
trusted authorization time backward or extend a grant. A forward wall-clock
correction remains an upper bound and can only shorten/reject a grant.

The clock floor is process-local. A changed process id, non-finite/regressing
monotonic source, naive UTC source, or otherwise invalid floor fails closed and
must not mint a portable authorization. The existing receipt PID binding and
bridge monotonic deadline checks remain mandatory.


## Clock observation boundary and sticky rollback fence

The reconciled bridge preserves the process-wide rollback hardening introduced
by merged PR #150 without returning to bridge-derived authorization deadlines.
Every bridge UTC observation is serialized under the process-owned replay guard
lock and compared with a sticky maximum-seen UTC value. A detected backward UTC
step permanently fences that bridge process until restart; replacing the caller's
durable replay guard cannot clear the fence.

A forward UTC correction remains an external policy upper bound and can terminate
an authorization earlier than its kernel-issued monotonic deadline. If UTC later
moves backward, the sticky fence prevents the earlier termination from being
reversed. Replay claims themselves remain retained against the kernel-issued
process-local monotonic deadline, so wall-clock movement cannot prune a live
claim early.


## Conservative observation deadline and monotonic high-water

The kernel now carries two independent process-local deadline bounds for every
successful authorization. The construction-time UTC/monotonic floor remains the
long-lived process reference. Immediately before execution authority is issued,
the kernel also derives a deadline from the current trusted UTC/monotonic
observation. The receipt records the earlier of those two deadlines. A transient
forward UTC correction therefore cannot inflate the monotonic authorization
budget and later become exploitable if UTC is corrected backward.

Trusted clock observations are serialized inside the kernel and maintain a
nondecreasing process-local monotonic high-water mark. Any later trusted sample
below the previously accepted monotonic value fails closed even when it remains
above the original construction floor. This covers regressions hidden between
policy evaluation, blocking audit callbacks and final authorization, including
concurrent callers sharing one kernel instance.
