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


def test_pilot_catalog_rejects_unknown_threshold_preset(tmp_path: Path) -> None:
    catalog_data = json.loads(CATALOG.read_text(encoding="utf-8"))
    catalog_data["threshold_preset"] = "loose"
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(catalog_data, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_pilot_catalog(catalog_path)


def test_pilot_cases_cover_decision_families() -> None:
    cases = load_pilot_cases(CASES)

    assert {case.case_type for case in cases} == {
        "positive",
        "confusing",
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
