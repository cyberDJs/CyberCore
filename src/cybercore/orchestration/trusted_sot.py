from __future__ import annotations

from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from cybercore.orchestration.contracts import (
    Finding,
    Recommendation,
    Remediation,
    RemediationDisposition,
    SOTStatus,
    SourceSnapshot,
)
from cybercore.orchestration.source_binding import (
    BindingIssue,
    BindingStatus,
    ProviderObservation,
    SourceProvenance,
    TrustedSourceBinding,
    bind_provider_observations,
)
from cybercore.orchestration.sot import build_sot_reconciler


class TrustedReconciliationState(TypedDict):
    observations: list[ProviderObservation]
    bindings: list[TrustedSourceBinding]
    remediations: list[Remediation]
    ingest_status: NotRequired[BindingStatus]
    sources: NotRequired[list[SourceSnapshot]]
    provenance: NotRequired[list[SourceProvenance]]
    binding_issues: NotRequired[list[BindingIssue]]
    canonical_facts: NotRequired[dict[str, str | int | float | bool | None]]
    findings: NotRequired[list[Finding]]
    status: NotRequired[SOTStatus]
    remediation_disposition: NotRequired[RemediationDisposition]
    remediation_ids: NotRequired[list[str]]
    recommendation: NotRequired[Recommendation]


def _bind_authority(state: TrustedReconciliationState) -> dict[str, object]:
    result = bind_provider_observations(
        state.get("observations", []),
        state.get("bindings", []),
    )
    return {
        "ingest_status": result["status"],
        "sources": result["sources"],
        "provenance": result["provenance"],
        "binding_issues": result["binding_issues"],
    }


def _route_after_binding(state: TrustedReconciliationState) -> str:
    return "reconcile" if state.get("ingest_status") == "BOUND" else "fail_closed"


def _reconcile(state: TrustedReconciliationState) -> dict[str, object]:
    graph = build_sot_reconciler()
    result = graph.invoke(
        {
            "sources": state.get("sources", []),
            "remediations": state.get("remediations", []),
        }
    )
    return {
        "canonical_facts": result.get("canonical_facts", {}),
        "findings": result.get("findings", []),
        "status": result.get("status", "UNKNOWN"),
        "remediation_disposition": result.get("remediation_disposition", "NONE"),
        "remediation_ids": result.get("remediation_ids", []),
        "recommendation": result.get("recommendation", "REQUEST_MORE_EVIDENCE"),
    }


def _fail_closed(state: TrustedReconciliationState) -> dict[str, object]:
    issue_sources = sorted(
        {
            issue["source_id"]
            for issue in state.get("binding_issues", [])
            if issue["source_id"] != "*"
        }
    )
    finding: Finding = {
        "kind": "UNKNOWN",
        "key": "authority-binding",
        "sources": issue_sources,
    }
    return {
        "canonical_facts": {},
        "findings": [finding],
        "status": "UNKNOWN",
        "remediation_disposition": "NONE",
        "remediation_ids": [],
        "recommendation": "REQUEST_MORE_EVIDENCE",
    }


def build_trusted_sot_reconciler():
    """Build LG-0002: trusted provider ingest followed by the LG-0001 reconciler."""

    builder = StateGraph(TrustedReconciliationState)
    builder.add_node("bind_authority", _bind_authority)
    builder.add_node("reconcile", _reconcile)
    builder.add_node("fail_closed", _fail_closed)
    builder.add_edge(START, "bind_authority")
    builder.add_conditional_edges(
        "bind_authority",
        _route_after_binding,
        {
            "reconcile": "reconcile",
            "fail_closed": "fail_closed",
        },
    )
    builder.add_edge("reconcile", END)
    builder.add_edge("fail_closed", END)
    return builder.compile()
