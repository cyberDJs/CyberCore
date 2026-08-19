# WB-0028 Capability Snapshot

Date: 2026-08-19
Work block: `WB-0028`

## Available now

- GitHub repository read/write through connector.
- Non-canonical branch creation.
- File creation/update in branch.
- Pull request creation.
- GitHub Actions CI/CodeQL verification after PR creation.
- PR review/comment/thread inspection.
- PR merge after explicit operator authorization and green gates.

## Not available or not yet verified

- Direct InterServer control panel mutation.
- Direct InterServer SSH/SFTP session.
- Direct DNS/mail/billing mutation.
- Secret store inspection.
- Live staging URL verification.
- Browser/runtime verification of InterServer staging.

## Policy decision

Allowed automatically in this slice:

- documentation;
- state metadata;
- target contract without secrets;
- ADR candidate;
- audit evidence;
- draft/ready PR.

Requires explicit later approval:

- live staging deployment;
- provider mutation;
- secret creation/rotation;
- production promotion;
- ADR acceptance.