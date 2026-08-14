# CyberCore Worklog

## 2026-07-22

### Completed

- Resolved README merge artifacts.
- Restored `src/cybercore/cli.py` after accidental truncation.
- Added `cybercore demo` and `cybercore learn` command wiring.
- Added Rich-based presentation layer.
- Added deterministic UC-001 demo flow.
- Added introductory Evidence First lesson.
- Added asciinema recording helper.
- Added `rich` as a runtime dependency.
- Established `PROJECT_STATE.md` as the canonical project-state checkpoint.

### Verification

Local verification on macOS with Python `3.14.6`:

- `pytest -v` -> 10 passed
- `cybercore demo --delay 0` -> passed
- `cybercore learn --non-interactive` -> passed
- `cybercore doctor` -> passed with one non-blocking Exchange Agent warning
- `python -m compileall -q src demos` -> passed

### Commits of note

- `f23a42cf65fca1e5ab120b9d21fe85a32d3413cb` - README cleanup
- `11e25ad1a359be06103b737e2b18778e48460d02` - restore CLI and wire demo/learn
- `ee4921c19ba8c75f81bbdc42e4b2a2a4bd56dc93` - canonical project-state checkpoint

### Outcome

PR #18 is technically verified. Next work should focus on persistent project memory automation as a separate work block.

## 2026-08-03

### Completed

- Continued `WB-0026` on branch `feat/main-branch-protection-enforcement`.
- Aligned canonical documentation after PR #31.
- Recorded successful GitHub Actions CI run `30774683751`.
- Recorded successful CodeQL run `30774683774`.
- Recorded that GitHub CodeQL Default setup conflicted with the repository
  Advanced setup, was disabled by explicit human action, and the retry
  succeeded.
- Recorded explicit human approval to activate `main` branch protection for
  repository `cyberDJs/CyberCore`.
- Recorded ruleset `18986451` (`main-branch-protection`) with target `branch`,
  target ref `~DEFAULT_BRANCH`, enforcement `active`, no bypass actors,
  `current_user_can_bypass: never`, and activation timestamp
  `2026-08-03T10:47:03.259+02:00`.
- Recorded exact active rules: deletion protection, non-fast-forward
  protection, pull request required, one approving review required, stale
  approvals dismissed after push, review thread resolution required,
  CODEOWNERS review not required, last-push approval not required, allowed
  merge methods `merge`, `squash`, and `rebase`, and linear history not
  required.
- Recorded required checks: `tests (python 3.11)`, `tests (python 3.12)`,
  `tests (python 3.13)`, `tests (python 3.14)`, `quality`, `package`, and
  `codeql`.
- Recorded required status-check policy:
  `strict_required_status_checks_policy: true` and
  `do_not_enforce_on_create: false`.
- Recorded activation-time PR #32 verification snapshot at head commit
  `c3868e058f42dfbb8c0c4bdf3eabfe094dd91ccf`: CI run `30784170890`
  passed, CodeQL run `30784170892` passed, and all seven required contexts
  passed.
- Recorded pre-correction PR #32 verification snapshot at head commit
  `034c77e156725169afb75e1cc89364bac252c67e`: CI run `30806185333`
  passed, CodeQL run `30806185411` passed, and all seven required contexts
  passed.
- Recorded that merge-time evidence must come from the final PR head after the
  final push.
- Documented that the informational check is named `CodeQL`, while the
  required ruleset context is the lowercase job context `codeql`.
- Preserved WB-0026 as active until PR #32 is reviewed, approved, merged, and
  protected `main` is verified after merge.
- Corrected rollback policy so a single failed required context does not
  disable the complete ruleset: preserve unaffected protections, change only
  the broken context through explicit approval, repair on a feature branch,
  and restore it only after hosted checks succeed.
- Reserved complete ruleset disablement for ruleset-wide failure with
  equivalent replacement protection active first.
- Did not commit, push, or change GitHub repository settings in this
  documentation update.
- Automated Codex review of head
  `034c77e156725169afb75e1cc89364bac252c67e` identified two findings:
  selective rollback must preserve unaffected protections, and earlier run
  evidence must be explicitly classified as snapshots rather than final-head
  merge evidence.
- Addressed both findings in canonical documentation.
- Recorded that the corrective push dismisses the existing approval and
  requires a fresh independent approval from `nulleimy`.

### Verification

- `git diff --check`: passed.
- `PYTHON=.venv/bin/python scripts/verify.sh`: Ruff passed, Ruff format check
  passed, Pyright reported 0 errors, pytest reported 218 passed, compileall
  passed, and package build passed.

## Checkpoint 2026-07-29T20:55:18.888287Z

- Branch: `feat/checkpoint-persistence`
- Commit: `81afdbe2ec202fba270ee28a49dacb13ca876040`
- Commit subject: docs(project): align checkpoint persistence state
- Working tree: **clean**
- Test evidence: `23 passed in 7.15s`
- Next action: Prepare PR #20

## Checkpoint 2026-07-29T21:49:59.921455Z

- Branch: `feat/verification-evidence`
- Commit: `82feab5229e9ca9a9d058b6867d049c1c8c76326`
- Commit subject: fix(checkpoint): preserve human text after legacy blocks
- Working tree: **clean**
- Test evidence: `46 passed`
- Next action: Prepare PR #21

<!-- CYBERCORE:WORKLOG-CHECKPOINT:f2e9c5eb99c292370057345207732f89d944dd2321593ba948f441e481567ccb -->
## Checkpoint 2026-07-29T22:48:27.668847Z

- Branch: `feat/idempotent-canonical-memory`
- Commit: `7d174275317df9c2b202d18f40154121cc9e4f54`
- Commit subject: docs(project): align WB-0018 canonical state
- Working tree: **clean**
- Test evidence: `52 passed`
- Next action: Prepare PR #22

<!-- CYBERCORE:WORKLOG-CHECKPOINT:442641789d2135153b0a26c2388703342ef740b05a71357b7751f50d8ac0890f -->
## Checkpoint 2026-07-30T03:20:59.395931Z

- Branch: `feat/post-merge-state-transition`
- Commit: `39987cefa72fbf1cc7ac8035701a50c8a7187dd4`
- Commit subject: test(cli): cover controlled post-merge write entrypoint
- Working tree: **clean**
- Test evidence: `66 passed`
- Next action: Prepare PR #23

<!-- CYBERCORE:WORKLOG-CHECKPOINT:9276592d0fa4dabfc1283b8d49de1b9877155cc0fc28b7f8a67183483d8bdaf8 -->
## Checkpoint 2026-07-30T05:15:03.966351Z

- Branch: `feat/remote-aware-repository-identity`
- Commit: `3a2daae9382ec56f5953ca79bfd1e9dd3cee4fe6`
- Commit subject: test(memory): cover remote identity and marker migration
- Working tree: **clean**
- Test evidence: `78 passed`
- Next action: Prepare WB-0020 pull request

<!-- CYBERCORE:WORKLOG-CHECKPOINT:82313961d6580f4149a6f724b72db06c7b1824b775e166dfa7fa838d36c81e1d -->
## Checkpoint 2026-07-30T06:09:08.276960Z

- Branch: `feat/repository-identity-diagnostics`
- Commit: `8e070d97a3a2fe21fd80bff5d2a201aab7d4867e`
- Commit subject: fix(identity): normalize host in safe origin output
- Working tree: **clean**
- Test evidence: `86 passed`
- Next action: Prepare WB-0021 pull request

<!-- CYBERCORE:WORKLOG-CHECKPOINT:ea971e23b56216f3331cdd63ac7875f09ed048ef980fa36e24f28c4a7f3504f7 -->
## Checkpoint 2026-07-30T07:12:08.651626Z

- Branch: `feat/repository-identity-policy`
- Commit: `9c850b6b22e99e28dbc6d761a7b8c675164e3c59`
- Commit subject: test(policy): cover workflow identity enforcement
- Working tree: **clean**
- Test evidence: `98 passed`
- Next action: Prepare WB-0022 pull request

<!-- CYBERCORE:WORKLOG-CHECKPOINT:ef06edd8722f5a167644d6c0eb284d33d958307d838002368c414b533a4c6b6b -->
## Checkpoint 2026-07-30T11:17:14.969374Z

- Branch: `feat/context-disclosure-policy`
- Commit: `5defceda6da8c2385ec2546906c4ca128b062d3c`
- Commit subject: docs(project): activate WB-0024 disclosure policy
- Working tree: **clean**
- Test evidence: `109 passed`
- Next action: Define the Operation Context Disclosure Policy contract.

<!-- CYBERCORE:WORKLOG-CHECKPOINT:510ac86821dc43380543fa9e3947774f200e61e0fa65ed2a6ceac95a305d669e -->
## Checkpoint 2026-07-30T19:51:00Z

- Branch: `feat/context-disclosure-policy`
- Commit: `4ffa60b6727cd00797a210f191ec40ae7973f831`
- Commit subject: fix(disclosure): sanitize checkpoint memory persistence
- Working tree: **clean**
- Test evidence: `201 passed`
- Next action: Review PR #29 and verify security checks before merge.

<!-- CYBERCORE:WORKLOG-CHECKPOINT:b53aa6e7859062c86482a19b2bf7288c333218fb22d955d25bdeff937619965a -->
## Checkpoint 2026-07-30T20:32:49.897252Z

- Branch: `feat/security-verification-pipeline`
- Commit: `27304c5190d13530a9e5fb06322bcbf37e91e75a`
- Commit subject: docs(project): activate WB-0025 security verification pipeline
- Working tree: **clean**
- Test evidence: `201 passed`
- Next action: Define the CI matrix and implement the first GitHub Actions verification workflow.

<!-- CYBERCORE:WORKLOG-CHECKPOINT:e3315217405865351d116ddbdc2d9a5a4f01e903893de145aefbd8875bd7e12e -->
## Checkpoint 2026-07-30T21:03:52.696599Z

- Branch: `feat/security-verification-pipeline`
- Commit: `a5c080f6b990b65bb54b0006cefa9a8701df8540`
- Commit subject: docs(project): mark WB-0025 CI foundation implemented
- Working tree: **clean**
- Test evidence: `214 passed`
- Next action: Open a draft PR and observe the first GitHub Actions CI run.

<!-- CYBERCORE:WORKLOG-CHECKPOINT:b6455e47afbc6860710121bdbb1467dc40d2bb3d8c91a672fe9cd20336ca341a -->
## Checkpoint 2026-07-31T03:34:00Z

- Branch: `feat/security-verification-pipeline`
- Commit: `18bec34f76e7915fa02301ee345dece0ac575ba5`
- Commit subject: docs(project): record PR 30 hosted CI state
- Working tree: **clean**
- Test evidence: `214 passed; GitHub Actions run 30588331452: 6/6 jobs passed`
- Next action: Review draft PR #30 and confirm the CI foundation before the ready-for-review transition.

<!-- CYBERCORE:WORKLOG-CHECKPOINT:566cde4bd0011a34fd4e38ade8c054c874b10dcca06367c9738de2b0f3bf8203 -->
## Checkpoint 2026-08-02T11:49:03.307596Z

- Branch: `feat/security-verification-codeql`
- Commit: `732bd4dd1e5d248dc0a1ecc7cacac7dbe049eb3d`
- Commit subject: docs(project): activate WB-0025 CodeQL and merge gates
- Working tree: **clean**
- Test evidence: `214 passed; PR #30 merged as dbd61e9094d2b45ce11468d12b3700c66979cd0b; GitHub Actions run 30602280063: 6/6 jobs passed`
- Next action: Define the CodeQL workflow contract and required merge-gate checks without changing repository settings.

<!-- CYBERCORE:WORKLOG-CHECKPOINT:217b222ca17723d04c0b6e70ebd9cfc90afdc01ba9a8732f9c47fa2874ef349e -->
## Checkpoint 2026-08-02T13:14:33.717174Z

- Branch: `feat/security-verification-codeql`
- Commit: `458363e46b87902ff8a75cae8cea3d651e4c2ec2`
- Commit subject: docs(project): mark WB-0025 CodeQL slice implemented
- Working tree: **clean**
- Test evidence: `Ruff passed; Pyright 0 errors; pytest 218 passed; compileall passed; build passed; scripts/verify.sh passed; git diff --check passed; workflow audit passed`
- Next action: Open a draft PR and observe the first hosted CodeQL run; do not change repository settings before explicit human approval.

<!-- CYBERCORE:WORKLOG-CHECKPOINT:1f9ddcf958ceefe5b3b11f0b7289a69cc4f518bbfe6ee8a2170f37d8de66a849 -->
## Checkpoint 2026-08-02T13:28:26.446552Z

- Branch: `feat/security-verification-codeql`
- Commit: `1226605fdea6fdec9c30fb9a9c22f4e347414304`
- Commit subject: docs(project): align WB-0025 CodeQL verification state
- Working tree: **clean**
- Test evidence: `pytest 218 passed; git diff --check passed`
- Next action: Open a draft PR and observe the first hosted CodeQL run; do not change repository settings before explicit human approval.

<!-- CYBERCORE:WORKLOG-CHECKPOINT:57437a493ae5230754384e34abb1e68eaf05619f1e4685fcc4f88e59ca239eff -->
## Checkpoint 2026-08-03T03:26:41.606453Z

- Branch: `feat/main-branch-protection-enforcement`
- Commit: `bd635ca56bd2cb7ce0b221c03e9664b128095d25`
- Commit subject: ci(security): add CodeQL analysis and merge-gate contract (#31)
- Working tree: **dirty**
- Test evidence: `git diff --check passed; PYTHON=.venv/bin/python scripts/verify.sh passed: Ruff passed, Ruff format check passed, Pyright 0 errors, pytest 218 passed in 60.45s, compileall passed, build passed; GitHub Actions run 30774683751 passed; CodeQL run 30774683774 passed`
- Next action: Superseded by WB-0026 active main protection verification for PR #32.

## 2026-08-03 — WB-0026 post-merge closeout

### Completed

- Confirmed PR #32 was independently approved by `nulleimy`.
- Confirmed PR #32 was merged into protected `main`.
- Recorded final PR head
  `bb14c930dd4404c665dc8faec8a3cd89ce812df4`.
- Recorded merge commit
  `00b408dd9439caa7e6c660737d1123d0eaa1c12f`.
- Recorded successful CI run `30827098051`.
- Recorded successful CodeQL run `30827098042`.
- Verified the merged pull request through the CyberCore post-merge command.
- Wrote the canonical transition closing `WB-0026`.
- Activated planned successor `WB-0027 — Visual Documentation and Learn Capture
  v0.1`.
- Preserved historical generated checkpoints as immutable audit records.

### Current state

- Closeout branch: `docs/close-wb-0026`.
- Successor implementation branch:
  `feat/visual-documentation-learn-capture`.
- WB-0027 runtime implementation: planned, not started.
- No GitHub settings, secrets, rulesets or production systems were changed by
  this closeout update.
- This closeout record was prepared before its own commit and push.

## 2026-08-14 — WB-0027 local implementation and verification

- Added version-controlled Mermaid sources and rendered SVG documentation for
  the evidence lifecycle, Work Block lifecycle, security merge gate,
  architecture overview, and public/private overlay.
- Added a local, keyboard-accessible Learn evidence-lifecycle demo with
  deterministic replay and reduced-motion support.
- Captured and inspected 1280x720 WebM, MP4, GIF, and poster assets.
- Verified `git diff --check`, the visual documentation contract, and the full
  Python suite: Ruff, format check, Pyright, 220 pytest tests, compileall, and
  package build.
- No GitHub settings, secrets, Cloudflare resources, or production systems were
  changed. The change set was fully verified before commit and has not been
  proposed for review.

<!-- CYBERCORE:WORKLOG-CHECKPOINT:0b5e2c1c58d929e500581e0bf6bc0c4843cb8a64ef77acd410dce392dc7cd824 -->
## Checkpoint 2026-08-14T14:06:26.325311Z

- Branch: `feat/visual-documentation-learn-capture`
- Commit: `643ed6d979ca3846ff067f2e826f954cf8ceea34`
- Commit subject: Merge pull request #33 from cyberDJs/docs/close-wb-0026
- Working tree: **dirty**
- Test evidence: `git diff --check passed; PYTHON=.venv/bin/python scripts/verify.sh passed: Ruff passed, Ruff format check passed, Pyright 0 errors, pytest 220 passed, compileall passed, build passed; scripts/render_visual_docs.sh passed; scripts/capture_learn_demo.sh passed; scripts/verify_visual_docs.sh passed`
- Next action: Review the uncommitted WB-0027 visual documentation and Learn capture change set; do not commit, push, or open a pull request without explicit human approval.
