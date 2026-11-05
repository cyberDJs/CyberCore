# CASER v4.1 — GitHub workflow/job snapshot reconciliation

Tracks #141, after candidate preflight #142.

A bounded, side-effect-free reconciliation of the **real** GitHub Actions job
names observed in CyberCore: workflow CI has quality, package and tests on
Python 3.11–3.14; workflow CodeQL has lowercase job `codeql`; workflow
Action Kernel real CyberHIVE contract has `real-hive-contract`.

The expected PR head and `provider_head_sha` must match exactly. Run IDs
are bound to their workflow and job IDs; missing, duplicated, failed, pending,
foreign and inconsistent observations block. We reuse the existing
`caser41_ci_evidence.evaluate_ci_evidence` for the seven mandatory quality
and CodeQL checks, rather than duplicate their rules. CyberHIVE is a
separate mandatory integration check within this snapshot.

**Important trust boundary:** The actual GitHub connector used in the
initial exploration returns workflow runs filtered by commit and job lists
by run ID, but job lists cover only the latest attempt's **first page**.
This module does **not** call GitHub and cannot authenticate those snapshots,
prove job pagination complete, infer provider refresh, or validate GitHub
branch protection settings. The caller-supplied `provider_head_sha` is not
independent evidence. A structurally consistent result is
`CONSISTENT_ONLY / PROVIDER_ORIGIN_AND_PAGINATION_UNVERIFIED`,
**never** VERIFIED, merge/deploy authorization, or persisted audit evidence.

Trusted integration must:
1. bind to the authenticated provider repository, current PR head and
   provider workflow run IDs, without fabricating missing values;
2. fetch all relevant jobs and check pagination, latest attempts, and run
   supersession; ensure provider data does not drift between reads;
3. independently verify branch protection, review gates and actual effects;
4. use the existing ActionKernel audit/checkpoint with separately retained
   external authority if persistence is explicitly approved.

## Tests, rollback, deployment

Synthetic regressions cover missing and incomplete jobs, wrong SHA,
incorrect CodeQL display label, cancelled/failed outcomes, duplicate run and
job IDs, foreign run jobs, malformed objects and non-authoritative verdicts.
Read-only opt-in module. No API call, retention, storage, new dependencies,
credentials, installed CASER skill or production change. Rollback: stop
importing the module. Only promote after exact-head CI/CodeQL/CyberHIVE and
independent review. The #141 trusted ingestion/anchor deployment remains
BLOCKED without independent source and owner proof.
