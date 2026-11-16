"""Conservative, pure bridge from CI snapshot structure to operator reports.

A consistent GitHub workflow/job snapshot is NOT an authenticated attestation.
Never label it VERIFIED, PASS, or READY_FOR_MERGE. External provider acquisition,
authorization, sanitization, storage and delivery are outside this module.
"""

from __future__ import annotations

import re

from cybercore.caser41_github_snapshot import reconcile_github_snapshot
from cybercore.operator_reporting import OperatorUpdate

_SHA = re.compile(r"[0-9a-f]{40}", re.ASCII)

_BLOCKED_REASONS = frozenset(
    {
        "INVALID_SHA",
        "HEAD_DRIFT",
        "INVALID_COLLECTION",
        "INVALID_WORKFLOW",
        "INVALID_WORKFLOW_STATE",
        "DUPLICATE_RUN_ID",
        "DUPLICATE_WORKFLOW",
        "WORKFLOW_NOT_SUCCESSFUL",
        "MISSING_WORKFLOW",
        "REUSED_WORKFLOW_ID",
        "INVALID_JOB",
        "INVALID_JOB_STATE",
        "DUPLICATE_JOB",
        "FOREIGN_RUN_JOB",
        "JOB_NOT_SUCCESSFUL",
        "MISSING_JOB",
    }
)


def ci_snapshot_operator_update(
    *,
    pr_number: int,
    expected_sha: str,
    provider_head_sha: str,
    workflows: object,
    jobs: object,
    changed: bool,
) -> OperatorUpdate:
    """Reconcile CI observations inside PR/SHA-bound report construction.

    Caller must acquire complete, authenticated records for *this* PR and
    verify stable HEAD before/after acquisition. This function cannot verify
    provider provenance or pagination, and never emits a verified CI PASS.
    """
    if type(pr_number) is not int or not 1 <= pr_number <= 1_000_000_000:
        raise ValueError("INVALID_PR_NUMBER")
    if type(expected_sha) is not str or _SHA.fullmatch(expected_sha) is None:
        raise ValueError("INVALID_SHA")
    if type(changed) is not bool:
        raise ValueError("INVALID_CHANGED_FLAG")
    # Do not accept a reusable Reconciliation detached from its input identity.
    # Run the structural reconciliation within the expected HEAD context.
    snapshot = reconcile_github_snapshot(
        expected_sha=expected_sha,
        provider_head_sha=provider_head_sha,
        workflows=workflows,
        jobs=jobs,
    )
    if snapshot.status == "CONSISTENT_ONLY":
        if snapshot.reason != "PROVIDER_ORIGIN_AND_PAGINATION_UNVERIFIED":
            raise ValueError("INVALID_RECONCILIATION")
        state = "UNKNOWN"
        event_kind = "critical_evidence_missing"
        what = "CI snapshot je strukturálně konzistentní; původ a úplnost nejsou ověřené"
        why = "Poskytnutá data sama neprokazují původ, stránkování ani aktuálnost"
        impact = "Nelze potvrdit PASS ani připravenost k merge"
        action = "Ověřit autentizovaný původ, úplné joby a aktuální HEAD"
    elif snapshot.status == "BLOCKED":
        if type(snapshot.reason) is not str or snapshot.reason not in _BLOCKED_REASONS:
            # Do not reflect arbitrary/untrusted reason text into user-facing reports.
            raise ValueError("INVALID_RECONCILIATION")
        state = "BLOCKED"
        event_kind = "source_drift" if snapshot.reason == "HEAD_DRIFT" else "checks_failed"
        what = "GitHub CI snapshot nesplnil požadovanou strukturální kontrolu"
        why = "Kontrolní kód: " + snapshot.reason
        impact = "Nelze označit release za bezpečně připravený"
        action = "Ověřit důkazy a opravit příčinu; při driftu znovu naplánovat"
    else:
        raise ValueError("INVALID_RECONCILIATION")
    return OperatorUpdate(
        event_kind=event_kind,
        subject=f"CyberCore PR #{pr_number}",
        sha=expected_sha,
        state=state,
        what=what,
        why=why,
        impact=impact,
        next_action=action,
        evidence_url=f"https://github.com/cyberDJs/CyberCore/pull/{pr_number}",
        approval_required=False,
        changed=changed,
    )
