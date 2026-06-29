from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.compare_csv_baseline import compare_csv_baseline, freeze_csv_baseline

ROOT = Path(__file__).resolve().parents[2]


def test_csv_baseline_freeze_then_compare_passes(tmp_path: Path) -> None:
    threshold_report_path = tmp_path / "threshold-comparison.json"
    baseline_path = tmp_path / "baseline.json"
    out_dir = tmp_path / "csv-baseline"
    threshold_report_path.write_text(
        json.dumps(_threshold_report(result="PASS"), ensure_ascii=False),
        encoding="utf-8",
    )

    freeze_result = freeze_csv_baseline(
        threshold_report_path=threshold_report_path,
        csv_path=ROOT / "docs/pilot/it-helpdesk-pilot-cases.csv",
        preset="balanced",
        baseline_id="it-helpdesk-pilot-standard-20260629",
        out_path=baseline_path,
    )
    compare_result = compare_csv_baseline(
        threshold_report_path=threshold_report_path,
        baseline_path=baseline_path,
        csv_path=ROOT / "docs/pilot/it-helpdesk-pilot-cases.csv",
        out_dir=out_dir,
    )

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert baseline["baseline_id"] == "it-helpdesk-pilot-standard-20260629"
    assert baseline["policy"]["required_preset"] == "balanced"
    assert baseline["policy"]["csv_sha256"]
    assert "query" not in json.dumps(baseline, ensure_ascii=False)
    assert freeze_result["json_path"] == str(baseline_path)
    assert compare_result["passed"] is True
    assert Path(compare_result["json_path"]).exists()
    assert Path(compare_result["markdown_path"]).exists()


def test_csv_baseline_compare_writes_failure_report_and_exits_nonzero(
    tmp_path: Path,
) -> None:
    threshold_report_path = tmp_path / "threshold-comparison.json"
    baseline_path = tmp_path / "baseline.json"
    out_dir = tmp_path / "csv-baseline"
    threshold_report_path.write_text(
        json.dumps(_threshold_report(result="PASS"), ensure_ascii=False),
        encoding="utf-8",
    )
    freeze_csv_baseline(
        threshold_report_path=threshold_report_path,
        csv_path=ROOT / "docs/pilot/it-helpdesk-pilot-cases.csv",
        preset="balanced",
        baseline_id="it-helpdesk-pilot-standard-20260629",
        out_path=baseline_path,
    )
    threshold_report_path.write_text(
        json.dumps(_threshold_report(result="FAIL", actual_decision="fallback")),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc_info:
        compare_csv_baseline(
            threshold_report_path=threshold_report_path,
            baseline_path=baseline_path,
            out_dir=out_dir,
        )

    assert exc_info.value.code == 1
    report = json.loads((out_dir / "csv-baseline-comparison.json").read_text())
    assert report["passed"] is False
    assert report["new_failures"][0]["case_id"] == "C001"


def test_csv_baseline_compare_writes_csv_hash_mismatch_evidence(
    tmp_path: Path,
) -> None:
    threshold_report_path = tmp_path / "threshold-comparison.json"
    baseline_path = tmp_path / "baseline.json"
    changed_csv = tmp_path / "changed.csv"
    out_dir = tmp_path / "csv-baseline"
    threshold_report_path.write_text(
        json.dumps(_threshold_report(result="PASS"), ensure_ascii=False),
        encoding="utf-8",
    )
    changed_csv.write_text(
        "case_id,query,expected_intent,case_type,memo\n"
        "C001,changed,it_api_timeout,positive,memo\n",
        encoding="utf-8",
    )
    freeze_csv_baseline(
        threshold_report_path=threshold_report_path,
        csv_path=ROOT / "docs/pilot/it-helpdesk-pilot-cases.csv",
        preset="balanced",
        baseline_id="it-helpdesk-pilot-standard-20260629",
        out_path=baseline_path,
    )

    result = compare_csv_baseline(
        threshold_report_path=threshold_report_path,
        baseline_path=baseline_path,
        csv_path=changed_csv,
        out_dir=out_dir,
        exit_on_failure=False,
    )

    assert result["passed"] is False
    assert result["failure_message"] == "csv_sha256 mismatch"
    report = json.loads((out_dir / "csv-baseline-comparison.json").read_text())
    assert report["csv_sha256_mismatch"]["expected_sha256"]
    assert report["csv_sha256_mismatch"]["actual_sha256"]


def _threshold_report(
    *,
    result: str,
    actual_decision: str = "confident",
    pass_rate: float = 1.0,
    risk_pass_rate: float = 1.0,
) -> dict[str, object]:
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
                    "actual_intent": "it_api_timeout",
                    "actual_route_key": "it.api_timeout.manual_lookup",
                    "result": result,
                    "query": "API timeout 500 에러가 납니다",
                    "authorization": "Bearer secret-token",
                    "encrypted_dek": "encrypted-value",
                }
            ]
        },
    }
