from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cybercore import entrypoint
from cybercore.post_merge import MergedPullRequest, PostMergeTransitionPreview


@dataclass
class _StatePlan:
    written: bool = False

    def write(self) -> None:
        self.written = True


def _preview() -> PostMergeTransitionPreview:
    return PostMergeTransitionPreview(
        pull_request=MergedPullRequest(
            number=22,
            repository="cyberDJs/CyberCore",
            base_branch="main",
            head_branch="feat/idempotent-canonical-memory",
            head_sha="head-sha",
            merge_commit="merge-sha",
            title="Canonical memory",
        ),
        main_commit="main-sha",
    )


def _transition_args() -> list[str]:
    return [
        "--completed-artifact",
        "WB-0018",
        "--verification",
        "52_passed",
        "--next-artifact",
        "WB-0019",
        "--next-milestone",
        "Post-Merge State Transition v0.1",
        "--next-branch",
        "feat/post-merge-state-transition",
        "--next-action",
        "Implement transition runtime",
        "--completed-status",
        "idempotent_canonical_memory",
        "--next-status",
        "post_merge_state_transition",
        "--next-objective",
        "Create a controlled post-merge transition.",
        "--next-scope",
        "verify merged pull requests",
        "--next-task",
        "implement transition preview",
    ]


def _terminal_args() -> list[str]:
    return [
        "--completed-artifact",
        "WB-0018",
        "--verification",
        "52_passed",
        "--next-action",
        "Select the next bounded candidate explicitly.",
        "--next-task",
        "select the next bounded candidate explicitly",
        "--terminal",
    ]


def test_non_post_merge_commands_delegate_to_existing_cli(monkeypatch) -> None:
    received: list[str] = []

    def fake_main(arguments: list[str]) -> int:
        received.extend(arguments)
        return 7

    monkeypatch.setattr(entrypoint.cli, "main", fake_main)

    assert entrypoint.main(["status"]) == 7
    assert received == ["status"]


def test_post_merge_state_defaults_to_preview(monkeypatch, tmp_path: Path, capsys) -> None:
    plan = _StatePlan()
    monkeypatch.setattr(
        entrypoint.RuntimePaths,
        "discover",
        classmethod(lambda cls, repo=None: type("Paths", (), {"repo": tmp_path})()),
    )
    monkeypatch.setattr(entrypoint, "plan_post_merge_transition", lambda *a, **k: _preview())
    monkeypatch.setattr(entrypoint, "plan_post_merge_state_update", lambda *a, **k: plan)
    monkeypatch.setattr(entrypoint, "render_post_merge_preview", lambda preview: "REMOTE PREVIEW\n")
    monkeypatch.setattr(
        entrypoint, "render_post_merge_state_preview", lambda state: "STATE PREVIEW\n"
    )

    result = entrypoint.main(["post-merge", "22", *_transition_args()])

    assert result == 0
    assert plan.written is False
    assert capsys.readouterr().out == "REMOTE PREVIEW\nSTATE PREVIEW\n"


def test_post_merge_write_requires_explicit_complete_transition(capsys) -> None:
    result = entrypoint.main(["post-merge", "22", "--write"])

    assert result == 2
    assert "complete successor work block contract" in capsys.readouterr().err


def test_post_merge_write_applies_verified_plan(monkeypatch, tmp_path: Path, capsys) -> None:
    plan = _StatePlan()
    monkeypatch.setattr(
        entrypoint.RuntimePaths,
        "discover",
        classmethod(lambda cls, repo=None: type("Paths", (), {"repo": tmp_path})()),
    )
    monkeypatch.setattr(entrypoint, "plan_post_merge_transition", lambda *a, **k: _preview())
    monkeypatch.setattr(entrypoint, "plan_post_merge_state_update", lambda *a, **k: plan)
    monkeypatch.setattr(entrypoint, "render_post_merge_preview", lambda preview: "REMOTE PREVIEW\n")
    monkeypatch.setattr(
        entrypoint, "render_post_merge_state_preview", lambda state: "STATE PREVIEW\n"
    )

    result = entrypoint.main(["post-merge", "22", *_transition_args(), "--write"])

    assert result == 0
    assert plan.written is True
    assert capsys.readouterr().out.endswith("POST-MERGE STATE WRITTEN\n")


def test_post_merge_terminal_write_needs_no_successor(monkeypatch, tmp_path: Path, capsys) -> None:
    plan = _StatePlan()
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        entrypoint.RuntimePaths,
        "discover",
        classmethod(lambda cls, repo=None: type("Paths", (), {"repo": tmp_path})()),
    )
    monkeypatch.setattr(entrypoint, "plan_post_merge_transition", lambda *a, **k: _preview())

    def fake_state_plan(*args, **kwargs):
        captured.update(kwargs)
        return plan

    monkeypatch.setattr(entrypoint, "plan_post_merge_state_update", fake_state_plan)
    monkeypatch.setattr(entrypoint, "render_post_merge_preview", lambda preview: "REMOTE PREVIEW\n")
    monkeypatch.setattr(
        entrypoint, "render_post_merge_state_preview", lambda state: "STATE PREVIEW\n"
    )

    result = entrypoint.main(["post-merge", "22", *_terminal_args(), "--write"])

    assert result == 0
    assert plan.written is True
    assert captured["terminal"] is True
    assert "next_artifact" not in captured
    assert capsys.readouterr().out.endswith("POST-MERGE STATE WRITTEN\n")


def test_post_merge_terminal_rejects_successor_fields(capsys) -> None:
    result = entrypoint.main(
        [
            "post-merge",
            "22",
            *_terminal_args(),
            "--next-artifact",
            "WB-0019",
        ]
    )

    assert result == 2
    assert "cannot declare a successor" in capsys.readouterr().err


def test_post_merge_terminal_rejects_empty_required_values(capsys) -> None:
    for option in ("--completed-artifact", "--verification", "--next-action"):
        arguments = _terminal_args()
        arguments[arguments.index(option) + 1] = "   "

        result = entrypoint.main(["post-merge", "22", *arguments, "--write"])

        assert result == 2
        assert "contract values must be non-empty strings" in capsys.readouterr().err


def test_post_merge_terminal_rejects_empty_next_task(capsys) -> None:
    arguments = _terminal_args()
    arguments[arguments.index("--next-task") + 1] = ""

    result = entrypoint.main(["post-merge", "22", *arguments, "--write"])

    assert result == 2
    assert "--next-task values must be non-empty strings" in capsys.readouterr().err
