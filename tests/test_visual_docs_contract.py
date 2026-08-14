from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DIAGRAMS = (
    "evidence-lifecycle",
    "work-block-lifecycle",
    "security-merge-gate",
    "architecture-overview",
    "public-private-overlay",
)


def test_visual_documentation_contract_is_complete_and_local() -> None:
    visual_root = REPOSITORY_ROOT / "docs" / "visual"
    for diagram in DIAGRAMS:
        assert (visual_root / "diagrams" / f"{diagram}.mmd").is_file()
        generated = visual_root / "generated" / f"{diagram}.svg"
        assert generated.is_file()
        assert generated.stat().st_size > 0
        content = generated.read_text(encoding="utf-8")
        assert 'href="http://' not in content
        assert 'href="https://' not in content
        assert 'src="http://' not in content
        assert 'src="https://' not in content

    for name in ("index.html", "app.js", "styles.css"):
        source = visual_root / "learn" / name
        assert source.is_file()
        text = source.read_text(encoding="utf-8")
        assert "http://" not in text
        assert "https://" not in text


def test_visual_documentation_scripts_use_safe_shell_behavior() -> None:
    for name in (
        "render_visual_docs.sh",
        "capture_learn_demo.sh",
        "verify_visual_docs.sh",
    ):
        script = REPOSITORY_ROOT / "scripts" / name
        lines = script.read_text(encoding="utf-8").splitlines()
        assert lines[:2] == ["#!/usr/bin/env bash", "set -euo pipefail"]
