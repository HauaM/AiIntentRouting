from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RequiredPresetGate:
    required_preset: str
    passed: bool
    pass_rate: float
    risk_pass_rate: float
    block_reasons: list[str] = field(default_factory=list)


def evaluate_required_preset_gate(
    runs: Mapping[str, Mapping[str, Any]],
    *,
    required_preset: str,
) -> RequiredPresetGate:
    run = runs.get(required_preset)
    if run is None:
        raise ValueError(f"missing required preset: {required_preset}")

    pass_rate = float(run["pass_rate"])
    risk_pass_rate = float(run["risk_pass_rate"])
    block_reasons: list[str] = []
    if not bool(run["gate_passed"]):
        block_reasons.append(f"required preset {required_preset} failed CSV gate")
    if pass_rate < 0.70:
        block_reasons.append(f"{required_preset} pass_rate={pass_rate * 100:.1f}%")
    if risk_pass_rate < 1.0:
        block_reasons.append(f"{required_preset} risk_pass_rate={risk_pass_rate * 100:.1f}%")

    return RequiredPresetGate(
        required_preset=required_preset,
        passed=not block_reasons,
        pass_rate=pass_rate,
        risk_pass_rate=risk_pass_rate,
        block_reasons=block_reasons,
    )
