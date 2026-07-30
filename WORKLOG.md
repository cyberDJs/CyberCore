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
