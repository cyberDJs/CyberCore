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

### Canonical consolidation of PR #151 and PR #152

This isolated candidate originates from PR #152 HEAD
`1815d3bf770b0e12eec9d80fd73ff1144a8228eb` and retains the
paired UTC/monotonic high-water, original kernel-issued PID and deadline
checks in the CyberHIVE bridge, and sticky replay monotonic high-water.

It also brings forward the distinct PR #151 protection (snapshot
`5db815a5365ccee755fdbcb29d768c9fb28b8ab3`): the kernel re-observes
trusted UTC and monotonic high-water **after execution and evidence audit
callbacks** before returning an authorized receipt. The previously computed
deadline is never enlarged; expiration fails closed as `FAILED/EXPIRED` and
the task ID remains consumed after reaching the execution boundary.

Regression evidence: post-authorization blocking callbacks at both execution
and evidence stages, with a ten-second monotonic delay and partial UTC rollback,
plus duplicate task reservation; supplemented by the independent PR #152
clock/replay regressions. This candidate is not approval to merge or deploy,
and the two source PR branches remain unchanged. An independent security
review must reconcile any additional unique PR #151 test coverage and validate
the final exact SHA before promotion.

### Sticky Action Kernel clock-authority invalidation (post-#154 follow-up)

The kernel's per-instance time authority is now latched invalid if a
trusted-time observation detects a PID change, malformed/non-finite sample,
naive UTC, or monotonic regression below the recorded high-water mark.
Subsequent calls to the *same* kernel instance fail closed even if the
next wall/monotonic readings look plausible. Reconstructing a kernel must
re-establish the process-local baseline and satisfy normal authorization;
there is no automatic reset of the invalidation flag.

This closes the distinct PR #153 regression
`test_invalid_monotonic_observation_latches_kernel_fail_closed`
that was not present after consolidated PR #154. The fix does not
make process-local clocks an authenticated time source or replace
durable cross-process replay protection. Verify exact-HEAD CI,
CodeQL, CyberHIVE contract and independent security review before
any separate merge decision.

### Sticky issued-clock authority fence (isolated follow-up)

A rejected nonfinite/regressed monotonic observation permanently revokes that
ActionKernel instance; recovering the observed counter cannot renew authority.
The bridge's process-owned replay guard additionally serializes kernel-issued
monotonic checks across invocations, retains a process-wide high-water, and
latches invalid issued-clock samples before claim. Thus retrying an unclaimed
receipt after its clock appears to recover cannot dispatch. A normal per-receipt
deadline expiry does not poison other receipts, but it still rejects the expired
receipt. An observed rollback invalidates all future issued-receipt bridge
attempts in that process. Restarting a process is not a substitute for trusted
time or durable replay protection, and the protection cannot detect an
unobserved clock correction. The reference remains synthetic/read-only.

Evidence: sticky kernel regression/nonfinite recovery tests, bridge entry
retry/nonfinite recovery tests, and cross-receipt high-water regression. Review
the fail-closed impact on liveness and the sampling lock's serialization
before promotion. The existing source branches and main remain untouched.


Reconciliation with merged PR #157 keeps its kernel clock latch implementation
and regression intact; this repair adds bridge-issued clock failure fencing and
retains the additional kernel nonfinite recovery coverage.

### Every bridge monotonic observation uses one sticky process authority

Budget anchors and elapsed-budget checks, issued-deadline checks, and replay
pruning now sample their production monotonic aliases under the same process
guard lock and share a high-water and permanent failure state. A nonfinite,
regressing, malformed or failed clock observation cannot be hidden by a later
plausible reading, even if it occurs before a durable replay claim. Budget
arithmetic therefore never consumes an unchecked NaN/infinity. Replacing the
caller-provided durable guard does not reset the bridge-owned clock fence.

An otherwise valid observation past one receipt's absolute deadline rejects
that receipt without poisoning later valid grants. Clock failure deliberately
revokes process bridge authority; this availability tradeoff has no automatic
reset. Delayed synchronous effects still cannot be cancelled or undone by
these result-acceptance checks. Initial UTC trust and durable shared replay
storage remain separate requirements.

### Kernel provider failures cannot restore clock authority

The kernel trusted-time boundary latches failure across provider exceptions,
malformed PID/monotonic/UTC observations, timezone failures and projection
overflow, in addition to regressed/nonfinite monotonic values. Sampling,
validation and projection remain serialized by its existing lock; high-water
state is committed only after the complete observation succeeds. A plausible
later value, the same task or a fresh task cannot clear the per-instance fence.
Failures use the existing PermissionError authority contract with the original
exception chained for diagnosis. KeyboardInterrupt/SystemExit are not caught.

This closes the independent review's inherited conditional P2 under injected
provider continuity loss plus stale UTC/monotonic recovery. It is not evidence
that normal OS monotonic clocks exhibit that fault. Raw UTC audit/provenance
metadata retains its raw wall-time values and does not advance the authority
high-water. Its provider failures or malformed timestamps also latch the same
kernel fence: an earlier metadata read must not hide continuity loss from the
next authorization. Sampling uses the same lock without adding monotonic reads
or projecting metadata time. Ordinary policy denial and normal expiry remain;
an expired grant with otherwise valid clocks does not invalidate the kernel.
