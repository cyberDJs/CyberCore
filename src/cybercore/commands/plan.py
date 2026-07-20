from __future__ import annotations

from cybercore.discovery import DiscoveryEngine
from cybercore.planner import PlannedAction, Planner
from cybercore.policy import PolicyEngine
from cybercore.registry import Registry
from cybercore.risk import RiskEngine


def run_plan(repo) -> tuple[PlannedAction, ...]:
    registry = Registry.load(repo)
    findings = DiscoveryEngine(registry).run()
    decisions = PolicyEngine().evaluate(findings)
    assessments = RiskEngine().assess(findings, decisions)
    return Planner().plan(findings, decisions, assessments)


def plan_lines(actions: tuple[PlannedAction, ...]) -> list[str]:
    lines = [f"PLANNED={len(actions)}"]
    for action in actions:
        lines.append