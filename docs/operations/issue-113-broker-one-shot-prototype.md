# CyberCore #113 — inert one-shot broker core candidate

Status: ISOLATED PROTOTYPE ONLY. No daemon, systemd socket/service, Polkit changes, SSH reload, credential provisioning, deployment or backup transfer.

Scope: src/cybercore/execution/nextcloud_r1_broker_core.py is a testable transaction core to support ADR-0016. It deliberately has no executable CLI, network listener or direct systemctl invocation. A future separately reviewed root-only Unix socket layer must obtain peer UID from kernel SO_PEERCRED; callers may not supply asserted UID in a request.

One-shot behavior: validate fixed target and exactly two operations, enforce trusted service UID, trusted root-only state directory, exclusive close-on-exec lock, and injected exact-action FileBoundExecutionAuthorizationVerifier. Before calling an injected fixed-argv runner, create an exclusive PREPARED record and fsync file+directory. A second request with the same exact operation identity fails closed, including when an earlier process died after PREPARED. On runner outcome create a separate result record; result is only local dispatch evidence, NOT transfer success, service readiness or independent activation proof.

The module does not itself read the production root-owned approval manifest: its verifier dependency must be the reviewed exact-action verifier, instantiated only inside a root-owned activation service. The synthetic tests use a fake verifier to isolate the transaction state machine. The marker key is SHA-256 of operation ID, operation, target and plan identity (no plaintext secret in receipt). No raw authorization reference is logged.

Negative/robustness tests: wrong peer uid, wrong action/target, missing authorization, unsafe state directory, symlinked lock, root identity check, replay, crash/PREPARED recovery, runner failure, concurrent duplicate dispatch, partial os.write completion, CLOEXEC lock descriptor and canonical operation-argv drift. Isolated target suite: python3 -m unittest discover -s tests -p test_nextcloud_r1_broker_core.py -v (requires PYTHONPATH=src).

Not yet proven: kernel SO_PEERCRED peer authentication; the trust of the service that supplies it; root-owned code delivery/installer SHA; validating the complete approval manifest at privilege boundary; parent directory hardening; direct systemctl DENY for the service account; real concurrent multiprocess lock/recovery; journal integrity and bounded size over repeated operations; real systemd restrictions; authorized source SFTP host-key and source archive checksum; actual transfer receipts; time-of-check/time-of-use threats; and full rollback.

SECURITY GATE: never install this module as a privileged broker, or pass subprocess/systemctl as runner on production, until the actual root-owned socket transport, exact approval binding, negative systemd/Polkit tests, replay recovery, threat model and rollback have independent exact-head review and a new explicit deployment approval. Current unsafe Polkit candidate remains blocked by PR #180. PR #181 is a separate docs-only ADR pending review.

Fixed actual target has service UID 995/GID 987 and eight code modules installed; credentials/state remain missing, systemd/SSH/Polkit inactive. No root production write in this branch.
