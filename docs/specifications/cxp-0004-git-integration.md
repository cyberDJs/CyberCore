# CXP-0004 — Git Integration v1

## Status

Proposed for WB-0006 design freeze.

## Purpose

Define the post-apply Git workflow without allowing the Exchange runtime to silently publish code.

## Boundary

CXP v1 separates four stages:

```text
verify → apply → test → publish to GitHub
```

The Exchange runtime may perform `verify` and, after explicit approval, `apply`. Git commit, push and pull-request creation are separate operator-visible actions.

## Repository contract

Before any mutation, the integration must validate:

- the repository root is explicit and not inferred from `$HOME`,
- `origin` resolves to the repository declared in `manifest.json`,
- expected marker files are present,
- the current branch matches the package policy,
- the working tree satisfies the declared cleanliness policy,
- the package is not applied directly to protected `main`.

## Commit policy

A successful Work Block produces at most one logical commit by default.

Recommended message:

```text
<type>: <meaningful summary> [WB-XXXX]
```

The commit must include the Work Block record and must not include secrets, local runtime state, generated caches or private inventory.

## Push policy

- Push targets a feature branch.
- Force push is forbidden by default.
- A failed push does not roll back a successful local apply; the state must remain explicit.
- Credentials are provided by the operator environment, never by the package.

## Pull request policy

The PR description must reference:

- Work Block ID,
- summary and scope,
- verification results,
- risks and rollback notes,
- related ADRs or specifications.

PR creation may be automated only after the operator explicitly approves publish.

## Failure semantics

Git publication failures are distinct from apply failures. Runtime state must report:

```text
APPLIED_NOT_PUBLISHED
```

until commit, push and PR steps complete or the operator intentionally abandons publication.
