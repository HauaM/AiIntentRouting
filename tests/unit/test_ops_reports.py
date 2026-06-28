from __future__ import annotations

import json
from pathlib import Path
from types import TracebackType

import pytest

from intent_routing.ops.reports import render_threshold_report


def _complete_runs(
    *,
    strict_findings: bool = True,
    balanced_findings: bool = False,
    exploratory_findings: bool = True,
) -> dict[str, dict[str, object]]:
    return {
        "strict": {
            "test_run_id": "tr-strict",
            "threshold_value": 1.0,
            "pass_rate": 0.5 if strict_findings else 0.9,
            "review_rate": 0.5 if strict_findings else 0.1,
            "risk_pass_rate": 1.0,
            "gate_passed": not strict_findings,
            "block_reasons": ["pass rate below 70%"] if strict_findings else [],
            "recommendations": ["review rate above 15%"] if strict_findings else [],
        },
        "balanced": {
            "test_run_id": "tr-balanced",
            "threshold_value": 0.8,
            "pass_rate": 0.8,
            "review_rate": 0.1 if not balanced_findings else 0.2,
            "risk_pass_rate": 1.0,
            "gate_passed": True,
            "block_reasons": [],
            "recommendations": ["review rate above 15%"] if balanced_findings else [],
        },
        "exploratory": {
            "test_run_id": "tr-exp",
            "threshold_value": 0.6,
            "pass_rate": 0.7,
            "review_rate": 0.2 if exploratory_findings else 0.1,
            "risk_pass_rate": 1.0,
            "gate_passed": True,
            "block_reasons": [],
            "recommendations": ["review rate above 15%"] if exploratory_findings else [],
        },
    }


def test_render_threshold_report_orders_presets_and_shows_gate_state() -> None:
    runs = _complete_runs()

    report = render_threshold_report("it-helpdesk-pilot", runs)

    assert "| strict | 1.00 | 50.0% | 50.0% | 100.0% | FAIL |" in report
    assert "| balanced | 0.80 | 80.0% | 10.0% | 100.0% | PASS |" in report
    assert "| exploratory | 0.60 | 70.0% | 20.0% | 100.0% | PASS |" in report
    assert "| --- | ---: | ---: | ---: | ---: | --- | --- |" in report
    assert report.index("| strict |") < report.index("| balanced |")
    assert report.index("| balanced |") < report.index("| exploratory |")


def test_render_threshold_report_uses_default_findings_message_when_none_exist() -> None:
    report = render_threshold_report(
        service_id="it-helpdesk-pilot",
        runs=_complete_runs(
            strict_findings=False,
            balanced_findings=False,
            exploratory_findings=False,
        ),
    )

    assert "## Findings" in report
    assert "- All presets passed without recommendations." in report
    assert report.endswith("\n")


def test_render_threshold_report_raises_when_a_preset_is_missing() -> None:
    runs = _complete_runs()
    del runs["exploratory"]

    with pytest.raises(ValueError, match="exploratory"):
        render_threshold_report("it-helpdesk-pilot", runs)


def test_render_threshold_report_includes_case_counts_failures_and_reviews() -> None:
    report = render_threshold_report(
        service_id="it-helpdesk-pilot",
        runs=_complete_runs(),
        results_by_preset={
            "strict": [],
            "balanced": [
                {
                    "case_id": "C001",
                    "case_type": "positive",
                    "expected_decision": "confident",
                    "expected_intent": "it_api_timeout",
                    "actual_decision": "fallback",
                    "actual_intent": None,
                    "confidence": None,
                    "result": "FAIL",
                    "reason": "actual decision did not match expected decision",
                },
                {
                    "case_id": "C002",
                    "case_type": "clarify",
                    "expected_decision": "clarify",
                    "expected_intent": None,
                    "actual_decision": "clarify",
                    "actual_intent": None,
                    "confidence": 0.72,
                    "result": "REVIEW",
                    "reason": "requires human inspection",
                },
            ],
            "exploratory": [],
        },
    )

    assert "## Case Result Counts" in report
    assert "| balanced | positive | 0 | 0 | 1 | 1 |" in report
    assert "## Failed Cases" in report
    failed_row = (
        "| balanced | C001 | positive | confident | fallback | it_api_timeout |  |  | "
        "actual decision did not match expected decision |"
    )
    assert failed_row in report
    assert "## Review Cases" in report
    review_row = (
        "| balanced | C002 | clarify | clarify | clarify |  |  | 72.0% | "
        "requires human inspection |"
    )
    assert review_row in report


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

    calls: list[tuple[str, str, dict[str, object] | None]] = []

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
            calls.append(("POST", path, json))
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

        def get(self, path: str) -> list[dict[str, object]]:
            calls.append(("GET", path, None))
            test_run_id = path.rsplit("/", 2)[1]
            preset = test_run_id.removeprefix("tr-")
            return [
                {
                    "case_id": f"{preset}-001",
                    "query_masked": "masked query",
                    "case_type": "clarify" if preset == "balanced" else "positive",
                    "expected_decision": "clarify" if preset == "balanced" else "confident",
                    "expected_intent": None if preset == "balanced" else "it_api_timeout",
                    "actual_decision": "clarify" if preset == "balanced" else "fallback",
                    "actual_intent": None,
                    "actual_route_key": None,
                    "confidence": 0.72 if preset == "balanced" else None,
                    "result": "REVIEW" if preset == "balanced" else "FAIL",
                    "reason": "requires human inspection"
                    if preset == "balanced"
                    else "actual decision did not match expected decision",
                }
            ]

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

    assert [(method, path) for method, path, _json in calls] == [
        ("POST", "/admin/v1/services/it-helpdesk-pilot/test-runs"),
        (
            "GET",
            "/admin/v1/services/it-helpdesk-pilot/test-runs/tr-strict/results",
        ),
        ("POST", "/admin/v1/services/it-helpdesk-pilot/test-runs"),
        (
            "GET",
            "/admin/v1/services/it-helpdesk-pilot/test-runs/tr-balanced/results",
        ),
        ("POST", "/admin/v1/services/it-helpdesk-pilot/test-runs"),
        (
            "GET",
            "/admin/v1/services/it-helpdesk-pilot/test-runs/tr-exploratory/results",
        ),
    ]
    post_payloads = [payload for method, _path, payload in calls if method == "POST"]
    assert [str(payload["threshold_preset"]) for payload in post_payloads if payload] == [
        "strict",
        "balanced",
        "exploratory",
    ]
    assert all(payload["policy_version"] == 3 for payload in post_payloads if payload)
    assert all(payload["intent_catalog_version"] == 7 for payload in post_payloads if payload)
    assert all(payload["source_filename"] == "cases.csv" for payload in post_payloads if payload)

    json_output = json.loads(
        (out_dir / "it-helpdesk-pilot-threshold-comparison.json").read_text(encoding="utf-8")
    )
    assert json_output["service_id"] == "it-helpdesk-pilot"
    assert list(json_output["runs"]) == ["strict", "balanced", "exploratory"]
    assert json_output["results"]["balanced"][0]["case_id"] == "balanced-001"

    markdown_output = (
        out_dir / "it-helpdesk-pilot-threshold-comparison.md"
    ).read_text(encoding="utf-8")
    assert "# CSV Gate Threshold Comparison: it-helpdesk-pilot" in markdown_output
    assert "## Case Result Counts" in markdown_output
    assert "## Review Cases" in markdown_output


def test_run_csv_gate_rejects_service_id_path_escape_and_writes_nothing_outside_out_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import scripts.run_csv_gate as run_csv_gate

    state_path = tmp_path / "seed-state.json"
    csv_path = tmp_path / "cases.csv"
    out_dir = tmp_path / "reports"
    outside_json = tmp_path / "outside-threshold-comparison.json"
    outside_md = tmp_path / "outside-threshold-comparison.md"

    state_path.write_text(
        json.dumps(
            {
                "service_id": "../../outside",
                "policy_version": 3,
                "intent_catalog_version": 7,
            }
        ),
        encoding="utf-8",
    )
    csv_path.write_text(
        "case_id,query,expected_intent,case_type,memo\n"
        "C001,hello,it_api_timeout,positive,sample\n",
        encoding="utf-8",
    )

    class FakeAdminApiClient:
        def __init__(self, **_: object) -> None:
            raise AssertionError("AdminApiClient should not be constructed for invalid service_id")

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
            raise AssertionError(f"unexpected post call: {path} {json}")

    monkeypatch.setattr(run_csv_gate, "AdminApiClient", FakeAdminApiClient)

    with pytest.raises(ValueError, match="service_id"):
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

    assert not outside_json.exists()
    assert not outside_md.exists()
    assert list(out_dir.glob("*")) == []


def test_run_csv_gate_uses_admin_token_from_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import scripts.run_csv_gate as run_csv_gate

    state_path = tmp_path / "seed-state.json"
    csv_path = tmp_path / "cases.csv"
    out_dir = tmp_path / "reports"

    state_path.write_text(
        json.dumps(
            {
                "service_id": "it-helpdesk-pilot",
                "policy_version": 3,
                "intent_catalog_version": 7,
            }
        ),
        encoding="utf-8",
    )
    csv_path.write_text(
        "case_id,query,expected_intent,case_type,memo\n"
        "C001,hello,it_api_timeout,positive,sample\n",
        encoding="utf-8",
    )

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
            assert admin_token == "env-bootstrap-token"
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

        def post(self, _path: str, *, json: dict[str, object] | None = None) -> dict[str, object]:
            assert json is not None
            preset = str(json["threshold_preset"])
            return {
                "test_run_id": f"tr-{preset}",
                "threshold_value": {"strict": 1.0, "balanced": 0.8, "exploratory": 0.6}[preset],
                "pass_rate": {"strict": 0.7, "balanced": 0.8, "exploratory": 0.7}[preset],
                "review_rate": {"strict": 0.1, "balanced": 0.1, "exploratory": 0.1}[preset],
                "risk_pass_rate": 1.0,
                "gate_passed": True,
                "block_reasons": [],
                "recommendations": [],
            }

        def get(self, path: str) -> list[dict[str, object]]:
            test_run_id = path.rsplit("/", 2)[1]
            return [
                {
                    "case_id": f"{test_run_id}-001",
                    "query_masked": "masked query",
                    "case_type": "positive",
                    "expected_decision": "confident",
                    "expected_intent": "it_api_timeout",
                    "actual_decision": "confident",
                    "actual_intent": "it_api_timeout",
                    "actual_route_key": "it.api_timeout.manual_lookup",
                    "confidence": 0.91,
                    "result": "PASS",
                    "reason": "matched expected decision and intent",
                }
            ]

    monkeypatch.setattr(run_csv_gate, "AdminApiClient", FakeAdminApiClient)
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "env-bootstrap-token")

    run_csv_gate.main(
        [
            "--base-url",
            "http://testserver",
            "--state",
            str(state_path),
            "--csv",
            str(csv_path),
            "--out-dir",
            str(out_dir),
        ]
        )


def test_run_threshold_comparison_returns_report_paths_and_runs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import scripts.run_csv_gate as run_csv_gate

    state_path = tmp_path / "seed-state.json"
    csv_path = tmp_path / "cases.csv"
    out_dir = tmp_path / "reports"
    state_path.write_text(
        json.dumps(
            {
                "service_id": "it-helpdesk-pilot",
                "policy_version": 3,
                "intent_catalog_version": 7,
            }
        ),
        encoding="utf-8",
    )
    csv_path.write_text(
        "case_id,query,expected_intent,case_type,memo\n"
        "C001,hello,it_api_timeout,positive,sample\n",
        encoding="utf-8",
    )

    class FakeAdminApiClient:
        def __init__(self, **_kwargs: object) -> None:
            return None

        def __enter__(self) -> FakeAdminApiClient:
            return self

        def __exit__(
            self,
            _exc_type: type[BaseException] | None,
            _exc: BaseException | None,
            _traceback: TracebackType | None,
        ) -> None:
            return None

        def post(self, _path: str, *, json: dict[str, object] | None = None) -> dict[str, object]:
            assert json is not None
            preset = str(json["threshold_preset"])
            return {
                "test_run_id": f"tr-{preset}",
                "threshold_value": {"strict": 1.0, "balanced": 0.8, "exploratory": 0.6}[preset],
                "pass_rate": 0.8,
                "review_rate": 0.1,
                "risk_pass_rate": 1.0,
                "gate_passed": True,
                "block_reasons": [],
                "recommendations": [],
            }

        def get(self, path: str) -> list[dict[str, object]]:
            test_run_id = path.rsplit("/", 2)[1]
            return [
                {
                    "case_id": f"{test_run_id}-001",
                    "query_masked": "masked query",
                    "case_type": "positive",
                    "expected_decision": "confident",
                    "expected_intent": "it_api_timeout",
                    "actual_decision": "confident",
                    "actual_intent": "it_api_timeout",
                    "actual_route_key": "it.api_timeout.manual_lookup",
                    "confidence": 0.91,
                    "result": "PASS",
                    "reason": "matched expected decision and intent",
                }
            ]

    monkeypatch.setattr(run_csv_gate, "AdminApiClient", FakeAdminApiClient)

    result = run_csv_gate.run_threshold_comparison(
        base_url="http://testserver",
        admin_token="bootstrap-token",
        state_path=state_path,
        csv_path=csv_path,
        out_dir=out_dir,
    )

    assert result["service_id"] == "it-helpdesk-pilot"
    assert result["runs"]["balanced"]["test_run_id"] == "tr-balanced"
    assert result["results"]["balanced"][0]["case_id"] == "tr-balanced-001"
    assert Path(result["json_path"]).exists()
    assert Path(result["markdown_path"]).exists()
