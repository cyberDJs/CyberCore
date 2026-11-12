from pathlib import Path

import yaml


CONTRACT = (
    Path(__file__).resolve().parents[1] / "configs/autonomy/cybercore-skillset.yaml"
)
SELECTED = {
    "caser",
    "caser-sourcer",
    "ai-agent-designer",
    "capability-composer",
    "capability-observability",
    "ai-evaluation-red-team",
    "release-change-manager",
}


def _contract() -> dict:
    result = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    assert isinstance(result, dict)
    return result


def test_skillset_contains_exactly_the_approved_seven_real_skills() -> None:
    spec = _contract()["spec"]
    assert spec["mode"] == "skillset"
    assert spec["selection_source"] == "capability-router"
    assert spec["execution_status"] == "proposal_only"
    capabilities = [node["capability"] for node in spec["nodes"].values()]
    assert len(capabilities) == 7
    assert set(capabilities) == SELECTED


def test_dependencies_are_valid_and_acyclic() -> None:
    nodes = _contract()["spec"]["nodes"]
    visited: set[str] = set()
    active: set[str] = set()

    def visit(name: str) -> None:
        assert name in nodes, "unknown dependency"
        assert name not in active, "skillset dependency cycle"
        if name in visited:
            return
        active.add(name)
        for dependency in nodes[name].get("needs", []):
            visit(dependency)
        active.remove(name)
        visited.add(name)

    for name in nodes:
        visit(name)
    assert len(visited) == 7


def test_protected_actions_are_explicitly_separated() -> None:
    gates = _contract()["spec"]["gates"]
    assert gates["canonical_merge"]["approval"] == "explicit_identity_bound_user_approval"
    assert gates["production_mutation"]["default"] == "denied"
    assert gates["secrets"]["default"] == "denied"
    assert "secret_read" in gates["secrets"]["before"]
    assert gates["production_mutation"]["before"] != gates["staging_mutation"]["before"]


def test_missing_source_and_drift_are_never_promoted_to_success() -> None:
    failures = _contract()["spec"]["failure"]
    assert failures["on_drift"] == "REPLAN_REQUIRED"
    assert failures["on_unverified_source"] == "BLOCKED"
    assert failures["on_unavailable_check"] == "UNKNOWN_not_PASS"
    assert failures["max_repair_attempts_per_root_cause"] <= 3
