from datetime import UTC, datetime

from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository


def test_runtime_log_exposes_raw_query_deletion_metadata_fields() -> None:
    deleted_at = datetime.now(UTC)

    runtime_log = models.RuntimeLog(
        raw_query_deleted_at=deleted_at,
        raw_query_deleted_by="retention-job",
        raw_query_delete_reason="expired after retention window",
    )

    assert {
        "raw_query_deleted_at",
        "raw_query_deleted_by",
        "raw_query_delete_reason",
    }.issubset(models.RuntimeLog.__table__.columns.keys())
    assert runtime_log.raw_query_deleted_at == deleted_at
    assert runtime_log.raw_query_deleted_by == "retention-job"
    assert runtime_log.raw_query_delete_reason == "expired after retention window"


def test_raw_text_rewrap_run_model_exposes_lifecycle_fields() -> None:
    started_at = datetime.now(UTC)

    run = models.RawTextRewrapRun(
        rewrap_run_id="rewrap-test",
        service_id="svc-test",
        target_key_id="key-new",
        source_key_ids=["key-old"],
        included_tables=["intent_examples", "runtime_logs"],
        dry_run=True,
        approval_id=None,
        actor_id="security-admin",
        status="running",
        scanned_count=0,
        rewrapped_count=0,
        skipped_count=0,
        failed_count=0,
        report={},
        started_at=started_at,
        completed_at=None,
    )

    assert {
        "rewrap_run_id",
        "service_id",
        "target_key_id",
        "source_key_ids",
        "included_tables",
        "dry_run",
        "approval_id",
        "actor_id",
        "status",
        "scanned_count",
        "rewrapped_count",
        "skipped_count",
        "failed_count",
        "report",
        "started_at",
        "completed_at",
    }.issubset(models.RawTextRewrapRun.__table__.columns.keys())
    assert run.source_key_ids == ["key-old"]
    assert run.included_tables == ["intent_examples", "runtime_logs"]
    assert run.report == {}


def test_repository_exposes_security_lifecycle_methods() -> None:
    assert {
        "create_raw_text_rewrap_run",
        "complete_raw_text_rewrap_run",
        "list_intent_examples_for_rewrap",
        "list_runtime_logs_for_rewrap",
        "count_raw_text_key_ids",
        "list_audit_logs",
        "redact_runtime_raw_queries",
    }.issubset(dir(IntentRoutingRepository))
