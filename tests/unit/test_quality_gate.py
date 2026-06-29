import pytest

from intent_routing.ops.quality_gate import evaluate_required_preset_gate


RUNS = {
    "strict": {"gate_passed": False, "pass_rate": 0.5, "risk_pass_rate": 1.0},
    "balanced": {"gate_passed": True, "pass_rate": 0.8, "risk_pass_rate": 1.0},
    "exploratory": {"gate_passed": True, "pass_rate": 0.7, "risk_pass_rate": 1.0},
}


def test_required_preset_gate_passes_when_balanced_passes() -> None:
    result = evaluate_required_preset_gate(RUNS, required_preset="balanced")

    assert result.required_preset == "balanced"
    assert result.passed is True
    assert result.block_reasons == []


def test_required_preset_gate_blocks_when_balanced_fails() -> None:
    runs = {preset: dict(payload) for preset, payload in RUNS.items()}
    runs["balanced"]["gate_passed"] = False
    runs["balanced"]["pass_rate"] = 0.6

    result = evaluate_required_preset_gate(runs, required_preset="balanced")

    assert result.passed is False
    assert "required preset balanced failed CSV gate" in result.block_reasons
    assert "balanced pass_rate=60.0%" in result.block_reasons


def test_required_preset_gate_rejects_missing_preset() -> None:
    with pytest.raises(ValueError, match="missing required preset"):
        evaluate_required_preset_gate({"strict": RUNS["strict"]}, required_preset="balanced")
