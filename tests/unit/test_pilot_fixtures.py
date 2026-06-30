import csv
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from intent_routing.domain.enums import ThresholdPreset
from intent_routing.ops.pilot_catalog import load_pilot_cases, load_pilot_catalog
from intent_routing.testing.csv_runner import CsvValidationError

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "docs/pilot/it-helpdesk-pilot-catalog.json"
CASES = ROOT / "docs/pilot/it-helpdesk-pilot-cases.csv"
TIERED_CASES = {
    30: ROOT / "docs/pilot/it-helpdesk-pilot-cases-30.csv",
    50: ROOT / "docs/pilot/it-helpdesk-pilot-cases-50.csv",
    100: ROOT / "docs/pilot/it-helpdesk-pilot-cases-100.csv",
}
RISK_TYPES = {
    "abuse",
    "dangerous_command",
    "sensitive_data",
    "credential_secret",
    "unauthorized_access",
    "prompt_injection",
    "fraud_or_illegal",
}


def test_pilot_catalog_has_route_key_and_example_contract() -> None:
    catalog = load_pilot_catalog(CATALOG)

    assert catalog.service_id == "it-helpdesk-pilot"
    assert catalog.display_name == "IT Helpdesk Pilot"
    assert catalog.environment == "dev"
    assert catalog.threshold_preset == ThresholdPreset.balanced
    assert len(catalog.intents) == 3
    assert {intent.intent_id for intent in catalog.intents} == {
        "it_api_timeout",
        "it_password_reset",
        "it_vpn_access",
    }
    for intent in catalog.intents:
        assert intent.route_key.count(".") == 2
        assert intent.positive_examples
        assert intent.include_keywords


def test_pilot_catalog_keeps_bge_positive_calibration_examples() -> None:
    catalog = load_pilot_catalog(CATALOG)
    examples_by_intent = {
        intent.intent_id: set(intent.positive_examples) for intent in catalog.intents
    }

    assert {
        "업무 API timeout 알림이 반복됩니다",
        "배치 API 응답 지연을 확인해 주세요",
    } <= examples_by_intent["it_api_timeout"]
    assert {
        "사번 계정 잠금 때문에 포털 접속이 안 됩니다",
        "내 계정 잠금 해제 진행 상태를 알고 싶습니다",
    } <= examples_by_intent["it_password_reset"]
    assert {
        "외부 근무 중 VPN 접속 오류가 납니다",
        "신규 노트북에서 VPN 연결이 실패합니다",
    } <= examples_by_intent["it_vpn_access"]

    all_positive_examples = {
        example for examples in examples_by_intent.values() for example in examples
    }
    assert "문서 보관함 권한 신청 방법을 알려주세요" not in all_positive_examples


def test_pilot_catalog_rejects_unknown_threshold_preset(tmp_path: Path) -> None:
    catalog_data = json.loads(CATALOG.read_text(encoding="utf-8"))
    catalog_data["threshold_preset"] = "loose"
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(catalog_data, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_pilot_catalog(catalog_path)


def test_pilot_cases_cover_decision_families() -> None:
    cases = load_pilot_cases(CASES)

    assert {case.case_type for case in cases} >= {
        "positive",
        "clarify",
        "risk",
        "off_topic",
        "fallback",
    }
    assert sum(1 for case in cases if case.case_type == "risk") >= 1
    assert all("010-" not in case.query for case in cases)


def test_pilot_cases_reject_unknown_header_column(tmp_path: Path) -> None:
    csv_text = CASES.read_text(encoding="utf-8").replace(
        "case_id,query,expected_intent,case_type,memo",
        "case_id,query,expected_intent,case_type,notes",
        1,
    )
    cases_path = tmp_path / "cases.csv"
    cases_path.write_text(csv_text, encoding="utf-8")

    with pytest.raises(CsvValidationError):
        load_pilot_cases(cases_path)


def test_pilot_cases_reject_empty_file(tmp_path: Path) -> None:
    cases_path = tmp_path / "cases.csv"
    cases_path.write_text("", encoding="utf-8")

    with pytest.raises(CsvValidationError):
        load_pilot_cases(cases_path)


def test_raw_csv_header_matches_sprint_zero_runner_contract() -> None:
    with CASES.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        assert next(reader) == ["case_id", "query", "expected_intent", "case_type", "memo"]


def test_tiered_pilot_case_files_exist_and_default_alias_is_standard() -> None:
    for path in TIERED_CASES.values():
        assert path.exists()

    assert CASES.read_bytes() == TIERED_CASES[50].read_bytes()


def test_tiered_pilot_cases_have_required_coverage_and_no_obvious_secrets() -> None:
    for expected_count, path in TIERED_CASES.items():
        cases = load_pilot_cases(path)
        by_type = {
            case_type: 0
            for case_type in ("positive", "clarify", "risk", "off_topic", "fallback")
        }
        positive_intents: set[str] = set()
        risk_memos = " ".join(case.memo for case in cases if case.case_type == "risk")

        for case in cases:
            by_type[case.case_type] = by_type.get(case.case_type, 0) + 1
            if case.case_type == "positive" and case.expected_intent is not None:
                positive_intents.add(case.expected_intent)
            assert "010-" not in case.query
            assert "4111" not in case.query
            assert "1234-5678" not in case.query
            assert "irt_" not in case.query
            assert "sk-" not in case.query.casefold()

        assert len(cases) == expected_count
        assert by_type["positive"] >= expected_count * 0.4
        assert by_type["clarify"] >= expected_count * 0.1
        assert by_type["risk"] >= 7
        assert by_type["off_topic"] >= expected_count * 0.1
        assert by_type["fallback"] >= expected_count * 0.1
        assert positive_intents == {
            "it_api_timeout",
            "it_password_reset",
            "it_vpn_access",
        }
        for risk_type in RISK_TYPES:
            assert risk_type in risk_memos


def test_pilot_readme_documents_unregistered_work_fallback_protection() -> None:
    readme = (ROOT / "docs/pilot/README.md").read_text(encoding="utf-8")
    section = _markdown_section(readme, "## 미등록 업무 Fallback 보호")

    assert "case_type=fallback" in section
    assert "회의실 예약" in section
    assert "새 Intent와 positive example을 추가" in section
    assert "negative example을 추가" in section
    assert "case_type=fallback`으로 유지" in section
    for internal_term in (
        "scoring guard",
        "threshold",
        "embedding",
        "score",
        "scoring",
        "숫자 기준",
        "임계값",
    ):
        assert internal_term not in section


def _markdown_section(markdown: str, heading: str) -> str:
    start = markdown.index(heading)
    next_heading = markdown.find("\n## ", start + len(heading))
    if next_heading == -1:
        return markdown[start:]
    return markdown[start:next_heading]
