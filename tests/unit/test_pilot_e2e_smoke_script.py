from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts import run_pilot_e2e_smoke as e2e_script
from scripts.run_pilot_readiness import _redact_threshold_report_json


def test_threshold_report_json_redacts_shared_evidence_secret_keys(tmp_path: Path) -> None:
    report_path = tmp_path / "threshold.json"
    report_path.write_text(
        json.dumps(
            {
                "api_key": "irt_raw_api_key",
                "Authorization": "Bearer raw-token",
                "nested": {
                    "query_raw": "raw query",
                    "state_path": "/tmp/pilot.state.secret.json",
                    "encrypted_dek": "dek-secret",
                    "ciphertext": "cipher-secret",
                    "query_masked": "API timeout 500 에러가 납니다",
                },
                "items": [
                    {
                        "Query_Masked": "another raw query",
                        "ENCRYPTED_DEK": "nested-dek",
                    }
                ],
                "safe_metric": 1.0,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    _redact_threshold_report_json(report_path)

    redacted = json.loads(report_path.read_text(encoding="utf-8"))
    assert redacted["api_key"] == "REDACTED"
    assert redacted["Authorization"] == "REDACTED"
    assert redacted["nested"]["query_raw"] == "REDACTED"
    assert redacted["nested"]["state_path"] == "REDACTED"
    assert redacted["nested"]["encrypted_dek"] == "REDACTED"
    assert redacted["nested"]["ciphertext"] == "REDACTED"
    assert redacted["nested"]["query_masked"] == "REDACTED"
    assert redacted["items"][0]["Query_Masked"] == "REDACTED"
    assert redacted["items"][0]["ENCRYPTED_DEK"] == "REDACTED"
    assert redacted["safe_metric"] == 1.0
    serialized = json.dumps(redacted, ensure_ascii=False)
    for secret in (
        "irt_raw_api_key",
        "Bearer raw-token",
        "raw query",
        ".secret.json",
        "dek-secret",
        "cipher-secret",
        "API timeout 500 에러가 납니다",
    ):
        assert secret not in serialized


def test_main_prints_paths_then_exits_nonzero_when_quality_gate_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run_pilot_e2e_smoke(**_: Any) -> dict[str, Any]:
        return {
            "json_path": "var/evidence/svc/e2e/pilot-e2e-smoke-index.json",
            "markdown_path": "var/evidence/svc/e2e/pilot-e2e-smoke-index.md",
            "quality_gate": {
                "required_preset": "balanced",
                "passed": False,
                "pass_rate": 0.5,
                "risk_pass_rate": 1.0,
            },
        }

    monkeypatch.setattr(e2e_script, "run_pilot_e2e_smoke", fake_run_pilot_e2e_smoke)

    with pytest.raises(SystemExit) as exc_info:
        e2e_script.main(
            [
                "--base-url",
                "http://127.0.0.1:8000",
                "--admin-token",
                "raw-admin-secret",
                "--service-id",
                "svc",
                "--environment",
                "dev",
                "--state-path",
                "var/pilot/svc.state.secret.json",
                "--out-dir",
                "var/evidence/svc/e2e",
            ]
        )

    assert exc_info.value.code == 1
    stdout = capsys.readouterr().out
    assert "pilot-e2e-smoke-index.json" in stdout
    assert "pilot-e2e-smoke-index.md" in stdout
    assert "raw-admin-secret" not in stdout
    assert ".secret.json" not in stdout
    assert "Bearer " not in stdout


def test_percent_formats_malformed_values_as_zero() -> None:
    assert e2e_script._percent(None) == "0.0%"
    assert e2e_script._percent("not-a-number") == "0.0%"
