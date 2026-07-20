from pathlib import Path

import pytest

from cybercore.registry import Registry, RegistryError


def _write_inventory(repo: Path) -> None:
    path = repo / "knowledge" / "registry" / "inventory.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        """
assets:
  - id: ASSET-001
    kind: asset
    subtype: vps
    name: Main VPS
    status: active
    owner: CyberCore
    relationships:
      - type: hosts
        target: SERVICE-001
services:
  - id: SERVICE-001
    kind: service
    subtype: nextcloud
    name: Cloud
    status: degraded
    owner: CyberCore
unknowns:
  - id: UNKNOWN-001
    question: What is the backup state?
    priority: high
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_registry_queries_and_relationships(tmp_path: Path) -> None:
    _write_inventory(tmp_path)
    registry = Registry.load(tmp_path)

    assert len(registry) == 2
    assert registry.require("SERVICE-001").name == "Cloud"
    assert [record.id for record in registry.records("assets")] == ["ASSET-001"]
    assert [record.id for record in registry.find(subtype="nextcloud")] == ["SERVICE-001"]
    assert [record.id for record in registry.search("main vps")] == ["ASSET-001"]
    assert registry.relationships("SERVICE-001") == (
        {"from": "ASSET-001", "type": "hosts", "to": "SERVICE-001"},
    )
    assert registry.unknowns("high")[0]["id"] == "UNKNOWN-001"


def test_registry_rejects_duplicate_ids(tmp_path: Path) -> None:
    path = tmp_path / "knowledge" / "registry" / "inventory.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "assets:\n  - {id: DUP-001}\nservices:\n  - {id: DUP-001}\n",
        encoding="utf-8",
    )

    with pytest.raises(RegistryError, match="Duplicate registry id"):
        Registry.load(tmp_path)
