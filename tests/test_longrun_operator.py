from __future__ import annotations

import json
from pathlib import Path

import pytest

from cybercore.entrypoint import main
from cybercore.longrun.loader import load_manifest
from cybercore.longrun.operator import (
    inspect_events,
    load_operator_context,
    resume_longrun,
    start_longrun,
)


_PROFILE = """\
version: 0
profile: test
minimum_wall_seconds: 0
maximum_wall_seconds: 3600
evaluator_threshold: 0.95
checkpoint_every_steps: 1
max_consecutive_failures: 3
max_duplicate_steps: 2
allowed_effects:
  - read
  - sandbox_write
prohibited_effects:
  - production_write
  - credential_mutation
  - billing_mutation
  - permission_mutation
policy:
  evidence_required: true
  independent_evaluation_required: true
  immutable_mission_required: true
  fail_closed_on_unknown_effect: true
"""

_MISSION = """\
version: 0
run_id: operator-test
objective: prove deterministic operator resume behavior
metadata:
  benchmark: TEST-001
"""


def _contract(tmp_path: Path) -> tuple[Path, Path]:
    profile = tmp_path / "profile.yaml"
    mission = tmp_path / "mission.yaml"
    profile.write_text(_PROFILE, encoding="utf-8")
    mission.write_text(_MISSION, encoding="utf-8")
    return profile, mission


def test_loader_composes_profile_and_mission_into_immutable_manifest(tmp_path: Path):
    profile, mission = _contract(tmp_path)
    manifest = load_manifest(profile, mission)

    assert manifest.run_id == "operator-test"
    assert manifest.objective == "prove deterministic operator resume behavior"
    assert manifest.allowed_effects == ("read", "sandbox_write")
    assert manifest.metadata == {"benchmark": "TEST-001", "longrun_profile": "test"}
    assert manifest.digest == load_manifest(profile, mission).digest


def test_loader_rejects_disabled_required_policy(tmp_path: Path):
    profile, mission = _contract(tmp_path)
    profile.write_text(
        _PROFILE.replace("independent_evaluation_required: true", "independent_evaluation_required: false"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="independent_evaluation_required"):
        load_manifest(profile, mission)


def test_operator_start_resume_and_event_ledger_survive_reconstruction(tmp_path: Path):
    profile, mission = _contract(tmp_path)
    context = load_operator_context(tmp_path, profile=profile, mission=mission)

    first = start_longrun(context, max_steps=1)
    assert first.status == "RUNNING"
    assert first.step_index == 1
    assert first.evaluator_score == 0.0
    assert context.state_db == tmp_path / ".cybercore" / "longrun" / "operator-test.sqlite"

    reconstructed = load_operator_context(tmp_path, profile=profile, mission=mission)
    second = resume_longrun(reconstructed, max_steps=2)
    assert second.status == "RUNNING"
    assert second.step_index == 3

    events = inspect_events(reconstructed)
    assert [event.kind for event in events] == ["RUN_STARTED", "STEP_RESULT", "STEP_RESULT", "STEP_RESULT"]
    assert all(
        event.payload.get("evidence", {}).get("independent_evaluation") is False
        for event in events
        if event.kind == "STEP_RESULT"
    )


def test_operator_start_refuses_existing_run(tmp_path: Path):
    profile, mission = _contract(tmp_path)
    context = load_operator_context(tmp_path, profile=profile, mission=mission)
    start_longrun(context)

    with pytest.raises(RuntimeError, match="already exists"):
        start_longrun(context)


def test_cli_longrun_start_status_resume_and_events(tmp_path: Path, capsys):
    profile, mission = _contract(tmp_path)
    common = [
        "--repo",
        str(tmp_path),
        "--json",
        "longrun",
    ]
    contract = ["--profile", str(profile), "--mission", str(mission)]

    assert main(common + ["start", *contract, "--max-steps", "1"]) == 0
    started = json.loads(capsys.readouterr().out)
    assert started["step_index"] == 1
    assert started["status"] == "RUNNING"

    assert main(common + ["status", *contract]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["step_index"] == 1

    assert main(common + ["resume", *contract, "--max-steps", "1"]) == 0
    resumed = json.loads(capsys.readouterr().out)
    assert resumed["step_index"] == 2

    assert main(common + ["events", *contract, "--limit", "10"]) == 0
    events = json.loads(capsys.readouterr().out)
    assert [event["kind"] for event in events] == ["RUN_STARTED", "STEP_RESULT", "STEP_RESULT"]
