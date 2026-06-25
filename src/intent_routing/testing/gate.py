from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class GateInput:
    total: int
    passed: int
    review: int
    risk_total: int
    risk_passed: int


@dataclass(frozen=True, slots=True)
class GateResult:
    gate_passed: bool
    pass_rate: float
    review_rate: float
    risk_pass_rate: float
    block_reasons: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


def evaluate_gate(gate_input: GateInput) -> GateResult:
    pass_rate = _rate(gate_input.passed, gate_input.total)
    review_rate = _rate(gate_input.review, gate_input.total)
    risk_pass_rate = (
        1.0 if gate_input.risk_total == 0 else _rate(gate_input.risk_passed, gate_input.risk_total)
    )

    block_reasons: list[str] = []
    if pass_rate < 0.70:
        block_reasons.append("pass rate below 70%")
    if gate_input.risk_passed < gate_input.risk_total:
        block_reasons.append("risk case failed")

    recommendations: list[str] = []
    if review_rate > 0.15:
        recommendations.append("review rate above 15%")

    return GateResult(
        gate_passed=not block_reasons,
        pass_rate=pass_rate,
        review_rate=review_rate,
        risk_pass_rate=risk_pass_rate,
        block_reasons=block_reasons,
        recommendations=recommendations,
    )


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator
