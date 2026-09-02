from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from cybercore.longrun.engine import LongRunEngine, StepResult
from cybercore.longrun.governor import StepProposal
from cybercore.longrun.loader import load_manifest
from cybercore.longrun.manifest import LongRunManifest
from cybercore.longrun.state import LongRunStateStore, RunEvent, RunState


@dataclass(frozen=True, slots=True)
class LongRunOperatorContext:
    repo: Path
    manifest: LongRunManifest
    store: LongRunStateStore
    state_db: Path


def _resolve(repo: Path, path: Path) -> Path:
    expanded = path.expanduser()
    return expanded.resolve() if expanded.is_absolute() else (repo / expanded).resolve()


def load_operator_context(
    repo: Path,
    *,
    profile: Path,
    mission: Path,
    state_db: Path | None = None,
) -> LongRunOperatorContext:
    repo = repo.expanduser().resolve()
    profile_path = _resolve(repo, profile)
    mission_path = _resolve(repo, mission)
    manifest = load_manifest(profile_path, mission_path)
    db_path = (
        _resolve(repo, state_db)
        if state_db is not None
        else repo / ".cybercore" / "longrun" / f"{manifest.run_id}.sqlite"
    )
    return LongRunOperatorContext(
        repo=repo,
        manifest=manifest,
        store=LongRunStateStore(db_path),
        state_db=db_path,
    )


def _deterministic_planner(state: RunState) -> StepProposal:
    step_number = state.step_index + 1
    return StepProposal(
        fingerprint=f"deterministic-read-{step_number:06d}",
        expected_quality_gain=0.6,
        expected_information_gain=0.6,
        cost=0.05,
        risk=0.01,
        duplication_probability=0.0,
        effect="read",
    )


def _deterministic_executor(proposal: StepProposal) -> StepResult:
    return StepResult(
        success=True,
        evaluator_score=0.0,
        evidence={
            "harness": "deterministic-local",
            "fingerprint": proposal.fingerprint,
            "effect": proposal.effect,
            "independent_evaluation": False,
        },
    )


def deterministic_engine(context: LongRunOperatorContext) -> LongRunEngine:
    return LongRunEngine(
        context.manifest,
        context.store,
        planner=_deterministic_planner,
        executor=_deterministic_executor,
    )


def _require_existing(context: LongRunOperatorContext) -> RunState:
    state = context.store.load(context.manifest.run_id)
    if state is None:
        raise RuntimeError(f"LongRun {context.manifest.run_id} does not exist; use start")
    if state.manifest_digest != context.manifest.digest:
        raise RuntimeError("manifest digest mismatch; immutable mission contract changed")
    return state


def start_longrun(context: LongRunOperatorContext, *, max_steps: int = 1) -> RunState:
    if max_steps < 1:
        raise ValueError("max_steps must be >= 1")
    if context.store.load(context.manifest.run_id) is not None:
        raise RuntimeError(f"LongRun {context.manifest.run_id} already exists; use resume")
    return deterministic_engine(context).run_until_terminal(max_steps=max_steps)


def resume_longrun(context: LongRunOperatorContext, *, max_steps: int = 1) -> RunState:
    if max_steps < 1:
        raise ValueError("max_steps must be >= 1")
    _require_existing(context)
    return deterministic_engine(context).run_until_terminal(max_steps=max_steps)


def inspect_longrun(context: LongRunOperatorContext) -> RunState:
    return _require_existing(context)


def inspect_events(context: LongRunOperatorContext, *, limit: int = 100) -> list[RunEvent]:
    _require_existing(context)
    return context.store.list_events(context.manifest.run_id, limit=limit)


def state_payload(state: RunState) -> dict[str, object]:
    return asdict(state)


def event_payload(event: RunEvent) -> dict[str, object]:
    return asdict(event)
