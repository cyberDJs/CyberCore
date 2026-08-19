# WB-0028 Change Budget

Date: 2026-08-19

## Budget

This slice may change documentation, project state, target contracts, and audit evidence.

It must not add executable deployment automation or perform remote mutation.

## Reason

The first safe step is to define the self-deployment boundary before implementing a runner.

## Drift condition

If the PR starts adding live deployment execution, secrets, provider changes, or production behavior, it exceeds WB-0028 scope and must be split.