from __future__ import annotations

from cybercore.orchestration.trusted_sot import build_trusted_sot_reconciler


def _bindings():
    return [
        {
            "binding_id": "github-main-files",
            "provider": "GITHUB",
            "authority": "CANONICAL",
            "match": {
                "repository": "cyberDJs/CyberCore",
                "ref": "main",
                "resource_kind": "file",
            },
        },
        {
            "binding_id": "drive-caser-e-working",
            "provider": "GOOGLE_DRIVE",
            "authority": "WORKING",
            "match": {"ancestor_id": "caser-e-working"},
        },
    ]


def _observations():
    return [
        {
            "source_id": "github-project-state",
            "provider": "GITHUB",
            "locator": {
                "repository": "cyberDJs/CyberCore",
                "ref": "main",
                "resource_kind": "file",
                "path": "PROJECT_STATE.md",
            },
            "facts": {"pr:40:state": "merged"},
        },
        {
            "source_id": "drive-working-audit",
            "provider": "GOOGLE_DRIVE",
            "locator": {
                "file_id": "audit-file",
                "ancestor_id": "caser-e-working",
                "resource_kind": "file",
                "mime_type": "text/plain",
            },
            "facts": {"pr:40:state": "open"},
        },
    ]


def test_bound_provider_observations_flow_into_lg0001():
    graph = build_trusted_sot_reconciler()
    result = graph.invoke(
        {"observations": _observations(), "bindings": _bindings(), "remediations": []}
    )

    assert result["ingest_status"] == "BOUND"
    assert result["status"] == "DRIFT"
    assert result["recommendation"] == "PROPOSE_REMEDIATION"
    assert [item["binding_id"] for item in result["provenance"]] == [
        "github-main-files",
        "drive-caser-e-working",
    ]


def test_existing_remediation_is_reused_after_trusted_ingest():
    graph = build_trusted_sot_reconciler()
    result = graph.invoke(
        {
            "observations": _observations(),
            "bindings": _bindings(),
            "remediations": [{"id": "PR#39", "state": "OPEN", "target_keys": ["pr:40:state"]}],
        }
    )

    assert result["status"] == "DRIFT"
    assert result["remediation_disposition"] == "EXISTING"
    assert result["recommendation"] == "OBSERVE_EXISTING_REMEDIATION"


def test_unbound_observation_routes_to_unknown_without_reconciliation():
    observations = _observations()
    observations[1]["locator"]["ancestor_id"] = "untrusted-folder"
    graph = build_trusted_sot_reconciler()
    result = graph.invoke(
        {"observations": observations, "bindings": _bindings(), "remediations": []}
    )

    assert result["ingest_status"] == "UNKNOWN"
    assert result["status"] == "UNKNOWN"
    assert result["recommendation"] == "REQUEST_MORE_EVIDENCE"
    assert result["binding_issues"][0]["reason"] == "UNBOUND"


def test_ambiguous_authority_binding_routes_to_unknown():
    bindings = _bindings()
    bindings.append(
        {
            "binding_id": "github-duplicate-rule",
            "provider": "GITHUB",
            "authority": "CANONICAL",
            "match": {
                "repository": "cyberDJs/CyberCore",
                "ref": "main",
                "resource_kind": "file",
            },
        }
    )
    graph = build_trusted_sot_reconciler()
    result = graph.invoke(
        {"observations": _observations(), "bindings": bindings, "remediations": []}
    )

    assert result["ingest_status"] == "UNKNOWN"
    assert result["status"] == "UNKNOWN"
    assert result["recommendation"] == "REQUEST_MORE_EVIDENCE"
