from pathlib import Path

from cybercore.ccl import CCLValidator
from cybercore.cli import main


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ccl"


def test_valid_observation_fixture() -> None:
    validator = CCLValidator.from_repo(REPO_ROOT)
    result = validator.validate_file(FIXTURES / "valid-observation.json")

    assert result.valid is True
    assert result.record_id == "cybercore:observation:test-001"
    assert result.errors == []


def test_invalid_evidence_time_order() -> None:
    validator = CCLValidator.from_repo(REPO_ROOT)
    result = validator.validate_file(FIXTURES / "invalid-evidence-time-order.json")

    assert result.valid is False
    assert [issue.code for issue in result.errors] == ["semantic_time_order"]


def test_ccl_validate_cli_success(capsys) -> None:
    rc = main(
        [
            "--repo",
            str(REPO_ROOT),
            "ccl",
            "validate",
            str(FIXTURES / "valid-observation.json"),
        ]
    )

    assert rc == 0
    assert "VALID cybercore:observation:test-001" in capsys.readouterr().out


def test_ccl_validate_cli_failure(capsys) -> None:
    rc = main(
        [
            "--repo",
            str(REPO_ROOT),
            "ccl",
            "validate",
            str(FIXTURES / "invalid-evidence-time-order.json"),
        ]
    )

    assert rc == 1
    output = capsys.readouterr().out
    assert "INVALID cybercore:evidence:test-001" in output
    assert "semantic_time_order" in output
