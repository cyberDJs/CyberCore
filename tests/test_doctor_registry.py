from pathlib import Path

from cybercore.commands.doctor import _registry_checks
from cybercore.models import CheckState


def _write_inventory(repo: Path, *, broken_target: bool = False) -> None:
    path = repo / "knowledge" / "registry" / "inventory.yaml"
    path.parent.mkdir(parents=True)
    target = "MISSING-001" if broken_target else "ASSET-001"
    path.write_text(
        f"""
assets:
  - id: ASSET-001
    kind: asset
    name: Main VPS
    status: active
    owner: CyberCore
    classification: internal
    last_reviewed: 2026-07-20
    evidence:
      - type: test
services:
  - id: SERVICE-001
    kind: service
    name: Cloud
    status: degraded
    owner: CyberCore
    classification: internal
    last_reviewed: 2026-07-20
    relationships:
      - type: hosted_by
        target: {target}
    evidence:
      - type: test
unknowns:
  - id: UNKNOWN-001
    question: Is backup verified?
    priority: high
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_registry_checks_report_operational_warnings(tmp_path: Path) -> None:
    _write_inventory(tmp_path)

    results = {result.name: result for result in _registry_checks(tmp_path)}

    assert results["registry"].state is CheckState.OK
    assert results["registry-graph"].state is CheckState.OK
    assert results["knowledge"].state is CheckState.OK
    assert results["registry-unknowns"].state is CheckState.WARN
    assert results["registry-degraded"].state is CheckState.WARN
    assert "SERVICE-001" in results["registry-degraded"].detail


def test_registry_checks_fail_when_graph_target_is_missing(tmp_path: Path) -> None:
    _write_inventory(tmp_path, broken_target=True)

    results = {result.name: result for result in _registry_checks(tmp_path)}

    assert results["registry"].state is CheckState.OK
    assert results["registry-graph"].state is CheckState.ERROR
    assert "MISSING-001" in results["registry-graph"].detail
