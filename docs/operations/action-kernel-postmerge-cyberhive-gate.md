# Action Kernel / CyberHIVE post-merge contract gate

## Purpose

Keep the read-only local CyberHIVE integration contract visible on the exact
`main` commit after PR merges. Previously the workflow only ran on
`pull_request` and manual `workflow_dispatch`, leaving a verification gap
on the merge commit even when the PR synthetic-merge contract was green.

## Trigger and trust boundary

Workflow: `.github/workflows/action-kernel-real-hive.yml`.

- `pull_request` targeting `main`: regression check of GitHub's synthetic
  PR merge ref (`refs/pull/<number>/merge`), **not** the PR head commit.
  Default `actions/checkout` checks out the workflow event SHA.
- `push` to `main`: check the *resulting merge commit*, independently of
  the PR synthetic-merge run. This is post-merge detection, **not** a required pre-merge
  status or an authorization to deploy.
- `workflow_dispatch`: manual exact-branch verification when needed.

The workflow uses `permissions: contents: read`, pinned action SHAs,
`persist-credentials: false`, a pinned CyberHIVE source commit
(`0838b6a9d8f6f614ef7cd678335a82a899946aa5`), and the local
`integration_tests/test_real_hive_node_agent.py` test. It does not contact
production nodes or perform a deployment.

## Verification and rollback

For the candidate PR, bind the source diff and independent review to the
candidate head commit SHA. Confirm required CI/CodeQL and the PR event's
`real-hive-contract` run succeeded, recording the **synthetic PR merge SHA**
that GitHub checked out, rather than falsely labeling that test as an
exact-head test. Any actual head-SHA execution requires separate evidence.
After a separately authorized merge, compare the new `main` SHA with the
`push` workflow run's `head_sha` and require `real-hive-contract` PASS.
A green synthetic PR merge run alone does not prove a green post-merge run.

If the trigger produces unexpected effects, revert only the added
`push: branches: [main]` trigger in a reviewed PR. Do not weaken the
existing PR/manual gates or branch protection. In case of failure, investigate
the exact merge commit and its logs; do not assume an upstream CyberHIVE
revision is safe because this contract pins an older commit.

This gate is a local software compatibility check. It does not prove runtime
safety, production rollout health, or authentication of external evidence.
