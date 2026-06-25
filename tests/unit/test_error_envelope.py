import pytest
from pydantic import ValidationError

from intent_routing.api.errors import ErrorEnvelope, ErrorInfo
from intent_routing.domain.enums import Decision, ErrorCode, ThresholdPreset
from intent_routing.domain.schemas import (
    ClarifyCandidate,
    ClarifyPayload,
    FallbackPolicy,
    RuntimeResponse,
)


def test_decision_enum_contains_no_internal_error_value() -> None:
    assert {item.value for item in Decision} == {
        "confident",
        "clarify",
        "fallback",
        "off_topic",
        "risk",
        "unauthorized",
    }


def test_threshold_values_are_prd_presets() -> None:
    assert ThresholdPreset.strict.threshold == 1.0
    assert ThresholdPreset.balanced.threshold == 0.8
    assert ThresholdPreset.exploratory.threshold == 0.6


def test_error_envelope_has_trace_and_no_decision() -> None:
    envelope = ErrorEnvelope(
        trace_id="irt-20260625-000081",
        request_id="dify-run-1",
        error=ErrorInfo(
            code=ErrorCode.VECTOR_STORE_UNAVAILABLE,
            message="일시적으로 의도 분류를 처리할 수 없습니다.",
            retryable=True,
            category="dependency_failure",
            layer="semantic_layer",
            support_message="pgvector 조회 중 timeout이 발생했습니다.",
            safe_detail="vector search timeout",
            fallback_policy=FallbackPolicy(
                type="client_fallback",
                recommended_action="show_fixed_message_or_handoff",
            ),
        ),
        release_version="rel-it-helpdesk-20260625-001",
    )

    data = envelope.model_dump(mode="json", exclude_none=True)
    assert data["status"] == "error"
    assert data["trace_id"] == "irt-20260625-000081"
    assert data["request_id"] == "dify-run-1"
    assert data["release_version"] == "rel-it-helpdesk-20260625-001"
    assert "decision" not in data
    assert data["error"]["code"] == "VECTOR_STORE_UNAVAILABLE"


def test_error_envelope_rejects_top_level_decision() -> None:
    with pytest.raises(ValidationError):
        ErrorEnvelope.model_validate(
            {
                "trace_id": "irt-20260625-000081",
                "request_id": "dify-run-1",
                "decision": Decision.fallback,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": "일시적으로 의도 분류를 처리할 수 없습니다.",
                    "retryable": True,
                },
                "release_version": "rel-it-helpdesk-20260625-001",
            }
        )


def test_runtime_response_serializes_prd_clarify_shape() -> None:
    response = RuntimeResponse(
        trace_id="irt-20260625-000082",
        request_id="dify-run-2",
        decision=Decision.clarify,
        domain="it_helpdesk",
        route_key="it_helpdesk.password_reset",
        clarify_question="어떤 계정의 비밀번호를 재설정할까요?",
        clarify=ClarifyPayload(
            reason="multiple_candidate_intents",
            message="비슷한 의도가 여러 개 발견되었습니다.",
            candidates=[
                ClarifyCandidate(
                    intent_id="intent-password-reset",
                    display_name="Password reset",
                    route_key="it_helpdesk.password_reset",
                    confidence=0.74,
                )
            ],
        ),
        fallback_policy=FallbackPolicy(
            type="client_fallback",
            retryable=True,
            recommended_action="ask_clarifying_question",
        ),
        release_version="rel-it-helpdesk-20260625-001",
    )

    data = response.model_dump(mode="json", exclude_none=True)
    assert data["decision"] == "clarify"
    assert data["domain"] == "it_helpdesk"
    assert data["route_key"] == "it_helpdesk.password_reset"
    assert data["clarify_question"] == "어떤 계정의 비밀번호를 재설정할까요?"
    assert data["clarify"]["reason"] == "multiple_candidate_intents"
    assert data["clarify"]["candidates"][0]["display_name"] == "Password reset"
    assert data["clarify"]["candidates"][0]["route_key"] == "it_helpdesk.password_reset"
    assert data["fallback_policy"]["retryable"] is True
