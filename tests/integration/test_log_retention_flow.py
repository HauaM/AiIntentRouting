from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from scripts import apply_log_retention
from tests.integration.test_trace_audit_logs import (
    _auditor_headers,
    _client,
    _operator_headers,
)

ACTOR_ID = "security-operator"
APPROVAL_ID = "SEC-20260628-RETENTION-001"
RAW_QUERY_LEAK_MARKERS = (
    "legacy runtime bearer token query",
    "Bearer live-runtime-token",
    "irt_live_secret_api_key_value",
    "query_raw",
    "ciphertext",
    "encrypted_dek",
    "RAW_TEXT_KEK_BASE64",
)


def test_runtime_raw_query_retention_dry_run_execute_and_admin_flow(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    service_id = f"it-helpdesk-pilot-{uuid4().hex}"
    other_service_id = f"{service_id}-other"
    now = datetime.now(UTC)
    eligible_trace_id = f"trace-retention-eligible-{uuid4().hex}"
    already_redacted_trace_id = f"trace-retention-redacted-{uuid4().hex}"
    recent_trace_id = f"trace-retention-recent-{uuid4().hex}"
    other_trace_id = f"trace-retention-other-{uuid4().hex}"
    _seed_retention_fixture(
        db_session,
        service_id=service_id,
        other_service_id=other_service_id,
        eligible_trace_id=eligible_trace_id,
        already_redacted_trace_id=already_redacted_trace_id,
        recent_trace_id=recent_trace_id,
        other_trace_id=other_trace_id,
        now=now,
    )
    before_eligible = _runtime_log(db_session, eligible_trace_id)
    assert before_eligible is not None
    before_ciphertext = before_eligible.query_raw_ciphertext
    before_deleted_at = before_eligible.raw_query_deleted_at

    apply_log_retention.main(
        [
            "--service-id",
            service_id,
            "--older-than-days",
            "30",
            "--limit",
            "500",
            "--actor-id",
            ACTOR_ID,
            "--reason",
            "raw query retention policy 30 days",
            "--report-dir",
            str(tmp_path),
        ]
    )

    dry_run_stdout = capsys.readouterr().out
    db_session.expire_all()
    dry_run_report, dry_run_markdown = _latest_reports(tmp_path)
    after_dry_run = _runtime_log(db_session, eligible_trace_id)
    assert after_dry_run is not None
    assert after_dry_run.query_raw_ciphertext == before_ciphertext
    assert after_dry_run.raw_query_deleted_at == before_deleted_at
    assert dry_run_report["dry_run"] is True
    assert dry_run_report["service_id"] == service_id
    assert dry_run_report["actor_id"] == ACTOR_ID
    assert dry_run_report["approval_id"] is None
    assert dry_run_report["eligible_trace_ids"] == [eligible_trace_id]
    assert dry_run_report["eligible_count"] == 1
    assert dry_run_report["already_redacted_count"] == 1
    assert dry_run_report["redacted_count"] == 0
    assert "started_at" in dry_run_report
    assert "completed_at" in dry_run_report
    assert eligible_trace_id in dry_run_markdown
    _assert_no_sensitive_material(dry_run_stdout, dry_run_report, dry_run_markdown)

    apply_log_retention.main(
        [
            "--service-id",
            service_id,
            "--older-than-days",
            "30",
            "--limit",
            "500",
            "--actor-id",
            ACTOR_ID,
            "--reason",
            "raw query retention policy 30 days",
            "--report-dir",
            str(tmp_path),
            "--execute",
            "--approval-id",
            APPROVAL_ID,
        ]
    )

    execute_stdout = capsys.readouterr().out
    db_session.expire_all()
    execute_report, execute_markdown = _latest_reports(tmp_path)
    eligible_log = _runtime_log(db_session, eligible_trace_id)
    already_redacted_log = _runtime_log(db_session, already_redacted_trace_id)
    recent_log = _runtime_log(db_session, recent_trace_id)
    other_log = _runtime_log(db_session, other_trace_id)
    assert eligible_log is not None
    assert already_redacted_log is not None
    assert recent_log is not None
    assert other_log is not None
    assert eligible_log.query_raw_ciphertext is None
    assert eligible_log.query_raw_encrypted_dek is None
    assert eligible_log.query_raw_encrypted_dek_iv is None
    assert eligible_log.query_raw_encrypted_dek_auth_tag is None
    assert eligible_log.query_raw_key_id is None
    assert eligible_log.query_raw_iv is None
    assert eligible_log.query_raw_auth_tag is None
    assert eligible_log.query_raw_algorithm is None
    assert eligible_log.raw_query_deleted_at is not None
    assert eligible_log.raw_query_deleted_by == ACTOR_ID
    assert eligible_log.raw_query_delete_reason == "raw query retention policy 30 days"
    assert eligible_log.query_masked == "legacy runtime bearer token [REDACTED]"
    assert already_redacted_log.raw_query_deleted_by == "previous-retention-job"
    assert recent_log.query_raw_ciphertext is not None
    assert recent_log.raw_query_deleted_at is None
    assert other_log.query_raw_ciphertext is not None
    assert other_log.raw_query_deleted_at is None
    assert execute_report["dry_run"] is False
    assert execute_report["approval_id"] == APPROVAL_ID
    assert execute_report["eligible_trace_ids"] == [eligible_trace_id]
    assert execute_report["redacted_count"] == 1
    assert execute_report["already_redacted_count"] == 1
    assert "completed_at" in execute_report
    assert APPROVAL_ID in execute_markdown
    _assert_no_sensitive_material(execute_stdout, execute_report, execute_markdown)

    client = _client(db_session, monkeypatch)
    masked_response = client.get(
        f"/admin/v1/services/{service_id}/runtime-logs/{eligible_trace_id}",
        headers=_operator_headers(service_id),
    )
    decrypt_response = client.post(
        f"/admin/v1/services/{service_id}/runtime-logs/{eligible_trace_id}:decrypt-raw-query",
        headers=_auditor_headers(service_id),
        json={"view_reason": "incident follow-up ticket INC-20260628-001"},
    )

    masked_body = masked_response.json()
    decrypt_body = decrypt_response.json()
    assert masked_response.status_code == 200
    assert masked_body["trace_id"] == eligible_trace_id
    assert masked_body["query_masked"] == "legacy runtime bearer token [REDACTED]"
    assert "query_raw" not in masked_body
    assert decrypt_response.status_code == 410
    assert decrypt_body["status"] == "error"
    assert decrypt_body["error"]["code"] == "RAW_QUERY_UNAVAILABLE"
    assert "decision" not in decrypt_body
    assert "query_raw" not in decrypt_response.text

    retention_audit_log = db_session.scalar(
        select(models.AuditLog)
        .where(models.AuditLog.service_id == service_id)
        .where(models.AuditLog.trace_id == eligible_trace_id)
        .where(models.AuditLog.event_type == "runtime_log.raw_query_redacted")
    )
    viewed_audit_log = db_session.scalar(
        select(models.AuditLog)
        .where(models.AuditLog.service_id == service_id)
        .where(models.AuditLog.trace_id == eligible_trace_id)
        .where(models.AuditLog.event_type == "raw_query.viewed")
    )
    assert retention_audit_log is not None
    assert retention_audit_log.actor_id == ACTOR_ID
    assert retention_audit_log.target_type == "runtime_log"
    assert retention_audit_log.target_id == eligible_trace_id
    assert retention_audit_log.after_state == {
        "trace_id": eligible_trace_id,
        "service_id": service_id,
        "raw_query_redacted": True,
        "reason": "raw query retention policy 30 days",
    }
    assert viewed_audit_log is None


def test_execute_requires_approval_id_and_explicit_database_url(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    service_id = f"it-helpdesk-pilot-{uuid4().hex}"
    _seed_retention_fixture(
        db_session,
        service_id=service_id,
        other_service_id=f"{service_id}-other",
        eligible_trace_id=f"trace-retention-eligible-{uuid4().hex}",
        already_redacted_trace_id=f"trace-retention-redacted-{uuid4().hex}",
        recent_trace_id=f"trace-retention-recent-{uuid4().hex}",
        other_trace_id=f"trace-retention-other-{uuid4().hex}",
        now=datetime.now(UTC),
    )
    required_args = [
        "--service-id",
        service_id,
        "--older-than-days",
        "30",
        "--limit",
        "500",
        "--actor-id",
        ACTOR_ID,
        "--reason",
        "raw query retention policy 30 days",
        "--report-dir",
        str(tmp_path),
        "--execute",
    ]

    with pytest.raises(SystemExit, match="--execute requires --approval-id"):
        apply_log_retention.main(required_args)

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    with pytest.raises(SystemExit, match="--execute requires DATABASE_URL"):
        apply_log_retention.main([*required_args, "--approval-id", APPROVAL_ID])

    assert not list(tmp_path.iterdir())


def _seed_retention_fixture(
    db_session: Session,
    *,
    service_id: str,
    other_service_id: str,
    eligible_trace_id: str,
    already_redacted_trace_id: str,
    recent_trace_id: str,
    other_trace_id: str,
    now: datetime,
) -> None:
    repository = IntentRoutingRepository(db_session)
    for created_service_id in (service_id, other_service_id):
        repository.create_service(
            service_id=created_service_id,
            display_name="IT Helpdesk Pilot",
            environment="prod",
            default_threshold_preset="balanced",
            max_input_tokens=256,
            status="active",
            created_by="retention-test",
            created_at=now,
            updated_at=now,
        )
    _create_runtime_log(
        repository,
        service_id=service_id,
        trace_id=eligible_trace_id,
        masked="legacy runtime bearer token [REDACTED]",
        created_at=now - timedelta(days=31),
    )
    repository.insert_runtime_log(
        trace_id=already_redacted_trace_id,
        service_id=service_id,
        latency_ms=10,
        query_masked="already redacted runtime query",
        raw_query_deleted_at=now - timedelta(days=1),
        raw_query_deleted_by="previous-retention-job",
        raw_query_delete_reason="previous retention policy",
        created_at=now - timedelta(days=32),
    )
    _create_runtime_log(
        repository,
        service_id=service_id,
        trace_id=recent_trace_id,
        masked="recent runtime query",
        created_at=now - timedelta(days=3),
    )
    _create_runtime_log(
        repository,
        service_id=other_service_id,
        trace_id=other_trace_id,
        masked="other service runtime query",
        created_at=now - timedelta(days=40),
    )
    db_session.commit()


def _create_runtime_log(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    trace_id: str,
    masked: str,
    created_at: datetime,
) -> None:
    repository.insert_runtime_log(
        trace_id=trace_id,
        service_id=service_id,
        latency_ms=10,
        query_raw_ciphertext=b"legacy runtime bearer token query ciphertext",
        query_raw_encrypted_dek=b"runtime encrypted dek",
        query_raw_encrypted_dek_iv=b"runtime encrypted dek iv",
        query_raw_encrypted_dek_auth_tag=b"runtime encrypted dek tag",
        query_raw_key_id="retention-kek-001",
        query_raw_iv=b"runtime query iv",
        query_raw_auth_tag=b"runtime query tag",
        query_raw_algorithm="AES-GCM",
        query_masked=masked,
        created_at=created_at,
    )


def _runtime_log(db_session: Session, trace_id: str) -> models.RuntimeLog | None:
    return db_session.scalar(
        select(models.RuntimeLog).where(models.RuntimeLog.trace_id == trace_id)
    )


def _latest_reports(report_dir: Path) -> tuple[dict[str, object], str]:
    json_reports = sorted(report_dir.glob("runtime-raw-query-retention-*.json"))
    markdown_reports = sorted(report_dir.glob("runtime-raw-query-retention-*.md"))
    assert json_reports
    assert len(json_reports) == len(markdown_reports)
    return (
        json.loads(json_reports[-1].read_text(encoding="utf-8")),
        markdown_reports[-1].read_text(encoding="utf-8"),
    )


def _assert_no_sensitive_material(
    stdout: str,
    report: dict[str, object],
    markdown_report: str,
) -> None:
    serialized_report = json.dumps(report, ensure_ascii=False, sort_keys=True)
    for marker in RAW_QUERY_LEAK_MARKERS:
        assert marker not in stdout
        assert marker not in serialized_report
        assert marker not in markdown_report
