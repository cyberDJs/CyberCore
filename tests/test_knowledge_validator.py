from __future__ import annotations

from datetime import date
from pathlib import Path

from cybercore.cli import main
from cybercore.knowledge import validate_repository


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_validator_accepts_traceable_records(tmp_path: Path) -> None:
    _write(
        tmp_path / "knowledge/records.yaml",
        """
evidence:
  - id: EVD-0001
    source_type: command_output
    source_ref: test
    observed_at: 2026-07-20T00:00:00Z
    classification: internal
    summary: test evidence
    freshness:
      review_after: 2026-08-20
claims:
  - id: CLM-0001
    subject_ref: ASSET-001
    predicate: state
    value: active
    evidence_refs: [EVD-0001]
    confidence: 0.95
    status: verified
    review_after: 2026-08-20
assets:
  - id: ASSET-001
    kind: asset
    name: Test asset
    status: active
    owner: CyberCore
    classification: internal
    last_reviewed: 2026-07-20
    evidence:
      - type: test
        reference: EVD-0001
""",
    )
    report = validate_repository(tmp_path, today=date(2026, 7, 20))
    assert report.successful
    assert report.records_checked == 3


def test_validator_rejects_missing_evidence_reference(tmp_path: Path) -> None:
    _write(
        tmp_path / "knowledge/records.yaml",
        """
claims:
  - id: CLM-0001
    subject_ref: ASSET-001
    predicate: state
    value: active
    evidence_refs: [EVD-9999]
    confidence: 0.95
    status: verified
    review_after: 2026-08-20
""",
    )
    report = validate_repository(tmp_path, today=date(2026, 7, 20))
    assert not report.successful
    assert any(item.code == "claim.missing_evidence" for item in report.errors)


def test_validate_cli_returns_nonzero_on_invalid_repository(tmp_path: Path) -> None:
    _write(tmp_path / "knowledge/records.yaml", "claims: [{id: CLM-0001}]")
    assert main(["--repo", str(tmp_path), "validate"]) == 1
