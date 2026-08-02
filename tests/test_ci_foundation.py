from __future__ import annotations

from pathlib import Path
import re
import tomllib

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
CI_WORKFLOW_PATH = WORKFLOW_DIR / "ci.yml"
CODEQL_WORKFLOW_PATH = WORKFLOW_DIR / "codeql.yml"
VERIFY_SCRIPT_PATH = REPO_ROOT / "scripts" / "verify.sh"
ALLOWED_ACTIONS = {
    "actions/checkout",
    "actions/setup-python",
    "actions/upload-artifact",
    "github/codeql-action/init",
    "github/codeql-action/analyze",
}
PINNED_ACTION_REF = re.compile(r"^([a-z0-9-]+/[a-z0-9-]+(?:/[a-z0-9-]+)?)@([0-9a-f]{40})$")
CODEQL_ACTION_SHA = "f205ea1c3313d32999d8d6a48b4f6530d4437b38"
CHECKOUT_SHA = "d23441a48e516b6c34aea4fa41551a30e30af803"


def _pyproject() -> dict[str, object]:
    return tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))


def _workflow(path: Path = CI_WORKFLOW_PATH) -> dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _triggers(workflow: dict[str, object]) -> dict[str, object]:
    triggers = workflow.get("on") or workflow.get(True)
    assert isinstance(triggers, dict)
    return triggers


def _workflow_paths() -> list[Path]:
    return sorted(WORKFLOW_DIR.glob("*.yml"))


def _uses_steps(path: Path | None = None) -> list[dict[str, object]]:
    steps: list[dict[str, object]] = []
    paths = [path] if path is not None else _workflow_paths()
    for workflow_path in paths:
        for job in _workflow(workflow_path)["jobs"].values():
            assert isinstance(job, dict)
            assert isinstance(job.get("steps"), list)
            steps.extend(step for step in job["steps"] if "uses" in step)
    return steps


def _workflow_contains_path_filters(triggers: dict[str, object]) -> bool:
    for event in ("pull_request", "push"):
        event_config = triggers.get(event)
        if isinstance(event_config, dict) and (
            "paths" in event_config or "paths-ignore" in event_config
        ):
            return True
    return False


def _job_named(workflow: dict[str, object], name: str) -> dict[str, object]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs[name]
    assert isinstance(job, dict)
    return job


def _step_uses(job: dict[str, object], action_path: str) -> list[dict[str, object]]:
    steps = job["steps"]
    assert isinstance(steps, list)
    return [
        step
        for step in steps
        if isinstance(step, dict)
        and isinstance(step.get("uses"), str)
        and step["uses"].startswith(f"{action_path}@")
    ]


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


def test_all_workflows_parse_as_valid_yaml() -> None:
    paths = _workflow_paths()

    assert paths == [CI_WORKFLOW_PATH, CODEQL_WORKFLOW_PATH]
    for path in paths:
        workflow = _workflow(path)
        assert isinstance(workflow, dict)
        assert isinstance(workflow.get("name"), str)
        assert isinstance(workflow.get("jobs"), dict)


def test_workflow_security_and_action_pinning_invariants() -> None:
    workflow_text = "\n".join(path.read_text(encoding="utf-8") for path in _workflow_paths())
    uses_steps = _uses_steps()

    assert "pull_request_target" not in workflow_text
    assert uses_steps
    for step in uses_steps:
        uses = step["uses"]
        assert isinstance(uses, str)
        ref = PINNED_ACTION_REF.fullmatch(uses)
        assert ref is not None
        assert ref.group(1) in ALLOWED_ACTIONS
        if ref.group(1) == "actions/checkout":
            assert ref.group(2) == CHECKOUT_SHA
            assert step.get("with", {}).get("persist-credentials") is False
        elif ref.group(1).startswith("github/codeql-action/"):
            assert ref.group(2) == CODEQL_ACTION_SHA


def test_workflow_permissions_remain_minimal() -> None:
    for path in _workflow_paths():
        workflow = _workflow(path)
        jobs = workflow["jobs"]
        assert isinstance(jobs, dict)

        if path == CI_WORKFLOW_PATH:
            assert workflow["permissions"] == {"contents": "read"}
        elif path == CODEQL_WORKFLOW_PATH:
            assert workflow["permissions"] == {}

        for job_id, job in jobs.items():
            assert isinstance(job_id, str)
            assert isinstance(job, dict)
            permissions = job.get("permissions", {})
            assert isinstance(permissions, dict)
            if path == CODEQL_WORKFLOW_PATH and job_id == "codeql":
                assert permissions == {
                    "actions": "read",
                    "contents": "read",
                    "security-events": "write",
                }
            else:
                assert "security-events" not in permissions


def test_required_workflows_do_not_use_path_filters() -> None:
    for path in _workflow_paths():
        assert _workflow_contains_path_filters(_triggers(_workflow(path))) is False


def test_codeql_workflow_contract() -> None:
    workflow = _workflow(CODEQL_WORKFLOW_PATH)
    triggers = _triggers(workflow)
    codeql = _job_named(workflow, "codeql")
    init_steps = _step_uses(codeql, "github/codeql-action/init")
    analyze_steps = _step_uses(codeql, "github/codeql-action/analyze")

    assert workflow["name"] == "CodeQL"
    assert triggers["pull_request"]["branches"] == ["main"]
    assert triggers["push"]["branches"] == ["main"]
    assert "workflow_dispatch" in triggers
    assert len(triggers["schedule"]) == 1
    cron_fields = triggers["schedule"][0]["cron"].split()
    assert len(cron_fields) == 5
    assert cron_fields[4] != "*"

    assert set(workflow["jobs"]) == {"codeql"}
    assert codeql["name"] == "codeql"
    assert codeql["runs-on"] == "ubuntu-24.04"

    assert len(init_steps) == 1
    assert len(analyze_steps) == 1
    assert init_steps[0]["with"]["languages"] == "python"
    assert init_steps[0]["with"]["build-mode"] == "none"
    assert init_steps[0]["with"]["queries"] == "security-extended"
    assert analyze_steps[0]["with"]["category"] == "/language:python"


def test_ci_workflow_security_and_action_pinning_invariants() -> None:
    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = _workflow()
    uses_steps = _uses_steps(CI_WORKFLOW_PATH)

    assert workflow["permissions"] == {"contents": "read"}
    assert "pull_request_target" not in workflow_text
    assert workflow["concurrency"]["cancel-in-progress"] is True

    assert uses_steps
    for step in uses_steps:
        uses = step["uses"]
        assert isinstance(uses, str)
        ref = PINNED_ACTION_REF.fullmatch(uses)
        assert ref is not None
        assert ref.group(1) in {
            "actions/checkout",
            "actions/setup-python",
            "actions/upload-artifact",
        }
        if ref.group(1) == "actions/checkout":
            assert step.get("with", {}).get("persist-credentials") is False


def test_ci_workflow_defines_required_checks_and_python_matrix() -> None:
    jobs = _workflow()["jobs"]
    matrix = jobs["tests"]["strategy"]["matrix"]["python-version"]

    assert set(jobs) == {"tests", "quality", "package"}
    assert jobs["tests"]["name"] == "tests (python ${{ matrix.python-version }})"
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
