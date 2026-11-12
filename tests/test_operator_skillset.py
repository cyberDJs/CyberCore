from pathlib import Path

import yaml


CONTRACT = Path(__file__).resolve().parents[1] / "configs/autonomy/cybercore-skillset.yaml"
SELECTED = {
    "caser",
    "cyberdjs-github-workflow",
    "github-repo-auditor",
    "systematic-debugging-and-root-cause-engineer",
    "adversary-lens",
    "release-change-manager",
    "cyberdjs-portfolio-index",
}


def _contract() -> dict:
    result = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    assert isinstance(result, dict)
    return result


def test_skillset_contains_exactly_the_approved_seven_real_skills() -> None:
    spec = _contract()["spec"]
    assert spec["mode"] == "strict_skillset"
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


def test_writer_consumes_drift_and_parallel_ownership_before_writes() -> None:
    nodes = _contract()["spec"]["nodes"]
    writer = nodes["github"]
    assert "portfolio" in writer["needs"]
    assert {"canonical_lane", "parallel_work", "drift_status"} <= set(writer["inputs"])


def test_security_waits_for_debug_regression_evidence() -> None:
    nodes = _contract()["spec"]["nodes"]
    assert "debug" in nodes["security"]["needs"]
    assert "regression_evidence" in nodes["security"]["inputs"]


def test_internal_inputs_are_produced_by_declared_ancestors() -> None:
    nodes = _contract()["spec"]["nodes"]
    external_inputs = {
        "project_scope",
        "live_repo_refs",
        "authorization_scope",
        "security_boundaries",
    }

    def ancestors(name: str) -> set[str]:
        result: set[str] = set()
        for dependency in nodes[name].get("needs", []):
            result.add(dependency)
            result.update(ancestors(dependency))
        return result

    for name, node in nodes.items():
        available = set(external_inputs)
        for dependency in ancestors(name):
            available.update(nodes[dependency].get("outputs", []))
        missing = set(node.get("inputs", [])) - available
        assert not missing, f"{name} has unproduced inputs: {sorted(missing)}"


def test_release_consumes_security_residual_risk() -> None:
    release_inputs = set(_contract()["spec"]["nodes"]["release"]["inputs"])
    assert {"security_verdict", "residual_risk"} <= release_inputs


def test_protected_actions_are_explicitly_separated() -> None:
    gates = _contract()["spec"]["gates"]
    assert gates["canonical_merge"]["approval"] == "explicit_identity_bound_user_approval"
    assert "no_parallel_canonical_writer" in gates["canonical_merge"]["require"]
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
