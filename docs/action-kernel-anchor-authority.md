# WB-AK-012 — independent checkpoint authority contract

Tracking: #127. Scope: isolated, read-only admission checks. **No external
checkpoint service is connected or trusted by this module.**

The `TrustedAnchorStore` protocol describes a separate authenticated authority
that must atomically compare-and-set checkpoints using a durable monotonic
sequence for each database identity. Its implementation is deliberately deferred:
the writer of the local audit database must not have permission to rewrite the
external accepted anchor.

`check_anchor_transition` rejects decreasing sequence numbers, identity
substitution, same-sequence conflicting hashes (equivocation), duplicates and
empty initial evidence. `verify_and_propose_anchor` additionally verifies that
the candidate exists in the local audit hash chain before it can be submitted
to the independent authority. These checks are **preflight only**, not a trust
grant. The external authority must recheck transition constraints transactionally
to avoid races. A returning `accepted=True` means only eligible for authority
review; it does not mean persisted, signed or authenticated.

Before production: choose a separate authority, independently verify identity,
protect signing credentials, implement atomic persistent monotonic CAS, handle
recovery and corruption, independently audit permissions and verify every
publication/read-back. Do not put the audit writer and anchor authority under
the same credentials. This PR changes no deployment, secrets or cloud service.
