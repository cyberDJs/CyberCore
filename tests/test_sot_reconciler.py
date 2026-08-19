from __future__ import annotations

from copy import deepcopy

from cybercore.orchestration.sot import build_sot_reconciler


def _invoke(sources, remediations=None):
    graph = build_sot_reconciler()
    return graph.invoke({"sources": sources, "remediations": remediations or []})


def test_matching_state_is_current():
    result = _invoke(
        [
            {
                "source_id": "github-main",
                "authority": "CANONICAL",
                "facts": {"pr:38:state": "merged"},
            },
            {
                "source_id": "project-state",
                "authority": "WORKING",
                "facts": {"pr:38:state": "merged"},
            },
        ]
    )

    assert result["status"] == "CURRENT"
    assert result["findings"] == []
    assert result["recommendation"] == "NO_ACTION"


def test_drift_proposes_remediation_when_none_exists():
    result = _invoke(
        [
            {
                "source_id": "github-main",
                "authority": "CANONICAL",
                "facts": {"pr:38:state": "merged"},
            },
            {
                "source_id": "PROJECT_STATE.md",
                "authority": "WORKING",
                "facts": {"pr:38:state": "open"},
            },
        ]
    )

    assert result["status"] == "DRIFT"
    assert result["findings"][0]["key"] == "pr:38:state"
    assert result["remediation_disposition"] == "PROPOSE"
    assert result["recommendation"] == "PROPOSE_REMEDIATION"


def test_existing_pr_remediation_prevents_duplicate_proposal():
    result = _invoke(
        [
            {
                "source_id": "github-pr-37",
                "authority": "CANONICAL",
                "facts": {"pr:37:state": "merged"},
            },
            {
                "source_id": "PROJECT_STATE.md@6b74a56",
                "authority": "WORKING",
                "facts": {"pr:37:state": "open"},
            },
        ],
        [
            {
                "id": "PR#38",
                "state": "OPEN",
                "target_keys": ["pr:37:state"],
            }
        ],
    )

    assert result["status"] == "DRIFT"
    assert result["remediation_disposition"] == "EXISTING"
    assert result["remediation_ids"] == ["PR#38"]
    assert result["recommendation"] == "OBSERVE_EXISTING_REMEDIATION"


def test_conflicting_canonical_sources_fail_closed():
    result = _invoke(
        [
            {
                "source_id": "canonical-a",
                "authority": "CANONICAL",
                "facts": {"release:state": "ready"},
            },
            {
                "source_id": "canonical-b",
                "authority": "CANONICAL",
                "facts": {"release:state": "blocked"},
            },
        ]
    )

    assert result["status"] == "CONFLICT"
    assert result["findings"][0]["kind"] == "CONFLICT"
    assert result["recommendation"] == "ESCALATE_AUTHORITY_CONFLICT"


def test_missing_canonical_source_is_unknown():
    result = _invoke(
        [
            {
                "source_id": "drive-working-copy",
                "authority": "WORKING",
                "facts": {"release:state": "ready"},
            }
        ]
    )

    assert result["status"] == "UNKNOWN"
    assert result["recommendation"] == "REQUEST_MORE_EVIDENCE"


def test_reconciliation_does_not_mutate_inputs():
    sources = [
        {
            "source_id": "github-main",
            "authority": "CANONICAL",
            "facts": {"pr:38:state": "merged"},
        },
        {
            "source_id": "project-state",
            "authority": "WORKING",
            "facts": {"pr:38:state": "open"},
        },
    ]
    original = deepcopy(sources)

    _invoke(sources)

    assert sources == original
