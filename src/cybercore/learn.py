from __future__ import annotations

from cybercore.presentation import banner, make_console, step


def run_lesson(*, lesson: str = "evidence", interactive: bool = True, no_color: bool = False) -> int:
    if lesson != "evidence":
        raise ValueError(f"Unknown lesson: {lesson}")

    console = make_console(no_color=no_color)
    banner(console, "Learn — Evidence First")
    sections = [
        ("Observation", "A raw fact collected from a system or provider."),
        ("Evidence", "An observation with source, time, scope, and confidence."),
        ("Context", "Relationships that explain what the evidence means."),
        ("Decision", "A proposed action that can be reviewed before execution."),
    ]
    for index, (title, detail) in enumerate(sections, start=1):
        step(console, index, title, detail)
        if interactive:
            input("Press ENTER to continue...")

    console.print(
        "\n[cc.ok]LESSON COMPLETE[/cc.ok] "
        "CyberCore does not treat assumptions as evidence."
    )
    return 0
