from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from jsonschema import ValidationError
from jsonschema.validators import validator_for
from referencing import Registry, Resource


SCHEMA_FILES: dict[str, str] = {
    "observation": "observation.schema.json",
    "evidence": "evidence.schema.json",
    "entity": "entity.schema.json",
    "claim": "claim.schema.json",
    "relationship": "relationship.schema.json",
    "contradiction": "contradiction.schema.json",
    "knowledge_state": "knowledge-state.schema.json",
    "finding": "finding.schema.json",
    "policy": "policy.schema.json",
    "intent": "intent.schema.json",
    "decision_candidate": "decision-candidate.schema.json",
    "mutation_plan": "mutation-plan.schema.json",
    "approval": "approval.schema.json",
    "apply_result": "apply-result.schema.json",
    "verification": "verification.schema.json",
    "outcome": "outcome.schema.json",
}


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    schema_id: str | None
    record_id: str | None
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "schema_id": self.schema_id,
            "record_id": self.record_id,
            "errors": [issue.__dict__ for issue in self.errors],
            "warnings": [issue.__dict__ for issue in self.warnings],
        }


class CCLValidationError(RuntimeError):
    """Raised when the validator cannot load or identify a CCL record."""


def _json_pointer(parts: list[Any]) -> str:
    if not parts:
        return "/"
    escaped = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(escaped)


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class CCLValidator:
    def __init__(self, schema_root: Path) -> None:
        self.schema_root = schema_root
        if not schema_root.is_dir():
            raise CCLValidationError(f"CCL schema directory not found: {schema_root}")
        self._schemas = self._load_schemas()

        resources: list[tuple[str, Resource[Any]]] = []
        base_uri = "cybercore://schemas/ccl/v1/"
        for filename, schema in self._schemas.items():
            resource = Resource.from_contents(schema)
            if "$id" in schema:
                resources.append((schema["$id"], resource))
            resources.append((f"{base_uri}{filename}", resource))
        self._registry = Registry().with_resources(resources)

    @classmethod
    def from_repo(cls, repo: Path) -> "CCLValidator":
        return cls(repo / "schemas" / "ccl" / "v1")

    def _load_schemas(self) -> dict[str, dict[str, Any]]:
        schemas: dict[str, dict[str, Any]] = {}
        for path in sorted(self.schema_root.glob("*.schema.json")):
            with path.open("r", encoding="utf-8") as handle:
                schemas[path.name] = json.load(handle)
        if not schemas:
            raise CCLValidationError(f"No CCL schemas found in {self.schema_root}")
        return schemas

    def validate_file(self, path: Path) -> ValidationResult:
        try:
            with path.open("r", encoding="utf-8") as handle:
                record = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise CCLValidationError(f"Cannot read CCL record {path}: {exc}") from exc
        return self.validate(record)

    def validate(self, record: dict[str, Any]) -> ValidationResult:
        record_type = record.get("type")
        filename = SCHEMA_FILES.get(record_type)
        if filename is None:
            raise CCLValidationError(f"Unsupported CCL record type: {record_type!r}")
        schema = self._schemas.get(filename)
        if schema is None:
            raise CCLValidationError(
                f"Schema is missing for CCL type {record_type!r}: {filename}"
            )

        validator_class = validator_for(schema)
        validator_class.check_schema(schema)
        validator = validator_class(schema, registry=self._registry)
        errors = [
            self._schema_issue(error)
            for error in sorted(validator.iter_errors(record), key=str)
        ]
        if not errors:
            errors.extend(self._semantic_issues(record))

        return ValidationResult(
            valid=not errors,
            schema_id=schema.get("$id"),
            record_id=record.get("id"),
            errors=errors,
        )

    @staticmethod
    def _schema_issue(error: ValidationError) -> ValidationIssue:
        return ValidationIssue(
            code=f"schema_{error.validator}",
            path=_json_pointer(list(error.absolute_path)),
            message=error.message,
        )

    def _semantic_issues(self, record: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        attributes = record.get("attributes", {})
        record_type = record.get("type")

        if record_type == "evidence":
            observed_at = attributes.get("observed_at")
            recorded_at = attributes.get("recorded_at")
            if (
                observed_at
                and recorded_at
                and _parse_time(recorded_at) < _parse_time(observed_at)
            ):
                issues.append(
                    ValidationIssue(
                        code="semantic_time_order",
                        path="/attributes/recorded_at",
                        message="recorded_at must not precede observed_at",
                    )
                )

        if record_type == "verification":
            started_at = attributes.get("apply_started_at")
            observed_at = attributes.get("observed_at")
            if (
                started_at
                and observed_at
                and _parse_time(observed_at) < _parse_time(started_at)
            ):
                issues.append(
                    ValidationIssue(
                        code="semantic_verification_time",
                        path="/attributes/observed_at",
                        message="verification observation must not precede apply execution",
                    )
                )

        confidence = attributes.get("confidence")
        if isinstance(confidence, dict):
            issues.extend(self._confidence_issues(confidence))

        return issues

    @staticmethod
    def _confidence_issues(confidence: dict[str, Any]) -> list[ValidationIssue]:
        level = confidence.get("level")
        score = confidence.get("score")
        if level == "unknown" and score is not None:
            return [
                ValidationIssue(
                    code="semantic_confidence_unknown",
                    path="/attributes/confidence/score",
                    message="unknown confidence must not define a score",
                )
            ]
        if score is None:
            return []
        ranges = {
            "low": (0.0, 0.39),
            "medium": (0.40, 0.69),
            "high": (0.70, 0.94),
            "verified": (0.95, 1.0),
        }
        expected = ranges.get(level)
        if expected and not expected[0] <= score <= expected[1]:
            return [
                ValidationIssue(
                    code="semantic_confidence_range",
                    path="/attributes/confidence/score",
                    message=f"score {score} is inconsistent with confidence level {level}",
                )
            ]
        return []
