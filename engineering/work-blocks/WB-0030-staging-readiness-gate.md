# WB-0030 — Staging Readiness Gate

Status: Active candidate
Date: 2026-08-20
Canonical repository: `cyberDJs/CyberCore`
Target branch: `feat/wb-0030-staging-readiness-gate`

## Goal

Add a fail-closed readiness gate before any future live InterServer staging remote-write work.

## In scope

- Non-secret readiness evidence example.
- Local readiness validator.
- CLI for validating readiness evidence.
- Tests proving the gate blocks until all readiness fields are verified or approved.
- State and audit documentation.

## Out of scope

- Live InterServer deployment.
- Staging remote write.
- Production deployment.
- DNS, mail, billing, DirectAdmin, VPS, WordPress, or Nextcloud mutation.
- Reading or storing plaintext secrets.
- Accepting new ADRs.

## Safety model

The readiness gate requires all of the following before a later work block may even ask for first remote-write authorization:

- staging URL verified;
- staging path verified;
- secret aliases verified without plaintext values;
- rollback verified;
- effect verifier verified;
- fresh operator authorization approved.

The example readiness evidence is intentionally not ready and must fail closed.

## Exit criteria

- Tests pass.
- CI and CodeQL pass.
- Manual AI review passes.
- PR is ready for merge with explicit operator authorization.
