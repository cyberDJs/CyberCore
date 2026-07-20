from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


class RegistryError(RuntimeError):
    """Raised when the file-backed registry cannot be loaded safely."""


@dataclass(frozen=True, slots=True)
class RegistryRecord:
    section: str
    data: dict[str, Any]

    @property
    def id(self) -> str:
        return str(self.data["id"])

    @property
    def kind(self) -> str:
        return str(self.data.get("kind", self.section.rstrip("s")))

    @property
    def name(self) -> str:
        return str(self.data.get("name", self.id))


class Registry:
    """Read-only query API over the versioned CyberCore registry."""

    ENTITY_SECTIONS = (
        "assets",
        "services",
        "domains",
        "repositories",
        "projects",
        "providers",
        "users",
        "agents",
    )

    def __init__(self, repo: Path, inventory_path: Path | None = None) -> None:
        self.repo = repo.resolve()
        self.inventory_path = inventory_path or self.repo / "knowledge" / "registry" / "inventory.yaml"
        self.document: dict[str, Any] = {}
        self._records: dict[str, RegistryRecord] = {}
        self._section_records: dict[str, tuple[RegistryRecord, ...]] = {}

    @classmethod
    def load(cls, repo: Path, inventory_path: Path | None = None) -> "Registry":
        registry = cls(repo, inventory_path=inventory_path)
        registry.reload()
        return registry

    def reload(self) -> None:
        if not self.inventory_path.is_file():
            raise RegistryError(f"Registry inventory not found: {self.inventory_path}")
        try:
            loaded = yaml.safe_load(self.inventory_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise RegistryError(f"Cannot load registry inventory: {exc}") from exc
        if not isinstance(loaded, dict):
            raise RegistryError("Registry inventory root must be an object")

        records: dict[str, RegistryRecord] = {}
        section_records: dict[str, tuple[RegistryRecord, ...]] = {}
        for section in self.ENTITY_SECTIONS:
            raw_records = loaded.get(section, [])
            if raw_records is None:
                raw_records = []
            if not isinstance(raw_records, list):
                raise RegistryError(f"Registry section {section!r} must be a list")
            parsed: list[RegistryRecord] = []
            for index, raw in enumerate(raw_records):
                if not isinstance(raw, dict):
                    raise RegistryError(f"Registry record {section}[{index}] must be an object")
                identifier = raw.get("id")
                if not isinstance(identifier, str) or not identifier:
                    raise RegistryError(f"Registry record {section}[{index}] has no valid id")
                if identifier in records:
                    raise RegistryError(f"Duplicate registry id: {identifier}")
                record = RegistryRecord(section=section, data=raw)
                records[identifier] = record
                parsed.append(record)
            section_records[section] = tuple(parsed)

        self.document = loaded
        self._records = records
        self._section_records = section_records

    def get(self, identifier: str) -> RegistryRecord | None:
        return self._records.get(identifier)

    def require(self, identifier: str) -> RegistryRecord:
        record = self.get(identifier)
        if record is None:
            raise RegistryError(f"Registry record not found: {identifier}")
        return record

    def records(self, section: str | None = None) -> tuple[RegistryRecord, ...]:
        if section is None:
            return tuple(self._records.values())
        if section not in self.ENTITY_SECTIONS:
            raise RegistryError(f"Unknown registry section: {section}")
        return self._section_records.get(section, ())

    def find(self, *, kind: str | None = None, subtype: str | None = None, status: str | None = None, owner: str | None = None) -> tuple[RegistryRecord, ...]:
        matches: list[RegistryRecord] = []
        for record in self._records.values():
            data = record.data
            if kind is not None and data.get("kind") != kind:
                continue
            if subtype is not None and data.get("subtype") != subtype:
                continue
            if status is not None and data.get("status") != status:
                continue
            if owner is not None and data.get("owner") != owner:
                continue
            matches.append(record)
        return tuple(matches)

    def search(self, query: str) -> tuple[RegistryRecord, ...]:
        needle = query.casefold().strip()
        if not needle:
            return ()
        return tuple(
            record
            for record in self._records.values()
            if needle in " ".join(
                str(record.data.get(field, ""))
                for field in ("id", "name", "kind", "subtype", "description", "provider")
            ).casefold()
        )

    def relationships(self, identifier: str, *, incoming: bool = True, outgoing: bool = True) -> tuple[dict[str, str], ...]:
        self.require(identifier)
        edges: list[dict[str, str]] = []
        if outgoing:
            for relationship in self.require(identifier).data.get("relationships", []):
                if isinstance(relationship, dict) and relationship.get("type") and relationship.get("target"):
                    edges.append({
                        "from": identifier,
                        "type": str(relationship["type"]),
                        "to": str(relationship["target"]),
                    })
        if incoming:
            for record in self._records.values():
                if record.id == identifier:
                    continue
                for relationship in record.data.get("relationships", []):
                    if isinstance(relationship, dict) and relationship.get("target") == identifier and relationship.get("type"):
                        edges.append({
                            "from": record.id,
                            "type": str(relationship["type"]),
                            "to": identifier,
                        })
        return tuple(edges)

    def unknowns(self, priority: str | None = None) -> tuple[dict[str, Any], ...]:
        raw = self.document.get("unknowns", [])
        if not isinstance(raw, list):
            raise RegistryError("Registry unknowns section must be a list")
        values = tuple(item for item in raw if isinstance(item, dict))
        if priority is None:
            return values
        return tuple(item for item in values if item.get("priority") == priority)

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self) -> Iterable[RegistryRecord]:
        return iter(self._records.values())
