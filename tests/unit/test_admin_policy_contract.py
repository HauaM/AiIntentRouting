from __future__ import annotations

import pytest
from pydantic import ValidationError

from intent_routing.api.admin import PolicyVersionCreateRequest, TestRunCreateRequest


def policy_payload(**overrides: object) -> dict[str, object]:
    return {
        "threshold_preset": "balanced",
        "clarify_margin": 0.08,
        "min_candidate_score": 0.55,
        "fallback_score": 0.45,
        "risk_policy": {"enabled": True},
        "off_topic_policy": {"enabled": True, "keywords": [], "message": ""},
        **overrides,
    }


def test_policy_request_accepts_custom_threshold() -> None:
    request = PolicyVersionCreateRequest.model_validate(
        policy_payload(threshold_preset="custom", threshold_value=0.72)
    )

    assert request.threshold_preset == "custom"
    assert request.threshold_value == pytest.approx(0.72)


@pytest.mark.parametrize(
    "payload",
    [
        policy_payload(threshold_preset="custom"),
        policy_payload(threshold_value=0.72),
        policy_payload(
            threshold_preset="custom",
            threshold_value=0.5,
            min_candidate_score=0.55,
        ),
    ],
)
def test_policy_request_rejects_invalid_threshold_contract(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        PolicyVersionCreateRequest.model_validate(payload)


def test_test_run_request_accepts_legacy_threshold_preset() -> None:
    request = TestRunCreateRequest.model_validate(
        {
            "policy_version": "pol-1",
            "intent_catalog_version": "cat-1",
            "threshold_preset": "exploratory",
            "source_filename": "cases.csv",
            "csv_text": "case_id,query,expected_intent,case_type,memo",
        }
    )

    assert request.threshold_preset == "exploratory"
