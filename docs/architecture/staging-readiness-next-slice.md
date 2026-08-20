# Staging Readiness Next Slice

Date: 2026-08-20
Status: Planning note

## Context

PR #47 merged WB-0029: a disabled/manual plan-only staging workflow and manifest validator.

That workflow proves a safe validation path exists, but it does not connect to InterServer and does not authorize remote writes.

## Next non-production slice

The next safe implementation slice should prepare staging readiness without crossing the remote-write boundary:

1. define target identity evidence fields;
2. define secret alias readiness checks without reading secret values;
3. define rollback readiness checks;
4. define effect verifier readiness checks;
5. add tests proving `staging_apply` remains blocked until all gates and fresh operator authorization exist.

## Still blocked

- live InterServer remote write;
- production deployment;
- provider mutation;
- DNS, mail, billing, DirectAdmin, VPS, WordPress, Nextcloud mutation;
- plaintext secret read/storage.

## Promotion rule

A future remote-write PR must be a separate work block with a MOP, rollback, effect verifier, target identity evidence, secret alias evidence, and fresh explicit operator authorization.
