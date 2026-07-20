from pathlib import Path

import pytest

from cybercore.registry import Registry, RegistryError
from cybercore.registry_graph import RegistryGraph


def _write_inventory(repo: Path) -> None:
    path = repo / "knowledge" / "registry" / "inventory.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        """
assets:
  - id: ASSET-001
    kind: asset
    name: Host
    status: active
    owner: CyberCore
    relationships:
      - type: hosts
        target: SERVICE-001
services:
  - id: SERVICE-001
    kind: service
    name: API
    status: active
    owner: CyberCore
    relationships:
      - type: depends_on
        target: DATABASE-001
  - id: DATABASE-001
    kind: service
    subtype: database
    name: Database
    status: active
    owner: CyberCore
projects:
  - id: PROJECT-001
    kind: project
    name: Control plane
    status: active
    owner: CyberCore
    relationships:
      - type: uses
        target: SERVICE-001
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_graph_edges_neighbours_and_path(tmp_path: Path) -> None:
    _write_inventory(tmp_path)
    graph = RegistryGraph.load(Registry.load(tmp_path))

    assert len(graph) == 3
    assert [(edge.source, edge.relationship, edge.target) for edge in graph.outgoing("SERVICE-001")] == [
        ("SERVICE-001", "depends_on", "DATABASE-001")
    ]
    assert [record.id for record in graph.neighbours("SERVICE-001")] == [
        "DATABASE-001",
        "ASSET-001",
        "PROJECT-001",
    ]
    assert graph.shortest_path("PROJECT-001", "DATABASE-001") == (
        "PROJECT-001",
        "SERVICE-001",
        "DATABASE-001",
    )


def test_graph_dependencies_and_impact(tmp_path: Path) -> None:
    _write_inventory(tmp_path)
    graph = RegistryGraph.load(Registry.load(tmp_path))

    assert [record.id for record in graph.dependencies("SERVICE-001")] == ["DATABASE-001"]
    assert [record.id for record in graph.impact("DATABASE-001")] == [
        "SERVICE-001",
        "ASSET-001",
        "PROJECT-001",
    ]
    assert graph.shortest_path("ASSET-001", "PROJECT-001") == (
        "ASSET-001",
        "SERVICE-001",
        "PROJECT-001",
    )


def test_graph_rejects_missing_target(tmp_path: Path) -> None:
    path = tmp_path / "knowledge" / "registry" / "inventory.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "assets:\n  - id: ASSET-001\n    relationships:\n      - {type: hosts, target: MISSING-001}\n",
        encoding="utf-8",
    )

    with pytest.raises(RegistryError, match="Relationship target does not exist"):
        RegistryGraph.load(Registry.load(tmp_path))
