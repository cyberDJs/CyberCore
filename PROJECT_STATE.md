# CyberCore Project State

_Last updated: 2026-08-03 10:47 CEST_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Stable branch: `main`
- Active branch: `feat/main-branch-protection-enforcement`
- Active work block: `WB-0026 Main Branch Protection Enforcement`
- Governance rule: no production mutation without explicit human approval
- CI policy: GitHub Actions verification is required before merge; `main`
  branch protection is active and verified through ruleset
  `main-branch-protection` (`18986451`)
- CodeQL policy: Advanced setup is verified; GitHub Default setup is disabled to avoid conflicting scans

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

### PR #24 — feat: add remote-aware repository identity

Merged into `main` as:

```text
5ac0db5278acc57710f4987ba34e605cdaaf2ec3
```

Completed artifact: `WB-0020`.

Verification:

- `pytest -q`: **78 passed**.

### PR #25 — feat: add repository identity diagnostics

Merged into `main` as:

```text
6c9a4cff56731e8e53bfb886fde6c61a2340a085
```

Completed artifact: `WB-0021`.

Verification:

- `pytest -q`: **86 passed**.

### PR #26 — feat: enforce canonical repository identity policy

Merged into `main` as:

```text
e674edc707a17ab8eb9ba1af9d40ae7a80657334
```

Completed artifact: `WB-0022`.

Verification:

- `pytest -q`: **98 passed**.

### PR #27 — feat: add trusted operation context

Merged into `main` as:

```text
03a04c5ad73489775552df34e21baa559f2a41da
```

Completed artifact: `WB-0023`.

Verification:

- `pytest -q`: **109 passed**.

### PR #29 — fix: enforce operation context disclosure policy

Merged into `main` as:

```text
1ba003f8e17448ac8f962955f88d6214c58c6cb2
```

Completed artifact: `WB-0024`.

Verification:

- `pytest -q`: **201 passed**.

### WB-0025 Slice 1 — CI foundation

Merged through PR #30 into `main` as:

```text
dbd61e9094d2b45ce11468d12b3700c66979cd0b
```

Verification:

- local verification: **214 passed**;
- GitHub Actions run `30602280063`: **6/6 jobs passed**;
- Python 3.11, 3.12, 3.13 and 3.14 passed;
- Ruff, Pyright, package build and clean-wheel smoke test passed.

### WB-0025 Slice 2 — CodeQL and merge gates

Merged through PR #31 into `main` as:

```text
bd635ca56bd2cb7ce0b221c03e9664b128095d25
```

Delivered:

- pinned advanced CodeQL workflow for Python;
- workflow-security tests for all `.github/workflows/*.yml` files;
- exact proposed required checks for `main`;
- branch-protection activation, rollback, and broken-check runbook;
- explicit non-mutation boundary for repository settings.

Verification:

- local validation completed: Ruff passed, Pyright reported 0 errors, pytest reported
  218 passed, compileall passed, package build passed, scripts/verify.sh passed,
  git diff --check passed, and the workflow security audit passed;
- GitHub Actions run `30774683751`: **passed**;
- CodeQL run `30774683774`: **passed** under the stable `codeql` job;
- GitHub CodeQL Default setup conflicted with the repository Advanced setup,
  was disabled by explicit human action, and the retry succeeded;
- branch protection remained disabled for PR #31 and was later activated under
  WB-0026 only after explicit human approval.

## Current milestone

Main Branch Protection Enforcement v0.1.

## Active objective

Record that `main` branch protection for PR #32 was explicitly approved,
activated, and verified while keeping WB-0026 active until PR #32 is reviewed
and merged.

Scope:

1. record explicit human approval for activating `main` protection;
2. record ruleset `18986451`, `main-branch-protection`, activated at
   `2026-08-03T10:47:03.259+02:00`;
3. record the active ruleset configuration and required checks;
4. record hosted verification against PR #32;
5. preserve rollback and keep WB-0026 active until PR #32 is reviewed,
   approved, merged, and protected `main` is verified after merge.

## Current status

- Work block: active
- Branch: `feat/main-branch-protection-enforcement`
- Project Kernel: present
- Runtime implementation: implemented
- Pull request: #32, draft
- Ruleset: `18986451` (`main-branch-protection`), target `branch`, target ref
  `~DEFAULT_BRANCH`, enforcement `active`, bypass actors `none`,
  `current_user_can_bypass: never`
- Activated: `2026-08-03T10:47:03.259+02:00` after explicit human approval
- Rules enabled: deletion protection, non-fast-forward protection, pull request
  required, one approving review required, stale approvals dismissed after push,
  review thread resolution required
- Rules not enabled: CODEOWNERS review not required, last-push approval not
  required, linear history not required
- Allowed merge methods: merge, squash, rebase
- Required checks: `tests (python 3.11)`, `tests (python 3.12)`,
  `tests (python 3.13)`, `tests (python 3.14)`, `quality`, `package`, `codeql`
- Required status-check policy: `strict_required_status_checks_policy: true`,
  `do_not_enforce_on_create: false`
- Verification against PR #32: head commit
  `c3868e058f42dfbb8c0c4bdf3eabfe094dd91ccf`; CI run `30784170890`
  passed; CodeQL run `30784170892` passed; all seven required contexts
  passed; PR mergeable `MERGEABLE`; merge state `BLOCKED`; review decision
  `REVIEW_REQUIRED`; PR remains draft
- Check-name distinction: the informational workflow check is named `CodeQL`,
  while the required ruleset context is the lowercase job context `codeql`
- Rollback: disable enforcement only for ruleset `18986451`, verify there is
  no active `main` enforcement, repair on a feature branch, and reactivate only
  after hosted CI and CodeQL checks succeed
- Tests: git diff --check passed; PYTHON=.venv/bin/python scripts/verify.sh
  passed on rerun after sandbox DNS failure: Ruff passed, Ruff format check
  passed, Pyright 0 errors, pytest 218 passed in 56.21s, compileall passed,
  package build passed

## Next action

- Update PR #32 metadata to reflect active and verified main protection.
- Mark PR #32 ready for review.
- Request independent approval from nulleimy.
- Merge only after all seven required checks succeed and approval is present.
- Verify protected main after merge and close WB-0026.

<!-- CYBERCORE:CHECKPOINT:START -->
<!-- CYBERCORE:PROJECT-STATE-CHECKPOINT:57437a493ae5230754384e34abb1e68eaf05619f1e4685fcc4f88e59ca239eff -->
## Automated repository checkpoint

- Generated: `2026-08-03T03:26:41.606453Z`
- Branch: `feat/main-branch-protection-enforcement`
- Commit: `bd635ca56bd2cb7ce0b221c03e9664b128095d25`
- Commit subject: ci(security): add CodeQL analysis and merge-gate contract (#31)
- Working tree: **dirty**
- Test evidence: `git diff --check passed; PYTHON=.venv/bin/python scripts/verify.sh passed: Ruff passed, Ruff format check passed, Pyright 0 errors, pytest 218 passed in 60.45s, compileall passed, build passed; GitHub Actions run 30774683751 passed; CodeQL run 30774683774 passed`
- Project Kernel: present
- Project State: present
<!-- CYBERCORE:CHECKPOINT:END -->
