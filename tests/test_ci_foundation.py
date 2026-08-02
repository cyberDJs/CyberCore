from __future__ import annotations

from pathlib import Path
import re
import tomllib

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
VERIFY_SCRIPT_PATH = REPO_ROOT / "scripts" / "verify.sh"
ALLOWED_ACTIONS = {
    "actions/checkout",
    "actions/setup-python",
    "actions/upload-artifact",
}
PINNED_ACTION_REF = re.compile(r"^(actions/[a-z0-9-]+)@([0-9a-f]{40})$")


def _pyproject() -> dict[str, object]:
    return tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))


def _workflow() -> dict[str, object]:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _uses_steps() -> list[dict[str, object]]:
    steps: list[dict[str, object]] = []
    for job in _workflow()["jobs"].values():
        steps.extend(step for step in job["steps"] if "uses" in step)
    return steps


def test_pyproject_defines_required_development_toolchain() -> None:
    pyproject = _pyproject()
    project = pyproject["project"]
    dependencies = project["dependencies"]
    dev_dependencies = project["optional-dependencies"]["dev"]
    dev_names = {dependency.split(">=", 1)[0].lower() for dependency in dev_dependencies}

    assert pyproject["build-system"]["build-backend"] == "hatchling.build"
    assert project["requires-python"] == ">=3.11"
    assert {"pytest", "ruff", "pyright", "build", "pyyaml"} <= dev_names
    assert all("ruff" not in dependency.lower() for dependency in dependencies)
    assert all("pyright" not in dependency.lower() for dependency in dependencies)
    assert all("pytest" not in dependency.lower() for dependency in dependencies)


def test_pyproject_configures_ruff_and_pyright_baselines() -> None:
    tool = _pyproject()["tool"]

    assert tool["ruff"]["target-version"] == "py311"
    assert tool["ruff"]["src"] == ["src", "tests"]
    assert tool["ruff"]["lint"]["select"] == ["E4", "E7", "E9", "F"]
    assert tool["pyright"]["pythonVersion"] == "3.11"
    assert tool["pyright"]["typeCheckingMode"] == "basic"
    assert tool["pyright"]["include"] == ["src/cybercore"]
    assert tool["pyright"]["venvPath"] == "."
    assert tool["pyright"]["venv"] == ".venv"


def test_ci_workflow_parses_and_uses_expected_triggers() -> None:
    workflow = _workflow()
    triggers = workflow.get("on") or workflow.get(True)

    assert triggers["pull_request"]["branches"] == ["main"]
    assert triggers["push"]["branches"] == ["main"]
    assert "workflow_dispatch" in triggers


def test_ci_workflow_security_and_action_pinning_invariants() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = _workflow()
    uses_steps = _uses_steps()

    assert workflow["permissions"] == {"contents": "read"}
    assert "pull_request_target" not in workflow_text
    assert workflow["concurrency"]["cancel-in-progress"] is True

    assert uses_steps
    for step in uses_steps:
        uses = step["uses"]
        assert isinstance(uses, str)
        ref = PINNED_ACTION_REF.fullmatch(uses)
        assert ref is not None
        assert ref.group(1) in ALLOWED_ACTIONS
        if ref.group(1) == "actions/checkout":
            assert step.get("with", {}).get("persist-credentials") is False


def test_ci_workflow_defines_required_checks_and_python_matrix() -> None:
    jobs = _workflow()["jobs"]
    matrix = jobs["tests"]["strategy"]["matrix"]["python-version"]

    assert set(jobs) == {"tests", "quality", "package"}
    assert matrix[0] == "3.11"
    assert matrix == ["3.11", "3.12", "3.13", "3.14"]
    assert jobs["quality"]["name"] == "quality"
    assert jobs["package"]["name"] == "package"


def test_package_job_installs_built_wheel_and_smokes_outside_checkout() -> None:
    package_steps = _workflow()["jobs"]["package"]["steps"]
    step_runs = "\n".join(step.get("run", "") for step in package_steps)

    assert "python -m build" in step_runs
    assert "test -f dist/cybercore-0.1.0-py3-none-any.whl" in step_runs
    assert "test -f dist/cybercore-0.1.0.tar.gz" in step_runs
    assert "pip install dist/cybercore-0.1.0-py3-none-any.whl" in step_runs
    assert 'cd "$outside"' in step_runs
    assert 'venv/bin/cybercore" --help' in step_runs
    assert 'venv/bin/python" -m cybercore --help' in step_runs


def test_local_verification_entrypoint_is_non_mutating() -> None:
    script = VERIFY_SCRIPT_PATH.read_text(encoding="utf-8")

    assert script.startswith("#!/bin/sh\nset -eu\n")
    assert "ruff check src tests" in script
    assert "ruff format --check src tests" in script
    assert "pyright" in script
    assert "pytest -q" in script
    assert "compileall -q src tests" in script
    assert '"$PYTHON" -m build' in script
    assert "pip install" not in script
    assert "ruff format src tests" not in script
