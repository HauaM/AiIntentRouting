import csv
from pathlib import Path

from intent_routing.ops.pilot_catalog import load_pilot_cases, load_pilot_catalog

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "docs/pilot/it-helpdesk-pilot-catalog.json"
CASES = ROOT / "docs/pilot/it-helpdesk-pilot-cases.csv"


def test_pilot_catalog_has_route_key_and_example_contract() -> None:
    catalog = load_pilot_catalog(CATALOG)

    assert catalog.service_id == "it-helpdesk-pilot"
    assert catalog.display_name == "IT Helpdesk Pilot"
    assert catalog.environment == "dev"
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


def test_raw_csv_header_matches_sprint_zero_runner_contract() -> None:
    with CASES.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        assert next(reader) == ["case_id", "query", "expected_intent", "case_type", "memo"]
