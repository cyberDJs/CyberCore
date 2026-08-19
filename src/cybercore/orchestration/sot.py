from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from cybercore.orchestration.contracts import (
    Finding,
    Recommendation,
    ReconciliationState,
    Scalar,
)


def _resolve_authority(state: ReconciliationState) -> dict[str, object]:
    canonical_sources = [
        source for source in state.get("sources", []) if source["authority"] == "CANONICAL"
    ]
    if not canonical_sources:
        return {
            "canonical_facts": {},
            "status": "UNKNOWN",
            "findings": [
                {
                    "kind": "UNKNOWN",
                    "key": "*",
                    "sources": [],
                }
            ],
        }

    canonical_facts: dict[str, Scalar] = {}
    canonical_owner: dict[str, str] = {}
    conflicts: list[Finding] = []

    for source in canonical_sources:
        for key, value in sorted(source["facts"].items()):
            if key not in canonical_facts:
                canonical_facts[key] = value
                canonical_owner[key] = source["source_id"]
                continue
            if canonical_facts[key] != value:
                conflicts.append(
                    {
                        "kind": "CONFLICT",
                        "key": key,
                        "expected": canonical_facts[key],
                        "observed": value,
                        "sources": [canonical_owner[key], source["source_id"]],
                    }
                )

    if conflicts:
        return {
            "canonical_facts": canonical_facts,
            "status": "CONFLICT",
            "findings": conflicts,
        }

    return {
        "canonical_facts": canonical_facts,
        "status": "CURRENT",
        "findings": [],
    }


def _compare_observations(state: ReconciliationState) -> dict[str, object]:
    if state.get("status") != "CURRENT":
        return {}

    canonical_facts = state.get("canonical_facts", {})
    drift: list[Finding] = []
    for source in state.get("sources", []):
        if source["authority"] == "CANONICAL":
            continue
        for key, observed in sorted(source["facts"].items()):
            if key not in canonical_facts:
                continue
            expected = canonical_facts[key]
            if observed != expected:
                drift.append(
                    {
                        "kind": "DRIFT",
                        "key": key,
                        "expected": expected,
                        "observed": observed,
                        "sources": [source["source_id"]],
                    }
                )

    return {
        "status": "DRIFT" if drift else "CURRENT",
        "findings": drift,
    }


def _detect_existing_remediation(state: ReconciliationState) -> dict[str, object]:
    if state.get("status") != "DRIFT":
        return {
            "remediation_disposition": "NONE",
            "remediation_ids": [],
        }

    drift_keys = {
        finding["key"] for finding in state.get("findings", []) if finding["kind"] == "DRIFT"
    }
    covered_keys: set[str] = set()
    remediation_ids: list[str] = []

    for remediation in state.get("remediations", []):
        if remediation["state"] != "OPEN":
            continue
        target_keys = set(remediation["target_keys"])
        if drift_keys.intersection(target_keys):
            covered_keys.update(target_keys)
            remediation_ids.append(remediation["id"])

    if drift_keys and drift_keys.issubset(covered_keys):
        return {
            "remediation_disposition": "EXISTING",
            "remediation_ids": sorted(remediation_ids),
        }

    return {
        "remediation_disposition": "PROPOSE",
        "remediation_ids": sorted(remediation_ids),
    }


def _finalize(state: ReconciliationState) -> dict[str, object]:
    status = state.get("status", "UNKNOWN")
    if status == "CURRENT":
        recommendation: Recommendation = "NO_ACTION"
    elif status == "CONFLICT":
        recommendation = "ESCALATE_AUTHORITY_CONFLICT"
    elif status == "UNKNOWN":
        recommendation = "REQUEST_MORE_EVIDENCE"
    elif state.get("remediation_disposition") == "EXISTING":
        recommendation = "OBSERVE_EXISTING_REMEDIATION"
    else:
        recommendation = "PROPOSE_REMEDIATION"
    return {"recommendation": recommendation}


def build_sot_reconciler():
    """Build the deterministic, read-only LG-0001 reconciliation graph."""

    builder = StateGraph(ReconciliationState)
    builder.add_node("resolve_authority", _resolve_authority)
    builder.add_node("compare_observations", _compare_observations)
    builder.add_node("detect_existing_remediation", _detect_existing_remediation)
    builder.add_node("finalize", _finalize)
    builder.add_edge(START, "resolve_authority")
    builder.add_edge("resolve_authority", "compare_observations")
    builder.add_edge("compare_observations", "detect_existing_remediation")
    builder.add_edge("detect_existing_remediation", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile()
