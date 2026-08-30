from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StepProposal:
    fingerprint: str
    expected_quality_gain: float
    expected_information_gain: float
    cost: float
    risk: float
    duplication_probability: float
    effect: str

    @property
    def value(self) -> float:
        return (
            self.expected_quality_gain
            + self.expected_information_gain
            - self.cost
            - self.risk
            - self.duplication_probability
        )


def authorize_step(
    proposal: StepProposal,
    *,
    allowed_effects: tuple[str, ...],
    prohibited_effects: tuple[str, ...],
) -> tuple[bool, str]:
    if proposal.effect in prohibited_effects:
        return False, "effect explicitly prohibited"
    if proposal.effect not in allowed_effects:
        return False, "effect not allowlisted"
    if proposal.value <= 0:
        return False, "non-positive expected value"
    return True, "authorized"
