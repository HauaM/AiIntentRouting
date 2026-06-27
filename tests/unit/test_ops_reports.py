from __future__ import annotations

import json
from pathlib import Path
from types import TracebackType

import pytest

from intent_routing.ops.reports import render_threshold_report


def test_render_threshold_report_orders_presets_and_shows_gate_state() -> None:
    report = render_threshold_report(
        service_id="it-helpdesk-pilot",
        runs={
            "exploratory": {
                "test_run_id": "tr-exp",
                "threshold_value": 0.6,
                "pass_rate": 0.7,
                "review_rate": 0.2,
                "risk_pass_rate": 1.0,
                "gate_passed": True,
                "block_reasons": [],
                "recommendations": ["review rate above 15%"],
            },
            "strict": {
                "test_run_id": "tr-strict",
                "threshold_value": 1.0,
                "pass_rate": 0.5,
                "review_rate": 0.5,
                "risk_pass_rate": 1.0,
                "gate_passed": False,
                "block_reasons": ["pass rate below 70%"],
                "recommendations": ["review rate above 15%"],
            },
            "balanced": {
                "test_run_id": "tr-balanced",
                "threshold_value": 0.8,
                "pass_rate": 0.8,
                "review_rate": 0.1,
                "risk_pass_rate": 1.0,
                "gate_passed": True,
                "block_reasons": [],
                "recommendations": [],
            },
        },
    )

    assert "| strict | 1.00 | 50.0% | 50.0% | 100.0% | FAIL |" in report
    assert "| balanced | 0.80 | 80.0% | 10.0% | 100.0% | PASS |" in report
    assert "| exploratory | 0.60 | 70.0% | 20.0% | 100.0% | PASS |" in report
    assert report.index("| strict |") < report.index("| balanced |")
    assert report.index("| balanced |") < report.index("| exploratory |")


def test_render_threshold_report_uses_default_findings_message_when_none_exist() -> None:
    report = render_threshold_report(
        service_id="it-helpdesk-pilot",
        runs={
            "strict": {
                "test_run_id": "tr-strict",
                "threshold_value": 1.0,
                "pass_rate": 0.9,
                "review_rate": 0.1,
                "risk_pass_rate": 1.0,
                "gate_passed": True,
                "block_reasons": [],
                "recommendations": [],
            }
        },
    )

    assert "## Findings" in report
    assert "- All presets passed without recommendations." in report
    assert report.endswith("\n")


def test_run_csv_gate_posts_presets_writes_outputs_and_avoids_secret_logging(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import scripts.run_csv_gate as run_csv_gate

    state_path = tmp_path / "seed-state.json"
    csv_path = tmp_path / "cases.csv"
    out_dir = tmp_path / "reports"

    state = {
        "service_id": "it-helpdesk-pilot",
        "policy_version": 3,
        "intent_catalog_version": 7,
        "api_key": "super-secret-api-key",
    }
    state_path.write_text(json.dumps(state), encoding="utf-8")
    csv_path.write_text(
        "case_id,query,expected_intent,case_type,memo\n"
        "C001,hello,it_api_timeout,positive,sample\n",
        encoding="utf-8",
    )

    calls: list[tuple[str, dict[str, object]]] = []

    class FakeAdminApiClient:
        def __init__(
            self,
            *,
            base_url: str,
            admin_token: str,
            actor_id: str,
            actor_roles: str,
        ) -> None:
            assert base_url == "http://testserver"
            assert admin_token == "bootstrap-token"
            assert actor_id == "csv-gate"
            assert actor_roles == "system_admin"

        def __enter__(self) -> FakeAdminApiClient:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            return None

        def post(self, path: str, *, json: dict[str, object] | None = None) -> dict[str, object]:
            assert json is not None
            calls.append((path, json))
            preset = str(json["threshold_preset"])
            return {
                "test_run_id": f"tr-{preset}",
                "threshold_value": {"strict": 1.0, "balanced": 0.8, "exploratory": 0.6}[preset],
                "pass_rate": {"strict": 0.5, "balanced": 0.8, "exploratory": 0.7}[preset],
                "review_rate": {"strict": 0.5, "balanced": 0.1, "exploratory": 0.2}[preset],
                "risk_pass_rate": 1.0,
                "gate_passed": preset != "strict",
                "block_reasons": ["pass rate below 70%"] if preset == "strict" else [],
                "recommendations": ["review rate above 15%"] if preset != "balanced" else [],
            }

    monkeypatch.setattr(run_csv_gate, "AdminApiClient", FakeAdminApiClient)

    run_csv_gate.main(
        [
            "--base-url",
            "http://testserver",
            "--admin-token",
            "bootstrap-token",
            "--state",
            str(state_path),
            "--csv",
            str(csv_path),
            "--out-dir",
            str(out_dir),
        ]
    )

    captured = capsys.readouterr()
    stdout = captured.out
    assert str(state["api_key"]) not in stdout
    assert str(out_dir / "it-helpdesk-pilot-threshold-comparison.md") in stdout
    assert "strict: FAIL" in captured.out
    assert "balanced: PASS" in captured.out
    assert "exploratory: PASS" in captured.out

    assert [path for path, _json in calls] == [
        "/admin/v1/services/it-helpdesk-pilot/test-runs",
        "/admin/v1/services/it-helpdesk-pilot/test-runs",
        "/admin/v1/services/it-helpdesk-pilot/test-runs",
    ]
    assert [str(payload["threshold_preset"]) for _path, payload in calls] == [
        "strict",
        "balanced",
        "exploratory",
    ]
    assert all(payload["policy_version"] == 3 for _path, payload in calls)
    assert all(payload["intent_catalog_version"] == 7 for _path, payload in calls)
    assert all(payload["source_filename"] == "cases.csv" for _path, payload in calls)

    json_output = json.loads(
        (out_dir / "it-helpdesk-pilot-threshold-comparison.json").read_text(encoding="utf-8")
    )
    assert json_output["service_id"] == "it-helpdesk-pilot"
    assert list(json_output["runs"]) == ["strict", "balanced", "exploratory"]

    markdown_output = (
        out_dir / "it-helpdesk-pilot-threshold-comparison.md"
    ).read_text(encoding="utf-8")
    assert "# CSV Gate Threshold Comparison: it-helpdesk-pilot" in markdown_output
