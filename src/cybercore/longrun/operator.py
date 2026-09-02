from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
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
    profile_path: Path
    mission_path: Path


def _resolve(repo: Path, path: Path) -> Path:
    expanded = path.expanduser()
    return expanded.resolve() if expanded.is_absolute() else (repo / expanded).resolve()


def _within_repo(path: Path, repo: Path) -> bool:
    try:
        path.relative_to(repo)
    except ValueError:
        return False
    return True


def load_operator_context(
    repo: Path,
    *,
    profile: Path,
    mission: Path,
    state_db: Path | None = None,
    require_existing_state: bool = False,
) -> LongRunOperatorContext:
    repo = repo.expanduser().resolve()
    profile_path = _resolve(repo, profile)
    mission_path = _resolve(repo, mission)
    manifest = load_manifest(profile_path, mission_path)
    db_path = (
        _resolve(repo, state_db)
        if state_db is not None
        else (repo / ".cybercore" / "longrun" / f"{manifest.run_id}.sqlite").resolve()
    )
    if not _within_repo(db_path, repo):
        raise ValueError("LongRun state database must remain inside the repository sandbox")
    return LongRunOperatorContext(
        repo=repo,
        manifest=manifest,
        store=LongRunStateStore(db_path, create=not require_existing_state),
        state_db=db_path,
        profile_path=profile_path,
        mission_path=mission_path,
    )


def _deterministic_targets(context: LongRunOperatorContext) -> tuple[Path, ...]:
    candidates = {
        context.repo / "pyproject.toml",
        context.repo / "README.md",
        context.repo / "configs" / "longrun" / "marathon16.yaml",
        context.repo / "docs" / "architecture" / "ADR-0007-durable-longrun-runtime.md",
        context.profile_path,
        context.mission_path,
    }
    for pattern in (
        "src/cybercore/longrun/*.py",
        "tests/test_longrun*.py",
    ):
        candidates.update(context.repo.glob(pattern))

    targets: list[Path] = []
    for path in sorted(candidates):
        if not _within_repo(path, context.repo):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        if path.stat().st_size > 1_000_000:
            continue
        targets.append(path)
    if not targets:
        raise RuntimeError("deterministic LongRun harness found no safe repository read targets")
    return tuple(targets)


def deterministic_engine(context: LongRunOperatorContext) -> LongRunEngine:
    targets = _deterministic_targets(context)
    fingerprints = {
        f"repo-read:{path.relative_to(context.repo).as_posix()}": path for path in targets
    }

    def planner(state: RunState) -> StepProposal:
        if state.step_index >= len(targets):
            return StepProposal(
                fingerprint="repo-read:targets-exhausted",
                expected_quality_gain=0.0,
                expected_information_gain=0.0,
                cost=0.01,
                risk=0.01,
                duplication_probability=1.0,
                effect="read",
            )
        path = targets[state.step_index]
        fingerprint = f"repo-read:{path.relative_to(context.repo).as_posix()}"
        return StepProposal(
            fingerprint=fingerprint,
            expected_quality_gain=0.5,
            expected_information_gain=0.5,
            cost=0.02,
            risk=0.01,
            duplication_probability=0.0,
            effect="read",
        )

    def executor(proposal: StepProposal) -> StepResult:
        target = fingerprints.get(proposal.fingerprint)
        if target is None:
            raise RuntimeError("deterministic harness proposal has no safe read target")
        data = target.read_bytes()
        return StepResult(
            success=True,
            evaluator_score=0.0,
            evidence={
                "harness": "deterministic-repo-integrity",
                "path": target.relative_to(context.repo).as_posix(),
                "sha256": sha256(data).hexdigest(),
                "size": len(data),
                "independent_evaluation": False,
            },
        )

    return LongRunEngine(
        context.manifest,
        context.store,
        planner=planner,
        executor=executor,
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
