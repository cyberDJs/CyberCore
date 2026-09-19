# WB-0038E — Execution Boundary Repair Evidence

Status: IMPLEMENTED_IN_BRANCH / VERIFICATION_PENDING

## Provenance

- Repository: cyberDJs/CyberCore
- Branch: wb-0038e-execution-boundary-repair
- Exact base: bb5fecce19aa7bf6ac0edaf0f780ff6364d020f1
- Authority: repo-only repair approved by the operator
- Remote deployment authority: false
- VPS mutation authority: false
- Credential or secret mutation authority: false
- Merge authority: false

## Confirmed defects addressed

1. The SSH client emitted protocol `version: 1` while the server exact-key schema rejected the field.
2. The SSH transport timed out after 30 seconds while mutating server operations could run for 120 seconds.
3. The bootstrap privilege path used `systemd-run`, allowing a transient-unit construction path under a Polkit rule intended only for bounded operations.
4. Rollback targeted the obsolete `/etc/sudoers.d/cybercore-exec` path instead of the installed Polkit rule.
5. Execution receipts exposed the raw authorization reference.
6. Existing tests did not exercise the real client payload against the server parser.
7. Mutating client and server paths treated a non-empty authorization reference as sufficient without structurally requiring an authorization verifier.

## Repair invariants

- Protocol version is one exact integer and is shared by client and server.
- Client payload must parse through the real `ServerRequest` contract.
- Transport timeout exceeds connection plus maximum server-operation budget.
- Mutating operations map only to preinstalled static wrapper services.
- Bootstrap file, unit, sshd, and Polkit installs encode explicit root:root ownership.
- systemd is reloaded before the Polkit rule becomes available.
- Polkit authorizes only `start` for the two exact static wrapper unit names.
- Rollback revokes the privilege rule before removing wrapper units.
- Raw authorization references are replaced by SHA-256 bindings in both local and server receipts.
- Mutating client and server operations fail closed unless an `ExecutionAuthorizationVerifier` explicitly authorizes the exact operation/target/plan/revision/reference tuple.
- The default verifier denies all mutations; the standalone server entrypoint has no permissive fallback.
- No deployment, VPS action, credential action, provider action, or production mutation is performed by this branch.

## Required verification before readiness

- focused execution/server/bootstrap tests;
- full repository CI on the exact branch head;
- CodeQL on the exact branch head;
- fresh independent review on the exact branch head;
- zero unresolved valid P1/P2 security or correctness findings.

Merge remains separately approval-gated.
