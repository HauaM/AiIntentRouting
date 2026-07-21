from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from intent_routing.db import models
from scripts import export_ops_evidence

FORBIDDEN_MARKERS = (
    "query_raw",
    "text_raw",
    "Authorization",
    "RAW_TEXT_KEK_BASE64",
    "irt_secret",
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE=",
    "Bearer export-token",
    "ciphertext-value",
    "encrypted-dek-value",
)


def test_export_ops_evidence_args_default_to_release_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("RELEASE_ENVIRONMENT", "qa")
    monkeypatch.setenv("INTENT_ROUTING_ENVIRONMENT", "prod")

    args = export_ops_evidence._parse_args(
        [
            "--base-url",
            "http://example.test",
            "--service-id",
            "svc-evidence",
            "--out-dir",
            str(tmp_path),
        ]
    )

    assert args.environment == "qa"

    with pytest.raises(SystemExit):
        export_ops_evidence._parse_args(
            [
                "--base-url",
                "http://example.test",
                "--service-id",
                "svc-evidence",
                "--out-dir",
                str(tmp_path),
                "--environment",
                "staging",
            ]
        )

    monkeypatch.setenv("RELEASE_ENVIRONMENT", "pilot")
    with pytest.raises(SystemExit):
        export_ops_evidence._parse_args(
            [
                "--base-url",
                "http://example.test",
                "--service-id",
                "svc-evidence",
                "--out-dir",
                str(tmp_path),
            ]
        )


def test_export_ops_evidence_writes_redacted_json_and_markdown(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    service_id = f"svc-task7-export-{uuid4().hex}"
    latest_rewrap_run_id = _seed_rewrap_runs(db_session, service_id)
    bind = db_session.get_bind()
    assert isinstance(bind, Engine)
    monkeypatch.setenv(
        "TEST_DATABASE_URL",
        bind.url.render_as_string(hide_password=False),
    )
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/readyz":
            return httpx.Response(
                200,
                json={"status": "ready", "database": "ok", "embedding": "ok"},
            )
        assert request.headers["X-Admin-Token"] == "local-admin-token"
        assert request.headers["X-Actor-Id"] == "ops-evidence"
        assert request.headers["X-Actor-Roles"] == "system_admin"
        assert request.headers["X-Service-Scope"] == service_id

        if request.url.path == f"/admin/v1/services/{service_id}/releases/active":
            assert request.url.params["environment"] == "dev"
            return httpx.Response(
                200,
                json={
                    "release_version": "rel-task7-export-001",
                    "service_id": service_id,
                    "environment": "dev",
                    "policy_version": "pol-task7-export-001",
                    "intent_catalog_version": "cat-task7-export-001",
                    "model_version": "emb-fake-v1",
                    "vector_index_version": "vec-task7-export-001",
                    "test_dataset_version": "tds-task7-export-001",
                    "test_run_id": "trn-task7-export-001",
                    "pass_rate": 0.98,
                    "risk_pass_rate": 1.0,
                    "active": True,
                    "released_by": "release-operator",
                    "released_at": "2026-06-29T00:00:00Z",
                    "rollback_target": "rel-task7-export-000",
                },
            )
        if request.url.path == f"/admin/v1/services/{service_id}/runtime-metrics":
            assert request.url.params["window_hours"] == "24"
            assert request.url.params["environment"] == "dev"
            return httpx.Response(
                200,
                json={
                    "service_id": service_id,
                    "window_hours": 24,
                    "request_count": 3,
                    "decision_counts": {
                        "confident": 2,
                        "clarify": 0,
                        "fallback": 1,
                        "off_topic": 0,
                        "risk": 0,
                        "unauthorized": 0,
                    },
                    "error_counts": {},
                    "latency_ms": {"p50": 22, "p95": 31, "max": 31},
                    "top_route_keys": [
                        {"route_key": "it.api_timeout.manual_lookup", "count": 2}
                    ],
                    "raw_query_retention": {
                        "encrypted_count": 1,
                        "incomplete_count": 0,
                        "redacted_count": 2,
                    },
                },
            )
        if (
            request.url.path
            == f"/admin/v1/services/{service_id}/security/raw-text-key-summary"
        ):
            return httpx.Response(
                200,
                json={
                    "service_id": service_id,
                    "active_key_id": "pilot-kek-20260628-002",
                    "intent_examples": [
                        {"key_id": "pilot-kek-20260628-002", "count": 2}
                    ],
                    "runtime_logs": [
                        {"key_id": "pilot-kek-20260628-002", "count": 1},
                        {"key_id": None, "count": 2, "state": "raw_query_redacted"},
                    ],
                },
            )
        if request.url.path == f"/admin/v1/services/{service_id}/audit-logs":
            assert request.url.params["limit"] == "50"
            event_type = request.url.params["event_type"]
            unrelated_event: dict[str, Any] = {
                "audit_id": str(uuid4()),
                "event_type": "release.activated",
                "actor_id": "release-operator",
                "service_id": service_id,
                "trace_id": None,
                "target_type": "release",
                "target_id": "rel-unrelated",
                "view_reason": "approval=REL-UNRELATED",
                "source_ip": "127.0.0.1",
                "created_at": "2026-06-29T00:00:01Z",
            }
            lifecycle_events: dict[str, list[dict[str, Any]]] = {
                "raw_text.rewrap.executed": [
                    {
                        "audit_id": str(uuid4()),
                        "event_type": "raw_text.rewrap.executed",
                        "actor_id": "security-operator",
                        "service_id": service_id,
                        "trace_id": None,
                        "target_type": "raw_text_rewrap_run",
                        "target_id": latest_rewrap_run_id,
                        "view_reason": "approval=SEC-EXPORT-REWRAP",
                        "source_ip": "127.0.0.1",
                        "created_at": "2026-06-29T00:00:02Z",
                    }
                ],
                "runtime_log.raw_query_redacted": [
                    {
                        "audit_id": str(uuid4()),
                        "event_type": "runtime_log.raw_query_redacted",
                        "actor_id": "retention-operator",
                        "service_id": service_id,
                        "trace_id": "trace-redacted",
                        "target_type": "runtime_log",
                        "target_id": "trace-redacted",
                        "view_reason": "approval=SEC-EXPORT-RETENTION",
                        "source_ip": "127.0.0.1",
                        "created_at": "2026-06-29T00:00:04Z",
                    }
                ],
                "raw_query.viewed": [
                    {
                        "audit_id": str(uuid4()),
                        "event_type": "raw_query.viewed",
                        "actor_id": "auditor-user",
                        "service_id": service_id,
                        "trace_id": "trace-export-secret",
                        "target_type": "runtime_log",
                        "target_id": "trace-export-secret",
                        "view_reason": (
                            "approval=SEC-EXPORT-RAW; "
                            "Authorization=Bearer export-token; "
                            "details=query_raw text_raw RAW_TEXT_KEK_BASE64 "
                            "irt_secret_export"
                        ),
                        "source_ip": "127.0.0.1",
                        "created_at": "2026-06-29T00:00:03Z",
                    }
                ],
                "api_key.revoked": [
                    {
                        "audit_id": str(uuid4()),
                        "event_type": "api_key.revoked",
                        "actor_id": "security-operator",
                        "service_id": service_id,
                        "trace_id": None,
                        "target_type": "api_key",
                        "target_id": "key-rotated",
                        "view_reason": None,
                        "source_ip": "127.0.0.1",
                        "created_at": "2026-06-29T00:00:05Z",
                    }
                ],
            }
            return httpx.Response(
                200,
                json=[unrelated_event, *lifecycle_events.get(event_type, [])],
            )
        return httpx.Response(404, json={"error": "unexpected path"})

    result = export_ops_evidence.run_ops_evidence_export(
        base_url="http://testserver",
        admin_token="local-admin-token",
        service_id=service_id,
        out_dir=tmp_path,
        window_hours=24,
        actor_id="ops-evidence",
        environment="dev",
        transport=httpx.MockTransport(handler),
    )

    json_path = Path(result["json_path"])
    markdown_path = Path(result["markdown_path"])
    assert json_path.name == "ops-evidence.json"
    assert markdown_path.name == "ops-evidence.md"
    json_text = json_path.read_text(encoding="utf-8")
    markdown = markdown_path.read_text(encoding="utf-8")
    parsed = json.loads(json_text)
    assert parsed["service_id"] == service_id
    assert parsed["active_release"]["release_version"] == "rel-task7-export-001"
    assert parsed["readyz"]["status"] == "ready"
    assert parsed["runtime_metrics"]["raw_query_retention"]["redacted_count"] == 2
    assert parsed["raw_text_key_summary"]["runtime_logs"][-1]["count"] == 2
    assert parsed["latest_rewrap_runs"][0]["rewrap_run_id"] == latest_rewrap_run_id
    assert parsed["audit_evidence"]["count"] == 4
    assert [event["event_type"] for event in parsed["audit_evidence"]["events"]] == [
        "api_key.revoked",
        "runtime_log.raw_query_redacted",
        "raw_query.viewed",
        "raw_text.rewrap.executed",
    ]
    assert "release.activated" not in json_text
    assert "rel-unrelated" not in json_text
    assert "Audit event count: `4`" in markdown
    assert latest_rewrap_run_id in markdown

    for rendered in (json_text, markdown):
        for forbidden in FORBIDDEN_MARKERS:
            assert forbidden not in rendered

    called_paths = [request.url.path for request in requests]
    assert called_paths == [
        "/readyz",
        f"/admin/v1/services/{service_id}/releases/active",
        f"/admin/v1/services/{service_id}/runtime-metrics",
        f"/admin/v1/services/{service_id}/security/raw-text-key-summary",
        f"/admin/v1/services/{service_id}/audit-logs",
        f"/admin/v1/services/{service_id}/audit-logs",
        f"/admin/v1/services/{service_id}/audit-logs",
        f"/admin/v1/services/{service_id}/audit-logs",
    ]
    requested_event_types = [
        request.url.params["event_type"]
        for request in requests
        if request.url.path == f"/admin/v1/services/{service_id}/audit-logs"
    ]
    assert requested_event_types == [
        "raw_text.rewrap.executed",
        "runtime_log.raw_query_redacted",
        "raw_query.viewed",
        "api_key.revoked",
    ]


def test_export_ops_evidence_reports_rewrap_collection_status_without_database_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    service_id = "svc-task7-no-db"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/readyz":
            return httpx.Response(200, json={"status": "ready"})
        if request.url.path == f"/admin/v1/services/{service_id}/releases/active":
            return httpx.Response(
                200,
                json={
                    "release_version": "rel-no-db-001",
                    "service_id": service_id,
                    "environment": "dev",
                    "policy_version": "pol-no-db-001",
                    "intent_catalog_version": "cat-no-db-001",
                    "model_version": "emb-fake-v1",
                    "vector_index_version": "vec-no-db-001",
                    "test_dataset_version": "tds-no-db-001",
                    "test_run_id": "trn-no-db-001",
                    "pass_rate": 1.0,
                    "risk_pass_rate": 1.0,
                    "active": True,
                    "released_by": "release-operator",
                    "released_at": "2026-06-29T00:00:00Z",
                    "rollback_target": None,
                },
            )
        if request.url.path == f"/admin/v1/services/{service_id}/runtime-metrics":
            return httpx.Response(
                200,
                json={
                    "service_id": service_id,
                    "window_hours": 24,
                    "request_count": 0,
                    "decision_counts": {},
                    "error_counts": {},
                    "latency_ms": {"p50": None, "p95": None, "max": None},
                    "top_route_keys": [],
                    "raw_query_retention": {
                        "encrypted_count": 0,
                        "incomplete_count": 0,
                        "redacted_count": 0,
                    },
                },
            )
        if (
            request.url.path
            == f"/admin/v1/services/{service_id}/security/raw-text-key-summary"
        ):
            return httpx.Response(
                200,
                json={
                    "service_id": service_id,
                    "active_key_id": "pilot-kek-20260628-002",
                    "intent_examples": [],
                    "runtime_logs": [],
                },
            )
        if request.url.path == f"/admin/v1/services/{service_id}/audit-logs":
            return httpx.Response(200, json=[])
        return httpx.Response(404, json={"error": "unexpected path"})

    result = export_ops_evidence.run_ops_evidence_export(
        base_url="http://testserver",
        admin_token="local-admin-token",
        service_id=service_id,
        out_dir=tmp_path,
        window_hours=24,
        actor_id="ops-evidence",
        environment="dev",
        transport=httpx.MockTransport(handler),
    )

    json_text = Path(result["json_path"]).read_text(encoding="utf-8")
    markdown = Path(result["markdown_path"]).read_text(encoding="utf-8")
    parsed = json.loads(json_text)
    assert parsed["latest_rewrap_runs"] == []
    assert parsed["latest_rewrap_runs_status"] == {
        "collected": False,
        "reason": "DATABASE_URL missing",
    }
    assert "Rewrap runs collected: `false`" in markdown
    assert "Rewrap runs collection reason: `DATABASE_URL missing`" in markdown


def _seed_rewrap_runs(db_session: Session, service_id: str) -> str:
    run_prefix = f"rtr-export-{service_id.removeprefix('svc-task7-export-')[:8]}"
    old_run_id = f"{run_prefix}-001"
    latest_run_id = f"{run_prefix}-002"
    db_session.execute(
        delete(models.RawTextRewrapRun).where(
            models.RawTextRewrapRun.service_id == service_id
        )
    )
    now = datetime.now(UTC)
    db_session.add_all(
        [
            models.RawTextRewrapRun(
                rewrap_run_id=old_run_id,
                service_id=service_id,
                target_key_id="pilot-kek-20260628-002",
                source_key_ids=["pilot-kek-20260628-001"],
                included_tables=["intent_examples"],
                dry_run=True,
                approval_id=None,
                actor_id="security-operator",
                status="completed",
                scanned_count=3,
                rewrapped_count=0,
                skipped_count=1,
                failed_count=0,
                report={"RAW_TEXT_KEK_BASE64": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="},
                started_at=now - timedelta(minutes=10),
                completed_at=now - timedelta(minutes=9),
            ),
            models.RawTextRewrapRun(
                rewrap_run_id=latest_run_id,
                service_id=service_id,
                target_key_id="pilot-kek-20260628-002",
                source_key_ids=["pilot-kek-20260628-001"],
                included_tables=["intent_examples", "runtime_logs"],
                dry_run=False,
                approval_id="SEC-EXPORT-REWRAP",
                actor_id="security-operator",
                status="completed",
                scanned_count=6,
                rewrapped_count=4,
                skipped_count=2,
                failed_count=0,
                report={
                    "query_raw": "plaintext should never export",
                    "text_raw": "example plaintext should never export",
                    "query_raw_ciphertext": "ciphertext-value",
                    "query_raw_encrypted_dek": "encrypted-dek-value",
                    "legacy_kek_base64": "MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE=",
                },
                started_at=now,
                completed_at=now + timedelta(seconds=1),
            ),
        ]
    )
    db_session.commit()
    return latest_run_id
