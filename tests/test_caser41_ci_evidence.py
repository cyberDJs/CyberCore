from cybercore.caser41_ci_evidence import (
    DEFAULT_REQUIRED_CHECKS,
    CheckObservation,
    evaluate_ci_evidence,
)

SHA = "a" * 40


def _checks() -> list[CheckObservation]:
    return [
        CheckObservation(name, SHA, "completed", "success")
        for name in sorted(DEFAULT_REQUIRED_CHECKS)
    ]


def test_complete_exact_head_snapshot_passes() -> None:
    result = evaluate_ci_evidence(SHA, _checks())
    assert result.passed
    assert result.reason == "EVIDENCE_CHECKS_PASSED"


def test_stale_head_fails_closed() -> None:
    checks = _checks()
    checks[0] = CheckObservation(checks[0].name, "b" * 40, "completed", "success")
    assert evaluate_ci_evidence(SHA, checks).reason == "STALE_OR_FOREIGN_SHA"


def test_missing_matrix_job_fails() -> None:
    checks = [item for item in _checks() if item.name != "tests (python 3.14)"]
    result = evaluate_ci_evidence(SHA, checks)
    assert not result.passed
    assert result.missing == ("tests (python 3.14)",)


def test_pending_job_fails_even_if_other_jobs_succeed() -> None:
    checks = _checks()
    checks[0] = CheckObservation(checks[0].name, SHA, "in_progress", None)
    assert evaluate_ci_evidence(SHA, checks).reason == "INCOMPLETE_REQUIRED_CHECK"


def test_failed_job_fails_even_if_workflow_success_is_reported() -> None:
    checks = _checks()
    checks[0] = CheckObservation(checks[0].name, SHA, "completed", "failure")
    assert evaluate_ci_evidence(SHA, checks).reason == "FAILED_REQUIRED_CHECK"


def test_duplicate_context_fails_closed() -> None:
    checks = _checks()
    checks.append(checks[0])
    assert evaluate_ci_evidence(SHA, checks).reason == "DUPLICATE_REQUIRED_CHECK"


def test_unknown_extra_context_does_not_replace_missing_required_one() -> None:
    checks = _checks()[1:]
    checks.append(CheckObservation("untrusted / success", SHA, "completed", "success"))
    assert evaluate_ci_evidence(SHA, checks).reason == "MISSING_REQUIRED_CHECKS"


def test_invalid_sha_and_empty_policy_cannot_pass() -> None:
    assert evaluate_ci_evidence("HEAD", _checks()).reason == "INVALID_EXPECTED_SHA"
    assert evaluate_ci_evidence(SHA, _checks(), required_checks=frozenset()).reason == (
        "INVALID_REQUIRED_CHECKS"
    )


def test_informational_codeql_display_does_not_replace_required_job() -> None:
    checks = [item for item in _checks() if item.name != "codeql"]
    checks.append(CheckObservation("CodeQL", SHA, "completed", "success"))
    result = evaluate_ci_evidence(SHA, checks)
    assert not result.passed
    assert result.missing == ("codeql",)


def test_failed_codeql_job_overrides_successful_display_check() -> None:
    checks = _checks()
    checks = [
        CheckObservation("codeql", SHA, "completed", "failure") if item.name == "codeql" else item
        for item in checks
    ]
    checks.append(CheckObservation("CodeQL", SHA, "completed", "success"))
    assert evaluate_ci_evidence(SHA, checks).reason == "FAILED_REQUIRED_CHECK"
