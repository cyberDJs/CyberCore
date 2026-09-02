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
from cybercore.longrun.state import LongRunStateStore, RunState


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


def _state(run_id: str) -> RunState:
    return RunState(
        run_id=run_id,
        manifest_digest=f"digest-{run_id}",
        status="RUNNING",
        step_index=0,
        consecutive_failures=0,
        last_step_fingerprint=None,
        duplicate_count=0,
        evaluator_score=0.0,
        started_at=0.0,
        updated_at=0.0,
    )


def test_loader_composes_profile_and_mission_into_immutable_manifest(tmp_path: Path):
    profile, mission = _contract(tmp_path)
    manifest = load_manifest(profile, mission)

    assert manifest.run_id == "operator-test"
    assert manifest.objective == "prove deterministic operator resume behavior"
    assert manifest.allowed_effects == ("read", "sandbox_write")
    assert manifest.evidence_required is True
    assert manifest.independent_evaluation_required is True
    assert manifest.metadata == {"benchmark": "TEST-001", "longrun_profile": "test"}
    assert manifest.digest == load_manifest(profile, mission).digest


def test_loader_rejects_disabled_required_policy(tmp_path: Path):
    profile, mission = _contract(tmp_path)
    profile.write_text(
        _PROFILE.replace(
            "independent_evaluation_required: true", "independent_evaluation_required: false"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="independent_evaluation_required"):
        load_manifest(profile, mission)


def test_loader_rejects_run_identifier_path_traversal(tmp_path: Path):
    profile, mission = _contract(tmp_path)
    mission.write_text(_MISSION.replace("operator-test", "../../../escape"), encoding="utf-8")

    with pytest.raises(ValueError, match="mission.run_id"):
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
    second = resume_longrun(reconstructed, max_steps=1)
    assert second.status == "RUNNING"
    assert second.step_index == 2

    events = inspect_events(reconstructed)
    assert [event.kind for event in events] == ["RUN_STARTED", "STEP_RESULT", "STEP_RESULT"]
    step_events = [event for event in events if event.kind == "STEP_RESULT"]
    assert all(event.payload.get("evidence", {}).get("sha256") for event in step_events)
    for event in step_events:
        evaluation = event.payload["evaluation"]
        assert evaluation["evaluator_id"] == "cybercore.deterministic-repo-integrity-judge"
        assert evaluation["verdict"] == "FAIL"
        assert evaluation["score"] == 0.0
        assert evaluation["evidence_digest"] == event.payload["evidence_digest"]
        assert evaluation["evaluation_digest"]


def test_harness_blocks_instead_of_padding_after_useful_targets_are_exhausted(tmp_path: Path):
    profile, mission = _contract(tmp_path)
    context = load_operator_context(tmp_path, profile=profile, mission=mission)
    start_longrun(context, max_steps=2)

    blocked = resume_longrun(context, max_steps=1)

    assert blocked.status == "BLOCKED"
    assert blocked.step_index == 2
    events = inspect_events(context)
    assert events[-1].kind == "STEP_BLOCKED"
    assert events[-1].payload["reason"] == "non-positive expected value"


def test_operator_start_refuses_existing_run(tmp_path: Path):
    profile, mission = _contract(tmp_path)
    context = load_operator_context(tmp_path, profile=profile, mission=mission)
    start_longrun(context)

    with pytest.raises(RuntimeError, match="already exists"):
        start_longrun(context)


def test_operator_rejects_state_database_outside_repo_sandbox(tmp_path: Path):
    profile, mission = _contract(tmp_path)
    outside = tmp_path.parent / "outside.sqlite"

    with pytest.raises(ValueError, match="repository sandbox"):
        load_operator_context(tmp_path, profile=profile, mission=mission, state_db=outside)


def test_operator_rejects_default_state_path_through_external_symlink(tmp_path: Path):
    profile, mission = _contract(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / ".cybercore").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="repository sandbox"):
        load_operator_context(tmp_path, profile=profile, mission=mission)

    assert not (outside / "longrun" / "operator-test.sqlite").exists()


def test_open_existing_state_preserves_literal_uri_escape_path(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    literal_dir = repo / "%2e%2e"
    literal_dir.mkdir()
    literal_db = literal_dir / "run.sqlite"
    outside_db = tmp_path / "run.sqlite"

    literal_store = LongRunStateStore(literal_db)
    literal_store.create(_state("inside-literal"))
    outside_store = LongRunStateStore(outside_db)
    outside_store.create(_state("outside-decoded"))

    reopened = LongRunStateStore(literal_db, create=False)

    assert reopened.load("inside-literal") is not None
    assert reopened.load("outside-decoded") is None


def test_cli_status_for_missing_run_does_not_create_database(tmp_path: Path, capsys):
    profile, mission = _contract(tmp_path)
    state_db = tmp_path / ".cybercore" / "longrun" / "operator-test.sqlite"

    code = main(
        [
            "--repo",
            str(tmp_path),
            "longrun",
            "status",
            "--profile",
            str(profile),
            "--mission",
            str(mission),
        ]
    )

    assert code == 2
    assert not state_db.exists()
    assert "does not exist" in capsys.readouterr().err


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
    assert all(event.get("payload", {}).get("evaluation") for event in events[1:])
