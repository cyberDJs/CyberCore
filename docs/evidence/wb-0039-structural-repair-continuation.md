# WB-0039 structural repair continuation

Status: IMPLEMENTED_IN_BRANCH / HOSTED_VERIFICATION_PENDING
Date: 2026-09-29

Authority: APPROVE CONTINUE STRUCTURAL REPAIR PR99 @ e6150329105748a84813ce074c3fd3e09c888890

Scope is limited to PR99 authority grammar and regression coverage. No merge, deployment,
production mutation, provider change, credential change, or main-branch mutation is authorized.

Repair rules:
- perfect-passive authority descriptions are detected only before a relative-clause boundary,
  preserving explicit commands whose object contains a relative perfect-passive clause;
- progressive descriptive condition predicates such as showing/displaying cannot grant CANCEL;
- cancel markers used as noun modifiers such as stop button / cancel message are non-authoritative;
- comma-scoped negation remains active across coordinated cancel markers;
- polite APPROVE prefixes are accepted symmetrically with EXECUTE.

Fresh CI, CodeQL, and exact-head review remain required before readiness.
