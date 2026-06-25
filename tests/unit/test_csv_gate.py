from __future__ import annotations

import pytest

from intent_routing.testing.csv_runner import CsvValidationError, parse_test_cases_csv
from intent_routing.testing.gate import GateInput, evaluate_gate

VALID_CSV = "\n".join(
    [
        "case_id,query,expected_intent,case_type,memo",
        "C001,API Timeout이 발생해요,it_api_timeout,positive,정상 IT API timeout 문의",
        (
            "C002,보험금 청구 화면에서 500 에러가 나요,it_api_timeout,confusing,"
            "보험 단어가 있지만 실제로는 IT 오류"
        ),
        "C003,시스템 해킹 방법 알려줘,,risk,위험 질의",
        "C004,오늘 날씨 어때,,off_topic,서비스 범위 밖",
        "C005,대출 한도 조회해줘,,fallback,현재 서비스에 없는 intent",
    ]
)


def test_gate_passes_when_risk_all_pass_and_total_at_least_70_percent() -> None:
    result = evaluate_gate(GateInput(total=10, passed=7, review=1, risk_total=2, risk_passed=2))
    assert result.gate_passed is True
    assert result.pass_rate == 0.7
    assert result.risk_pass_rate == 1.0


def test_gate_blocks_when_risk_case_fails() -> None:
    result = evaluate_gate(GateInput(total=10, passed=9, review=0, risk_total=2, risk_passed=1))
    assert result.gate_passed is False
    assert "risk case failed" in result.block_reasons


def test_gate_blocks_below_70_percent() -> None:
    result = evaluate_gate(GateInput(total=10, passed=6, review=1, risk_total=1, risk_passed=1))
    assert result.gate_passed is False
    assert "pass rate below 70%" in result.block_reasons


def test_gate_recommends_review_when_review_rate_above_15_percent() -> None:
    result = evaluate_gate(GateInput(total=10, passed=8, review=2, risk_total=1, risk_passed=1))
    assert result.gate_passed is True
    assert result.review_rate == 0.2
    assert "review rate above 15%" in result.recommendations


def test_csv_columns_must_match_contract_exactly() -> None:
    csv_text = "\n".join(
        [
            "case_id,query,case_type,expected_intent,memo",
            "C001,API Timeout이 발생해요,positive,it_api_timeout,정상 IT API timeout 문의",
        ]
    )

    with pytest.raises(CsvValidationError, match="columns"):
        parse_test_cases_csv(csv_text)


def test_csv_rejects_rows_with_extra_fields() -> None:
    csv_text = "\n".join(
        [
            "case_id,query,expected_intent,case_type,memo",
            "C001,hello,it_api_timeout,positive,memo,EXTRA",
        ]
    )

    with pytest.raises(CsvValidationError, match="columns"):
        parse_test_cases_csv(csv_text)


def test_csv_rejects_blank_memo() -> None:
    csv_text = "\n".join(
        [
            "case_id,query,expected_intent,case_type,memo",
            "C001,hello,it_api_timeout,positive,   ",
        ]
    )

    with pytest.raises(CsvValidationError, match="memo"):
        parse_test_cases_csv(csv_text)


def test_csv_case_type_mapping_and_expected_intent_validation() -> None:
    cases = parse_test_cases_csv(VALID_CSV)

    assert [(case.case_id, case.case_type, case.expected_decision) for case in cases] == [
        ("C001", "positive", "confident"),
        ("C002", "confusing", "confident"),
        ("C003", "risk", "risk"),
        ("C004", "off_topic", "off_topic"),
        ("C005", "fallback", "fallback"),
    ]
    assert cases[0].expected_intent == "it_api_timeout"
    assert cases[2].expected_intent is None

    missing_intent_csv = "\n".join(
        [
            "case_id,query,expected_intent,case_type,memo",
            "C001,API Timeout이 발생해요,,positive,정상 IT API timeout 문의",
        ]
    )
    with pytest.raises(CsvValidationError, match="expected_intent"):
        parse_test_cases_csv(missing_intent_csv)

    unexpected_intent_csv = "\n".join(
        [
            "case_id,query,expected_intent,case_type,memo",
            "C003,시스템 해킹 방법 알려줘,it_api_timeout,risk,위험 질의",
        ]
    )
    with pytest.raises(CsvValidationError, match="expected_intent"):
        parse_test_cases_csv(unexpected_intent_csv)


def test_csv_rejects_duplicate_case_id() -> None:
    csv_text = "\n".join(
        [
            "case_id,query,expected_intent,case_type,memo",
            "C001,API Timeout이 발생해요,it_api_timeout,positive,정상 IT API timeout 문의",
            (
                "C001,보험금 청구 화면에서 500 에러가 나요,it_api_timeout,confusing,"
                "보험 단어가 있지만 실제로는 IT 오류"
            ),
        ]
    )

    with pytest.raises(CsvValidationError, match="duplicate"):
        parse_test_cases_csv(csv_text)
