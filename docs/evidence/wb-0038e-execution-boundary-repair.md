# WB-0038E — Execution Boundary Repair Evidence

Status: MERGED_CANONICAL / REPOSITORY_VERIFIED / NOT_DEPLOYED

## Provenance

- Repository: cyberDJs/CyberCore
- Repair branch: wb-0038e-execution-boundary-repair
- Pull request: #95
- Exact repair base: bb5fecce19aa7bf6ac0edaf0f780ff6364d020f1
- Exact approved head: 4dbb0202cf959443f768871fa299e2d370ce680f
- Merge commit: 3884f6b605a1fb3b0003b142044485cb9ba6ecce
- Authority: repo-only repair plus explicit exact-head merge approval
- Remote deployment authority: false
- VPS mutation authority: false
- Credential or secret mutation authority: false
- Production execution authority: false

## Confirmed defects addressed

1. The SSH client emitted protocol `version: 1` while the server exact-key schema rejected the field.
2. The SSH transport timed out after 30 seconds while mutating server operations could run for 120 seconds.
3. The bootstrap privilege path used `systemd-run`, allowing a transient-unit construction path under a Polkit rule intended only for bounded operations.
4. Rollback targeted the obsolete `/etc/sudoers.d/cybercore-exec` path instead of the installed Polkit rule.
5. Execution receipts exposed the raw authorization reference.
6. Existing tests did not exercise the real client payload against the server parser.
7. Mutating client and server paths treated a non-empty authorization reference as sufficient without structurally requiring an authorization verifier.
8. Upgrade ordering could leave the legacy Polkit rule effective while static wrapper names were being established.
9. The strict installer sandbox ignored a missing `/opt/backups/vikunja`, causing first-run installation failure on a clean target.
10. Rollback could continue removing static wrapper units when an exact-match privilege-policy removal was skipped because of local drift.

## Canonical repair invariants

- Protocol version is one exact integer shared by client and server.
- Client payload parses through the real `ServerRequest` contract.
- Transport timeout exceeds connection plus maximum server-operation budget.
- Mutating operations map only to preinstalled static wrapper services.
- Bootstrap file, unit, sshd, and Polkit installs encode explicit root:root ownership.
- Existing managed privilege is revoked and verified ineffective before either static wrapper name is installed or reused.
- Both wrapper names must be verified free of unsafe transient-unit occupation before installation proceeds.
- `/opt/backups/vikunja` is created as `root:root` mode `0700` before the strict installer sandbox can start.
- systemd is reloaded before the narrowed Polkit rule becomes available.
- Polkit authorizes only `start` for the two exact static wrapper unit names.
- Rollback verifies effective privilege revocation before removing wrapper units; failure stops rollback and retains the occupied wrapper names.
- Raw authorization references are replaced by SHA-256 bindings in local and server receipts.
- Mutating client and server operations fail closed unless an `ExecutionAuthorizationVerifier` explicitly authorizes the exact operation/target/plan/revision/reference tuple.
- The default verifier denies all mutations; the standalone server entrypoint has no permissive fallback.

## Exact-head verification

On repair head `4dbb0202cf959443f768871fa299e2d370ce680f`:

- CI #857: PASS.
- CodeQL #858: PASS.
- Fresh exact-head Codex review: completed with no major issues.
- Unresolved review threads before merge: 0.

Post-merge on canonical `main@3884f6b605a1fb3b0003b142044485cb9ba6ecce`:

- CI #858: PASS.
- CodeQL #859: PASS.

## Effect boundary

The repository contract is repaired and canonical. This is not proof of deployed runtime mutation readiness.

WB-0038E did not:

- deploy the subsystem;
- create or rotate SSH credentials;
- mutate sshd or Polkit on a target;
- install a production authorization verifier;
- execute Vikunja backup mutations;
- grant production or provider authority.

A future deployment still requires a separately reviewed target-bound plan, a real authorization verifier backed by canonical approval state, runtime verification, rollback evidence, and explicit deployment authority.

## Residual follow-up

Open PR #94 is mostly superseded by PR #95, but it contains one narrower response-hardening change not present in canonical main: rejected `RequestValidationError` details are replaced with a fixed remote-facing message. That hardening should be extracted as a separate minimal change rather than merging the stale eight-file PR.
