# CyberCore Project State

_Last updated: 2026-07-30 01:01 CEST_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Stable branch: `main`
- Active branch: `feat/remote-aware-repository-identity`
- Active work block: `WB-0020 Remote-Aware Repository Identity v0.1`
- Governance rule: no production mutation without explicit human approval
- CI policy: local or self-hosted verification; GitHub Actions are not required

## Completed checkpoints

### PR #18 — Interactive demo, Project Kernel and CCL runtime foundation

Squash-merged into `main` as:

```text
df222d59635398d325d467110a7139210fe46396
```

Delivered:

- interactive demo and learning framework,
- architecture audit and reference architecture v2,
- CyberCore Genome v0,
- CCL-0001 through CCL-0005,
- JSON Schemas for the canonical lifecycle,
- CCL runtime validator and CLI,
- validation fixtures and tests.

Verification:

- `pytest -q`: **14 passed in 1.05s**,
- tested feature commit: `f83285474afe323eee6fd12296957283238258df`.

### PR #19 — Repository checkpoint runtime

Squash-merged into `main` as:

```text
4ef4bbf
```

Delivered:

- `cybercore checkpoint`,
- repository branch, commit and working-tree collection,
- Markdown and JSON checkpoint rendering,
- optional explicit file output,
- clean and dirty repository tests.

Verification:

- `pytest -q`: **18 passed in 3.23s**,
- checkpoint reported clean working tree,
- Project Kernel and Project State reported present.

### PR #20 — Controlled checkpoint persistence

Squash-merged into `main` as:

```text
de4f8f211ef1bf88db65b00ffb5ee577e9c20a86
```

Delivered:

- project-memory preview and explicit write mode,
- managed `PROJECT_STATE.md` synchronization,
- structured `WORKLOG.md` checkpoints,
- preservation of human-controlled governance content,
- validation of incompatible checkpoint options.

Verification:

- `pytest -q`: **23 passed in 5.90s**.

### PR #21 — Verification evidence automation

Merged into `main` as:

```text
d21e3bc3875bf298939585958c90167fa36dd76c
```

Delivered:

- structured repository- and commit-bound verification evidence,
- shell-free verification command execution,
- evidence validation during canonical checkpoint persistence,
- rejection of failed, stale, malformed, or mismatched evidence,
- generated-evidence exclusion from version control,
- managed checkpoint marker normalization while preserving human content.

Verification:

- `pytest -q`: **46 passed**.

### PR #22 — Idempotent canonical memory

Merged into `main` as:

```text
1e174e9180e64c3bfc5c70fa52d5c7e399ead9eb
```

Delivered:

- stable checkpoint identity independent of generation time,
- duplicate-safe `WORKLOG.md` checkpoint persistence,
- convergent repeated preview and write operations,
- staged canonical-memory writes,
- rollback after partial filesystem mutation,
- temporary-file cleanup and fault-injection coverage.

Verification:

- `pytest -q`: **52 passed**.

### PR #23 — feat: add controlled post-merge state transitions

Merged into `main` as:

```text
ca2da8b72563e65d0818861e00ff38ca6f12b75e
```

Completed artifact: `WB-0019`.

Verification:

- `pytest -q`: **66 passed**.

## Current milestone

Remote-Aware Repository Identity v0.1.

## Active objective

Make repository and checkpoint identity stable across clone paths by deriving it from a normalized Git remote when available.

Scope:

1. normalize supported HTTPS, SSH and SCP-style Git remote URLs;
2. derive canonical repository identity from the origin remote;
3. preserve a deterministic fallback for repositories without a usable remote;
4. make checkpoint identity identical across separate clone locations;
5. handle missing, changed and unsupported origin remotes safely;
6. preserve compatibility with existing path-bound checkpoint markers;
7. add normalization, migration and multi-clone regression tests;

## Current status

- Work block: active
- Branch: `feat/remote-aware-repository-identity`
- Project Kernel: present
- Runtime implementation: planned
- Tests: 66 passed
- Pull request: not created

## Next action

Define remote identity normalization contract and tests.


<!-- CYBERCORE:CHECKPOINT:START -->
<!-- CYBERCORE:PROJECT-STATE-CHECKPOINT:442641789d2135153b0a26c2388703342ef740b05a71357b7751f50d8ac0890f -->
## Automated repository checkpoint

- Generated: `2026-07-30T03:20:59.395931Z`
- Branch: `feat/post-merge-state-transition`
- Commit: `39987cefa72fbf1cc7ac8035701a50c8a7187dd4`
- Commit subject: test(cli): cover controlled post-merge write entrypoint
- Working tree: **clean**
- Test evidence: `66 passed`
- Project Kernel: present
- Project State: present
<!-- CYBERCORE:CHECKPOINT:END -->
