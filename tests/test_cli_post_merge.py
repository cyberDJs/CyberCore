from __future__ import annotations

import json
from pathlib import Path

from cybercore import cli
from cybercore.post_merge import MergedPullRequest, PostMergeTransitionPreview


def _preview() -> PostMergeTransitionPreview:
    return PostMergeTransitionPreview(
        pull_request=MergedPullRequest(
            number=22,
            repository="cyberDJs/CyberCore",
            base_branch="main",
            head_branch="feat/idempotent-canonical-memory",
            head_sha="5f16ec7156ce49cc4f6eedd103170ccf37c3ccb8",
            merge_commit="1e174e9180e64c3bfc5c70fa52d5c7e399ead9eb",
            title="feat: make canonical memory idempotent and rollback-safe",
        ),
        main_commit="1e174e9180e64c3bfc5c70fa52d5c7e399ead9eb",
    )


def test_post_merge_cli_renders_read_only_preview(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    calls: list[tuple[Path, int, str, str | None]] = []

    def fake_plan(
        repo: Path,
        pull_request_number: int,
        *,
        stable_branch: str,
        expected_head_sha: str | None,
    ) -> PostMergeTransitionPreview:
        calls.append((repo, pull_request_number, stable_branch, expected_head_sha))
        return _preview()

    monkeypatch.setattr(cli, "plan_post_merge_transition", fake_plan)

    result = cli.main(
        [
            "--repo",
            str(tmp_path),
            "post-merge",
            "22",
            "--expected-head-sha",
            "5f16ec7156ce49cc4f6eedd103170ccf37c3ccb8",
        ]
    )

    assert result == 0
    assert calls == [
        (
            tmp_path.resolve(),
            22,
            "main",
            "5f16ec7156ce49cc4f6eedd103170ccf37c3ccb8",
        )
    ]
    output = capsys.readouterr().out
    assert "POST-MERGE TRANSITION PREVIEW" in output
    assert "Pull request: #22" in output
    assert "Mutation: none" in output


def test_post_merge_cli_supports_json_output(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(cli, "plan_post_merge_transition", lambda *args, **kwargs: _preview())

    result = cli.main(["--repo", str(tmp_path), "--json", "post-merge", "22"])

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pull_request"] == 22
    assert payload["merge_commit"] == "1e174e9180e64c3bfc5c70fa52d5c7e399ead9eb"
    assert payload["mutation"] == "none"
