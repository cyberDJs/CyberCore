# Action Kernel MVP acceptance evidence — WB-CC-FINAL-01

Tracking: issue #118. Candidate base: PR #143 exact head `b3ec55f6151c726e2c585f4ecaf759d9753474c9`.

This document is evidence mapping for the local, read-only MVP only. It does
not authorize merge, deployment, remote node enrollment, live operations, or
production use.

| Issue #118 acceptance gate | Candidate evidence |
| --- | --- |
| Typed task traverses policy, read-only executor and returns auditable receipt | Action Kernel unit tests, trusted local broker tests, real CyberHIVE contract gate |
| Denied/unknown capability and spoofed actor fail closed | `test_feature_disabled_untrusted_and_spoofed_actor_fail_closed`, unknown capability/target tests, broker spoof test |
| Oversized/malformed payload fails closed | request size, malformed JSON/non-finite argument and evidence-size tests |
| Backend/audit unavailable fails closed | audit unavailable/failure and replay backend failure tests |
| Timeout/deadline fails closed | pre-claim, post-claim and post-dispatch authorization-expiry regressions; late synchronous dispatch result is rejected |
| No production network calls needed in CI | Action Kernel and CyberHIVE contract gates use local typed dry-run interfaces |
| No raw credentials to agents | typed request/receipt contracts contain no credential payload; authority docs prohibit caller-supplied authority |
| No extra ledger writer/event bus | local broker reuses injected audit sink and existing CyberHIVE registry/runtime contracts |
| Rollback and capability disable switch documented | feature-disabled policy path plus trusted-local-broker rollback notes |
| Security review and required CI pass | exact-head CI, Python 3.11-3.14, Ruff, Pyright, package, CodeQL, real CyberHIVE contract, independent review required before promotion |

## Timeout/deadline scope

The current CyberHIVE `NodeAgentRegistry.dispatch()` contract is synchronous
and has no cancellation/deadline argument. WB-CC-FINAL-01 therefore closes the
MVP acceptance gap by enforcing an authorization deadline on result acceptance:

1. authorization is checked before optional runtime work;
2. checked again at the claim boundary;
3. checked after replay claims and before dispatch;
4. checked immediately after synchronous dispatch returns;
5. a late result is rejected fail-closed and replay claims remain consumed.

This is intentionally not described as hard cancellation. A future remote or
long-running execution contract must propagate a deadline/cancellation token at
the CyberHIVE API boundary and will require a separate work batch and approval.

## Promotion rule

Do not mark issue #118 complete until the candidate exact head has all required
checks green and an independent exact-head review with no unresolved P1/P2
findings. Merge and deployment remain separate approval gates.
