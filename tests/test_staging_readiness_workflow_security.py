from __future__ import annotations

from pathlib import Path
import tomllib

import yaml


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
WORKFLOW = ROOT / ".github" / "workflows" / "staging-readiness-gate.yml"


def test_staging_yaml_dependency_is_available_at_runtime() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]

    assert any(dependency.lower().startswith("pyyaml>=") for dependency in dependencies)


def test_readiness_dispatch_input_is_not_interpolated_into_shell_script() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    triggers = workflow.get("on") or workflow.get(True)
    assert isinstance(triggers, dict)
    assert "readiness" in triggers["workflow_dispatch"]["inputs"]

    job = workflow["jobs"]["validate-readiness-blocked"]
    validate_step = next(
        step for step in job["steps"] if step.get("name") == "Validate readiness gate is blocked"
    )

    assert validate_step["env"]["READINESS_PATH"] == "${{ inputs.readiness }}"
    run = validate_step["run"]
    assert "${{ inputs.readiness }}" not in run
    assert '--readiness "$READINESS_PATH"' in run
