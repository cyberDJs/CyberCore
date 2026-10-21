# WB-AK-008: trusted local broker (candidate)

Tracking: #127. This component is **not** an independently authenticated
remote API, and must not be exposed to model-controlled callers.

## Security boundary

The application, not the model, constructs `ActionKernel` with its allowlist,
policy/audit sink, and trusted `NodeAgentRegistry` plus replay guard.
`TrustedLocalHiveBroker.execute(task, authenticated_actor=...)` accepts only an
identity authenticated by that application, not a string copied from model
output. The broker evaluates the policy and uses the resulting receipt internally.
Callers cannot submit their own `ExecutionReceipt`.

Existing direct `run_local_hive_dry_run` is **not** an authenticated public
entry point. Keep it restricted to trusted local code. No live operation is
enabled, and all Hive requests remain explicitly dry-run.

## Important limitations

- Caller authentication/transport and secure credential storage are **outside**
  this work block. Merely naming `authenticated_actor` does not authenticate it.
- Current `ActionKernel` audit sink is injected; this PR adds **no persistent
  single-writer audit backend**. If the sink is unavailable, policy denies.
- Binding and signing receipts across processes is not solved by this broker.
- SQLite replay guarantees are scoped to a single local host.
- Rollback: remove broker use, preserve audit/replay records; no migration needed.

## Verification

Tests reject actor impersonation, disabled policy and missing audit, and check
that the broker has no API parameter accepting an external receipt.
A separate full CyberHIVE runtime integration is required before promotion.
