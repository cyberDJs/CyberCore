from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable

from cybercore.registry import Registry, RegistryError, RegistryRecord


@dataclass(frozen=True, slots=True)
class RegistryEdge:
    source: str
    relationship: str
    target: str


class RegistryGraph:
    """Deterministic in-memory graph built from Registry relationships."""

    def __init__(self, registry: Registry) -> None:
        self.registry = registry
        self._outgoing: dict[str, tuple[RegistryEdge, ...]] = {}
        self._incoming: dict[str, tuple[RegistryEdge, ...]] = {}
        self._build()

    @classmethod
    def load(cls, registry: Registry) -> "RegistryGraph":
        return cls(registry)

    def _build(self) -> None:
        outgoing: dict[str, list[RegistryEdge]] = {record.id: [] for record in self.registry}
        incoming: dict[str, list[RegistryEdge]] = {record.id: [] for record in self.registry}

        for record in self.registry:
            relationships = record.data.get("relationships", [])
            if relationships is None:
                relationships = []
            if not isinstance(relationships, list):
                raise RegistryError(f"Relationships for {record.id} must be a list")
            for index, value in enumerate(relationships):
                if not isinstance(value, dict):
                    raise RegistryError(f"Relationship {record.id}[{index}] must be an object")
                relationship = value.get("type")
                target = value.get("target")
                if not isinstance(relationship, str) or not relationship:
                    raise RegistryError(f"Relationship {record.id}[{index}] has no valid type")
                if not isinstance(target, str) or not target:
                    raise RegistryError(f"Relationship {record.id}[{index}] has no valid target")
                if self.registry.get(target) is None:
                    raise RegistryError(f"Relationship target does not exist: {record.id} -> {target}")
                edge = RegistryEdge(record.id, relationship, target)
                outgoing[record.id].append(edge)
                incoming[target].append(edge)

        self._outgoing = {key: tuple(values) for key, values in outgoing.items()}
        self._incoming = {key: tuple(values) for key, values in incoming.items()}

    def edges(self) -> tuple[RegistryEdge, ...]:
        return tuple(edge for values in self._outgoing.values() for edge in values)

    def outgoing(self, identifier: str, relationship: str | None = None) -> tuple[RegistryEdge, ...]:
        self.registry.require(identifier)
        values = self._outgoing.get(identifier, ())
        if relationship is None:
            return values
        return tuple(edge for edge in values if edge.relationship == relationship)

    def incoming(self, identifier: str, relationship: str | None = None) -> tuple[RegistryEdge, ...]:
        self.registry.require(identifier)
        values = self._incoming.get(identifier, ())
        if relationship is None:
            return values
        return tuple(edge for edge in values if edge.relationship == relationship)

    def neighbours(self, identifier: str, relationship: str | None = None) -> tuple[RegistryRecord, ...]:
        self.registry.require(identifier)
        ids: list[str] = []
        for edge in (*self.outgoing(identifier, relationship), *self.incoming(identifier, relationship)):
            candidate = edge.target if edge.source == identifier else edge.source
            if candidate not in ids:
                ids.append(candidate)
        return tuple(self.registry.require(value) for value in ids)

    def shortest_path(self, source: str, target: str) -> tuple[str, ...]:
        self.registry.require(source)
        self.registry.require(target)
        if source == target:
            return (source,)

        queue: deque[tuple[str, tuple[str, ...]]] = deque([(source, (source,))])
        visited = {source}
        while queue:
            current, path = queue.popleft()
            for neighbour in self.neighbours(current):
                if neighbour.id in visited:
                    continue
                next_path = (*path, neighbour.id)
                if neighbour.id == target:
                    return next_path
                visited.add(neighbour.id)
                queue.append((neighbour.id, next_path))
        return ()

    def traverse(
        self,
        identifier: str,
        *,
        direction: str = "outgoing",
        relationship: str | None = None,
        max_depth: int | None = None,
    ) -> tuple[RegistryRecord, ...]:
        self.registry.require(identifier)
        if direction not in {"outgoing", "incoming"}:
            raise RegistryError("Graph direction must be 'outgoing' or 'incoming'")
        if max_depth is not None and max_depth < 0:
            raise RegistryError("Graph max_depth cannot be negative")

        queue: deque[tuple[str, int]] = deque([(identifier, 0)])
        visited = {identifier}
        result: list[RegistryRecord] = []
        while queue:
            current, depth = queue.popleft()
            if max_depth is not None and depth >= max_depth:
                continue
            edges = self.outgoing(current, relationship) if direction == "outgoing" else self.incoming(current, relationship)
            for edge in edges:
                candidate = edge.target if direction == "outgoing" else edge.source
                if candidate in visited:
                    continue
                visited.add(candidate)
                result.append(self.registry.require(candidate))
                queue.append((candidate, depth + 1))
        return tuple(result)

    def dependencies(self, identifier: str) -> tuple[RegistryRecord, ...]:
        return self.traverse(identifier, direction="outgoing", relationship="depends_on")

    def impact(self, identifier: str) -> tuple[RegistryRecord, ...]:
        """Return records that can reach the identifier through any relationship."""
        return self.traverse(identifier, direction="incoming")

    def __len__(self) -> int:
        return len(self.edges())

    def __iter__(self) -> Iterable[RegistryEdge]:
        return iter(self.edges())
