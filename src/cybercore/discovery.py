from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from typing import Any, Callable, Iterable

from cybercore.registry import Registry, RegistryRecord


Severity = str
Detector = Callable[[Registry], Iterable["DiscoveryFinding"]]


@dataclass(frozen=True, slots=True)
class DiscoveryFinding:
    id: str
    detector: str
    severity: Severity
    subject_ref: str | None
    summary: str
    evidence: tuple[str, ...]
    proposed_action: str

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence"] = list(self.evidence)
        return payload


def _finding_id(detector: str, subject_ref: str | None, summary: str) -> str:
    source = f"{detector}|{subject_ref or '-'}|{summary}".encode("utf-8")
    return f"DISC-{hashlib.sha256(source).hexdigest()[:12].upper()}"


def _finding(
    detector: str,
    severity: Severity,
    subject_ref: str | None,
    summary: str,
    evidence: Iterable[str],
    proposed_action: str,
) -> DiscoveryFinding:
    return DiscoveryFinding(
        id=_finding_id(detector, subject_ref, summary),
        detector=detector,
        severity=severity,
        subject_ref=subject_ref,
        summary=summary,
        evidence=tuple(evidence),
        proposed_action=proposed_action,
    )


def detect_registry_unknowns(registry: Registry) -> Iterable[DiscoveryFinding]:
    for unknown in registry.unknowns():
        identifier = str(unknown.get("id", "UNKNOWN"))
        question = str(unknown.get("question", "Unresolved registry question"))
        priority = str(unknown.get("priority", "medium"))
        severity = "high" if priority == "high" else "medium"
        yield _finding(
            "registry-unknown",
            severity,
            identifier,
            question,
            (f"registry:unknowns/{identifier}",),
            "Collect evidence and resolve the registry unknown.",
        )


def detect_missing_monitoring(registry: Registry) -> Iterable[DiscoveryFinding]:
    for record in registry.records("assets"):
        monitoring = record.data.get("monitoring")
        if not isinstance(monitoring, dict) or monitoring.get("status") in (None, "unknown", "disabled"):
            yield _finding(
                "monitoring-coverage",
                "high" if record.data.get("status") == "active" else "medium",
                record.id,
                f"Monitoring coverage is unknown for {record.name}.",
                (f"registry:{record.id}.monitoring",),
                "Verify monitoring coverage and record the monitor reference.",
            )


def detect_missing_backup(registry: Registry) -> Iterable[DiscoveryFinding]:
    for record in registry.records("assets"):
        backup = record.data.get("backup")
        if not isinstance(backup, dict) or backup.get("status") in (None, "unknown", "disabled"):
            yield _finding(
                "backup-coverage",
                "high" if record.data.get("status") == "active" else "medium",
                record.id,
                f"Backup coverage is unknown for {record.name}.",
                (f"registry:{record.id}.backup",),
                "Verify backup scope and attach restore-test evidence.",
            )


def detect_active_services_without_endpoints(registry: Registry) -> Iterable[DiscoveryFinding]:
    for record in registry.records("services"):
        endpoints = record.data.get("endpoints")
        if record.data.get("status") == "active" and (not isinstance(endpoints, list) or not endpoints):
            yield _finding(
                "service-endpoint",
                "medium",
                record.id,
                f"Active service {record.name} has no documented endpoint.",
                (f"registry:{record.id}.endpoints",),
                "Discover and document service endpoints, or mark the service as intentionally internal.",
            )


DEFAULT_DETECTORS: tuple[Detector, ...] = (
    detect_registry_unknowns,
    detect_missing_monitoring,
    detect_missing_backup,
    detect_active_services_without_endpoints,
)


class DiscoveryEngine:
    """Runs deterministic, read-only detectors over a Registry snapshot."""

    def __init__(self, registry: Registry, detectors: Iterable[Detector] = DEFAULT_DETECTORS) -> None:
        self.registry = registry
        self.detectors = tuple(detectors)

    def run(self) -> tuple[DiscoveryFinding, ...]:
        findings = [finding for detector in self.detectors for finding in detector(self.registry)]
        return tuple(sorted(findings, key=lambda item: (item.severity, item.detector, item.id)))
