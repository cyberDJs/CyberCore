from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import yaml


@dataclass(frozen=True, slots=True)
class ValidationFinding:
    severity: str
    code: str
    path: str
    message: str


@dataclass(slots=True)
class ValidationReport:
    files_checked: int = 0
    records_checked: int = 0
    findings: list[ValidationFinding] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationFinding]:
        return [item for item in self.findings if item.severity == "error"]

    @property
    def warnings(self) -> list[ValidationFinding]:
        return [item for item in self.findings if item.severity == "warning"]

    @property
    def successful(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "successful": self.successful,
            "files_checked": self.files_checked,
            "records_checked": self.records_checked,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "findings": [
                {
                    "severity": finding.severity,
                    "code": finding.code,
                    "path": finding.path,
                    "message": finding.message,
                }
                for finding in self.findings
            ],
        }


class KnowledgeValidator:
    """Deterministic validator for the file-backed CyberCore knowledge layer."""

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
    RECORD_SECTIONS = ("evidence", "claims", "relationships", "decision_candidates")
    SECRET_MARKERS = ("password", "passwd", "private_key", "api_key", "access_token", "secret_value")

    def __init__(self, repo: Path, today: date | None = None) -> None:
        self.repo = repo
        self.today = today or date.today()
        self.report = ValidationReport()
        self.ids: dict[str, str] = {}
        self.evidence_ids: set[str] = set()
        self.claim_ids: set[str] = set()

    def validate(self) -> ValidationReport:
        knowledge = self.repo / "knowledge"
        if not knowledge.is_dir():
            self._add("error", "knowledge.missing", "knowledge", "Knowledge directory does not exist")
            return self.report

        yaml_files = sorted(knowledge.rglob("*.yaml")) + sorted(knowledge.rglob("*.yml"))
        if not yaml_files:
            self._add("error", "knowledge.empty", "knowledge", "No YAML knowledge files found")
            return self.report

        documents: list[tuple[Path, Any]] = []
        for path in yaml_files:
            relative = path.relative_to(self.repo)
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError) as exc:
                self._add("error", "yaml.invalid", str(relative), str(exc))
                continue
            self.report.files_checked += 1
            documents.append((relative, data))
            self._scan_secrets(data, str(relative))
            self._index_records(data, str(relative))

        for relative, data in documents:
            self._validate_document(data, str(relative))
        return self.report

    def _validate_document(self, data: Any, path: str) -> None:
        if not isinstance(data, dict):
            return
        for section in self.ENTITY_SECTIONS:
            records = data.get(section, [])
            if isinstance(records, list):
                for index, record in enumerate(records):
                    self._validate_entity(record, f"{path}:{section}[{index}]")
        for section in self.RECORD_SECTIONS:
            records = data.get(section, [])
            if isinstance(records, list):
                for index, record in enumerate(records):
                    record_path = f"{path}:{section}[{index}]"
                    if section == "evidence":
                        self._validate_evidence(record, record_path)
                    elif section == "claims":
                        self._validate_claim(record, record_path)
                    elif section == "relationships":
                        self._validate_relationship(record, record_path)
                    elif section == "decision_candidates":
                        self._validate_decision(record, record_path)

    def _index_records(self, data: Any, path: str) -> None:
        if not isinstance(data, dict):
            return
        for section in (*self.ENTITY_SECTIONS, *self.RECORD_SECTIONS):
            records = data.get(section, [])
            if not isinstance(records, list):
                continue
            for index, record in enumerate(records):
                if not isinstance(record, dict):
                    continue
                identifier = record.get("id")
                if not isinstance(identifier, str):
                    continue
                location = f"{path}:{section}[{index}]"
                if identifier in self.ids:
                    self._add("error", "id.duplicate", location, f"Duplicate ID {identifier}; first seen at {self.ids[identifier]}")
                else:
                    self.ids[identifier] = location
                if section == "evidence":
                    self.evidence_ids.add(identifier)
                if section == "claims":
                    self.claim_ids.add(identifier)

    def _validate_entity(self, record: Any, path: str) -> None:
        self.report.records_checked += 1
        if not isinstance(record, dict):
            self._add("error", "entity.type", path, "Entity must be an object")
            return
        self._require(record, ("id", "kind", "name", "status", "owner", "classification", "last_reviewed"), path)
        self._validate_date(record.get("last_reviewed"), path, "last_reviewed")
        for relationship in record.get("relationships", []):
            if not isinstance(relationship, dict) or not relationship.get("type") or not relationship.get("target"):
                self._add("error", "relationship.invalid", path, "Inline relationship requires type and target")
                continue
            target = relationship["target"]
            if target not in self.ids:
                self._add("error", "relationship.missing_target", path, f"Relationship target {target} does not exist")
        evidence = record.get("evidence", [])
        if not evidence:
            self._add("warning", "entity.no_evidence", path, "Entity has no evidence")

    def _validate_evidence(self, record: Any, path: str) -> None:
        self.report.records_checked += 1
        if not isinstance(record, dict):
            self._add("error", "evidence.type", path, "Evidence must be an object")
            return
        self._require(record, ("id", "source_type", "source_ref", "observed_at", "classification", "summary", "freshness"), path)
        freshness = record.get("freshness")
        if isinstance(freshness, dict):
            review_after = self._parse_date(freshness.get("review_after"))
            expires_after = self._parse_date(freshness.get("expires_after"))
            if review_after and review_after < self.today:
                self._add("warning", "evidence.stale", path, f"Evidence review was due {review_after.isoformat()}")
            if expires_after and expires_after < self.today:
                self._add("error", "evidence.expired", path, f"Evidence expired {expires_after.isoformat()}")
        else:
            self._add("error", "evidence.freshness", path, "Evidence freshness must be an object")

    def _validate_claim(self, record: Any, path: str) -> None:
        self.report.records_checked += 1
        if not isinstance(record, dict):
            self._add("error", "claim.type", path, "Claim must be an object")
            return
        self._require(record, ("id", "subject_ref", "predicate", "value", "evidence_refs", "confidence", "status", "review_after"), path)
        confidence = record.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            self._add("error", "claim.confidence", path, "Confidence must be between 0.0 and 1.0")
        refs = record.get("evidence_refs")
        if not isinstance(refs, list) or not refs:
            self._add("error", "claim.no_evidence", path, "Claim must reference at least one evidence record")
        else:
            for ref in refs:
                if ref not in self.evidence_ids:
                    self._add("error", "claim.missing_evidence", path, f"Evidence reference {ref} does not exist")
        review_after = self._parse_date(record.get("review_after"))
        if review_after and review_after < self.today:
            self._add("warning", "claim.stale", path, f"Claim review was due {review_after.isoformat()}")
        for ref in record.get("contradicts", []):
            if ref not in self.claim_ids:
                self._add("error", "claim.missing_contradiction", path, f"Contradicted claim {ref} does not exist")

    def _validate_relationship(self, record: Any, path: str) -> None:
        self.report.records_checked += 1
        if not isinstance(record, dict):
            self._add("error", "relationship.type", path, "Relationship must be an object")
            return
        self._require(record, ("id", "from_ref", "type", "to_ref", "claim_ref"), path)
        for field_name in ("from_ref", "to_ref"):
            ref = record.get(field_name)
            if isinstance(ref, str) and ref not in self.ids:
                self._add("error", "relationship.missing_endpoint", path, f"{field_name} {ref} does not exist")
        claim_ref = record.get("claim_ref")
        if isinstance(claim_ref, str) and claim_ref not in self.claim_ids:
            self._add("error", "relationship.missing_claim", path, f"Claim reference {claim_ref} does not exist")

    def _validate_decision(self, record: Any, path: str) -> None:
        self.report.records_checked += 1
        if not isinstance(record, dict):
            self._add("error", "decision.type", path, "Decision candidate must be an object")
            return
        self._require(record, ("id", "problem", "options", "recommended_option", "supporting_claims", "risk", "requires_human_approval"), path)
        if record.get("requires_human_approval") is not True:
            self._add("error", "decision.approval", path, "Decision candidate must require human approval")
        options = record.get("options")
        if not isinstance(options, list) or len(options) < 2:
            self._add("error", "decision.options", path, "Decision candidate requires at least two options")
        for ref in record.get("supporting_claims", []):
            if ref not in self.claim_ids:
                self._add("error", "decision.missing_claim", path, f"Supporting claim {ref} does not exist")

    def _scan_secrets(self, value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = str(key).lower()
                if any(marker in normalized for marker in self.SECRET_MARKERS) and child not in (None, "", "REDACTED"):
                    self._add("error", "secret.possible_value", path, f"Possible secret-bearing field: {key}")
                self._scan_secrets(child, path)
        elif isinstance(value, list):
            for child in value:
                self._scan_secrets(child, path)

    def _require(self, record: dict[str, Any], fields: Iterable[str], path: str) -> None:
        for field_name in fields:
            if field_name not in record or record[field_name] in (None, ""):
                self._add("error", "field.required", path, f"Missing required field: {field_name}")

    def _validate_date(self, value: Any, path: str, field_name: str) -> None:
        if value is not None and self._parse_date(value) is None:
            self._add("error", "date.invalid", path, f"Invalid {field_name}: {value!r}")

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value[:10])
            except ValueError:
                return None
        return None

    def _add(self, severity: str, code: str, path: str, message: str) -> None:
        self.report.findings.append(ValidationFinding(severity, code, path, message))


def validate_repository(repo: Path, today: date | None = None) -> ValidationReport:
    return KnowledgeValidator(repo, today=today).validate()
