from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from intent_routing.ops.csv_baseline import (
    compare_baseline,
    freeze_baseline,
    render_baseline_comparison_json,
    render_baseline_comparison_markdown,
)


def test_baseline_compare_passes_when_case_results_match(tmp_path: Path) -> None:
    report = _threshold_report(result="PASS")
    baseline = freeze_baseline(report, _csv_path(tmp_path), "balanced")

    result = compare_baseline(report, baseline)

    assert result.passed is True
    assert result.block_reasons == []
    assert result.new_failures == []
    assert result.new_reviews == []
    assert result.missing_cases == []
    assert result.changed_decisions == []
    assert result.changed_intents == []
    assert result.changed_route_keys == []


def test_baseline_compare_fails_on_new_fail_case(tmp_path: Path) -> None:
    baseline = freeze_baseline(_threshold_report(result="PASS"), _csv_path(tmp_path), "balanced")
    current = _threshold_report(result="FAIL", actual_decision="fallback")

    result = compare_baseline(current, baseline)

    assert result.passed is False
    assert result.new_failures == [
        {
            "case_id": "C001",
            "preset": "balanced",
            "expected_result": "PASS",
            "actual_result": "FAIL",
        }
    ]
    assert "new FAIL cases above allowance" in result.block_reasons


def test_baseline_compare_fails_on_new_review_case_when_disallowed(
    tmp_path: Path,
) -> None:
    baseline = freeze_baseline(
        _threshold_report(result="PASS"),
        _csv_path(tmp_path),
        "balanced",
    )
    current = _threshold_report(result="REVIEW")

    result = compare_baseline(current, baseline)

    assert result.passed is False
    assert result.new_reviews == [
        {
            "case_id": "C001",
            "preset": "balanced",
            "expected_result": "PASS",
            "actual_result": "REVIEW",
        }
    ]
    assert "new REVIEW cases above allowance" in result.block_reasons


def test_baseline_compare_fails_on_risk_pass_rate_regression(tmp_path: Path) -> None:
    baseline = freeze_baseline(_threshold_report(result="PASS"), _csv_path(tmp_path), "balanced")
    current = _threshold_report(result="PASS", risk_pass_rate=0.5)

    result = compare_baseline(current, baseline)

    assert result.passed is False
    assert result.block_reasons == ["balanced risk_pass_rate 50.0% below required 100.0%"]


def test_freeze_baseline_stores_repo_relative_csv_path() -> None:
    csv_path = Path.cwd() / "docs/pilot/it-helpdesk-pilot-cases.csv"

    baseline = freeze_baseline(_threshold_report(result="PASS"), csv_path, "balanced")

    assert baseline["policy"]["csv_path"] == "docs/pilot/it-helpdesk-pilot-cases.csv"


def test_baseline_compare_fails_on_csv_sha256_mismatch(tmp_path: Path) -> None:
    baseline = freeze_baseline(_threshold_report(result="PASS"), _csv_path(tmp_path), "balanced")
    changed_csv = tmp_path / "changed.csv"
    changed_csv.write_text(
        "case_id,query,expected_intent,case_type,memo\n"
        "C001,changed,it_api_timeout,positive,memo\n",
        encoding="utf-8",
    )

    result = compare_baseline(
        _threshold_report(result="PASS"),
        baseline,
        current_csv_path=changed_csv,
    )

    assert result.passed is False
    assert result.csv_sha256_mismatch is not None
    assert result.csv_sha256_mismatch["expected_sha256"] == baseline["policy"]["csv_sha256"]
    assert result.csv_sha256_mismatch["actual_sha256"]
    assert "csv_sha256 mismatch" in result.block_reasons


def test_baseline_compare_fails_on_missing_baseline_case(tmp_path: Path) -> None:
    baseline = freeze_baseline(_threshold_report(result="PASS"), _csv_path(tmp_path), "balanced")
    current = _threshold_report(result="PASS")
    current["results"]["balanced"] = []

    result = compare_baseline(current, baseline)

    assert result.passed is False
    assert result.missing_cases == [{"case_id": "C001", "preset": "balanced"}]
    assert "missing baseline cases in current report" in result.block_reasons


def test_baseline_compare_fails_on_decision_intent_and_route_key_drift(
    tmp_path: Path,
) -> None:
    baseline = freeze_baseline(_threshold_report(result="PASS"), _csv_path(tmp_path), "balanced")
    current = _threshold_report(
        result="PASS",
        actual_decision="fallback",
        actual_intent="it_password_reset",
        actual_route_key="it.password_reset.self_service",
    )

    result = compare_baseline(current, baseline)

    assert result.passed is False
    assert result.changed_decisions == [
        {
            "case_id": "C001",
            "preset": "balanced",
            "baseline_value": "confident",
            "actual_value": "fallback",
        }
    ]
    assert result.changed_intents == [
        {
            "case_id": "C001",
            "preset": "balanced",
            "baseline_value": "it_api_timeout",
            "actual_value": "it_password_reset",
        }
    ]
    assert result.changed_route_keys == [
        {
            "case_id": "C001",
            "preset": "balanced",
            "baseline_value": "it.api_timeout.manual_lookup",
            "actual_value": "it.password_reset.self_service",
        }
    ]
    assert "decision drift from baseline" in result.block_reasons
    assert "intent drift from baseline" in result.block_reasons
    assert "route_key drift from baseline" in result.block_reasons


def test_baseline_markdown_escapes_table_cells_as_single_line(tmp_path: Path) -> None:
    baseline = freeze_baseline(_threshold_report(result="PASS"), _csv_path(tmp_path), "balanced")
    current = _threshold_report(
        result="PASS",
        actual_intent="line one\nline|two",
    )

    markdown = render_baseline_comparison_markdown(compare_baseline(current, baseline))

    assert "line one line\\|two" in markdown
    assert "line one\nline" not in markdown


def test_baseline_renderer_excludes_query_text_and_secret_fields(tmp_path: Path) -> None:
    report = _threshold_report(
        result="FAIL",
        query="API timeout 500 에러가 납니다",
        authorization="Bearer secret-token",
        api_key="sk-secret",
        encrypted_dek="encrypted-value",
    )
    baseline = freeze_baseline(report, _csv_path(tmp_path), "balanced")
    result = compare_baseline(report, baseline)

    rendered = (
        json.dumps(baseline, ensure_ascii=False)
        + render_baseline_comparison_json(result)
        + render_baseline_comparison_markdown(result)
    )

    for forbidden in (
        "API timeout 500 에러가 납니다",
        "Bearer secret-token",
        "sk-secret",
        "encrypted-value",
        "query",
        "authorization",
        "api_key",
        "encrypted_dek",
    ):
        assert forbidden not in rendered


def _csv_path(tmp_path: Path) -> Path:
    path = tmp_path / "cases.csv"
    path.write_text(
        "case_id,query,expected_intent,case_type,memo\n"
        "C001,hello,it_api_timeout,positive,memo\n",
        encoding="utf-8",
    )
    return path


def _threshold_report(
    *,
    result: str,
    actual_decision: str = "confident",
    actual_intent: str | None = "it_api_timeout",
    actual_route_key: str | None = "it.api_timeout.manual_lookup",
    pass_rate: float = 1.0,
    risk_pass_rate: float = 1.0,
    **extra_row: object,
) -> dict[str, Any]:
    return {
        "service_id": "svc-test",
        "policy_version": "pol-test",
        "intent_catalog_version": "cat-test",
        "runs": {
            "balanced": {
                "pass_rate": pass_rate,
                "risk_pass_rate": risk_pass_rate,
                "gate_passed": result == "PASS",
            }
        },
        "results": {
            "balanced": [
                {
                    "case_id": "C001",
                    "case_type": "positive",
                    "expected_decision": "confident",
                    "expected_intent": "it_api_timeout",
                    "actual_decision": actual_decision,
                    "actual_intent": actual_intent,
                    "actual_route_key": actual_route_key,
                    "result": result,
                    **extra_row,
                }
            ]
        },
    }
