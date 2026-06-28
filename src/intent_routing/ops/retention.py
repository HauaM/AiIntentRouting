from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository


@dataclass(frozen=True, slots=True)
class RuntimeRawQueryRetentionPlan:
    service_id: str
    older_than_days: int
    eligible_trace_ids: Sequence[str]
    already_redacted_count: int


def plan_runtime_raw_query_redaction(
    repository: IntentRoutingRepository,
    service_id: str,
    older_than_days: int,
    limit: int,
) -> RuntimeRawQueryRetentionPlan:
    if older_than_days < 0:
        raise ValueError("older_than_days must be non-negative")
    if limit < 1:
        raise ValueError("limit must be at least 1")

    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    eligible_trace_ids = list(
        repository.session.scalars(
            select(models.RuntimeLog.trace_id)
            .where(models.RuntimeLog.service_id == service_id)
            .where(models.RuntimeLog.created_at < cutoff)
            .where(models.RuntimeLog.raw_query_deleted_at.is_(None))
            .where(*_complete_raw_query_envelope_filters())
            .order_by(models.RuntimeLog.created_at, models.RuntimeLog.trace_id)
            .limit(limit)
        )
    )
    already_redacted_count = repository.session.scalar(
        select(func.count(models.RuntimeLog.trace_id))
        .where(models.RuntimeLog.service_id == service_id)
        .where(models.RuntimeLog.created_at < cutoff)
        .where(models.RuntimeLog.raw_query_deleted_at.is_not(None))
    )
    return RuntimeRawQueryRetentionPlan(
        service_id=service_id,
        older_than_days=older_than_days,
        eligible_trace_ids=eligible_trace_ids,
        already_redacted_count=int(already_redacted_count or 0),
    )


def apply_runtime_raw_query_redaction(
    repository: IntentRoutingRepository,
    service_id: str,
    trace_ids: Sequence[str],
    actor_id: str,
    reason: str,
) -> int:
    trace_id_values = tuple(dict.fromkeys(trace_ids))
    if not trace_id_values:
        return 0

    deleted_at = datetime.now(UTC)
    redacted_trace_ids = repository.redact_runtime_raw_query_trace_ids(
        service_id,
        trace_ids=trace_id_values,
        actor_id=actor_id,
        reason=reason,
        deleted_at=deleted_at,
    )
    for trace_id in redacted_trace_ids:
        repository.insert_audit_log(
            event_type="runtime_log.raw_query_redacted",
            actor_id=actor_id,
            service_id=service_id,
            trace_id=trace_id,
            target_type="runtime_log",
            target_id=trace_id,
            view_reason=None,
            source_ip=None,
            before_state=None,
            after_state={
                "trace_id": trace_id,
                "service_id": service_id,
                "raw_query_redacted": True,
                "reason": reason,
            },
            created_at=deleted_at,
        )
    return len(redacted_trace_ids)


def _complete_raw_query_envelope_filters() -> tuple[Any, ...]:
    return (
        models.RuntimeLog.query_raw_ciphertext.is_not(None),
        models.RuntimeLog.query_raw_encrypted_dek.is_not(None),
        models.RuntimeLog.query_raw_encrypted_dek_iv.is_not(None),
        models.RuntimeLog.query_raw_encrypted_dek_auth_tag.is_not(None),
        models.RuntimeLog.query_raw_key_id.is_not(None),
        models.RuntimeLog.query_raw_iv.is_not(None),
        models.RuntimeLog.query_raw_auth_tag.is_not(None),
        models.RuntimeLog.query_raw_algorithm.is_not(None),
    )
