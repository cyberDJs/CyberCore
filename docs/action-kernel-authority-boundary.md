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

At the initial expiry check, before optional runtime setup or replay claiming, the bridge also captures the remaining UTC
authorization interval and a monotonic timestamp. A result is rejected when
monotonic elapsed time across claim acquisition and dispatch reaches that interval, even if the wall clock moves
backward. The UTC check remains active for forward clock corrections.

Hard cancellation/deadline propagation belongs to a later CyberHIVE contract
change and requires its own reviewed API rather than a thread-based timeout
shim that cannot safely stop already-running work.

## Clock observation boundary

The first observed UTC value must be trustworthy. The bridge captures a
monotonic bound before that value and accounts for subsequent sampling, setup,
claims and dispatch using one budget. UTC corrections predating the first UTC
observation cannot be reconstructed from these local samples; this is not an
authenticated time source. Tests inject corrections after the observed baseline
and retain no-claim/no-dispatch assertions. Detected process UTC rollback keeps
the replay guard failed closed; no automatic reset is introduced.

## Isolated ActionKernel issuance-clock hardening (PR #152)

The kernel stores a process-local construction UTC/monotonic baseline and samples
subsequent monotonic clock values under a per-kernel lock. The monotonic
high-water is nondecreasing across policy evaluation and issuance as well as
across requests. A same-process monotonic regression fails closed. A separate
trusted UTC high-water retains a forward correction seen by policy even when
wall time rolls back during a blocking audit. Each new UTC peak is paired with
its monotonic observation and projected forward by elapsed monotonic time;
a later raw UTC value only replaces the peak if it exceeds the *projected*
peak, preventing time corrections from reducing trusted elapsed time,
so a blocked audit cannot restart a grant at the later issuance sample.
Issued deadlines remain bounded by the peak's original observation time.

At issuance the absolute process-local deadline is the minimum of the
construction-baseline projection and the trusted current-UTC projection.
A transient forward UTC correction must not expand the duration of a grant.
This code remains a local read-only synthetic ActionKernel reference; it is
not a trusted cross-process authority, a hard cancellation mechanism, or
authenticated external time. The bridge retains the replay and UTC defenses
merged in PR #150, and additionally verifies the issuing PID and a finite,
nondecreasing monotonic sample against the original kernel-issued floor and
absolute deadline before claim/dispatch and after synchronous dispatch.
Missing/legacy receipt bounds fail closed; a result accepted after the
kernel-issued deadline is forbidden even after UTC rollback. Hard cancellation
is not provided.

Evidence requirements before promotion: exact-head Python 3.11-3.14 CI,
CodeQL, CyberHIVE contract, review of high-water/clock ordering, and a
separate independent security verdict. No merge or deployment authorized.

### Process replay monotonic rollback fence

The process-owned replay guard records both a UTC high-water and a monotonic
high-water under its claim/pruning lock. Before pruning or storing a claim it
rejects non-finite or decreasing monotonic samples and enters sticky
fail-closed state. A UTC correction that remains nondecreasing must not revive
a claimed receipt if the monotonic clock regresses after the cache's 300-second
minimum retention and a previous key was pruned. The caller-provided durable
claim store remains required, and no in-process cache is a replacement for
cross-process replay authority. Regression cases verify prune-then-rollback,
continued UTC progression, and persistent denial after a non-finite sample.
