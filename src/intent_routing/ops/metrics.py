from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.orm import Session

from intent_routing.db import models
from intent_routing.domain.enums import Decision

DECISION_COUNT_KEYS = tuple(decision.value for decision in Decision)


def empty_runtime_metrics(service_id: str, window_hours: int) -> dict[str, Any]:
    return {
        "service_id": service_id,
        "window_hours": window_hours,
        "request_count": 0,
        "decision_counts": {decision: 0 for decision in DECISION_COUNT_KEYS},
        "error_counts": {},
        "latency_ms": {"p50": None, "p95": None, "max": None},
        "top_route_keys": [],
        "raw_query_retention": {"encrypted_count": 0, "redacted_count": 0},
    }


def runtime_metrics_for_service(
    session: Session,
    service_id: str,
    *,
    window_hours: int,
    top_route_limit: int = 10,
) -> dict[str, Any]:
    metrics = empty_runtime_metrics(service_id, window_hours)
    params = {"service_id": service_id, "window_hours": window_hours}
    summary = session.execute(
        text(
            """
            SELECT count(*) AS request_count,
                   percentile_disc(0.5) WITHIN GROUP (ORDER BY latency_ms) AS p50,
                   percentile_disc(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95,
                   max(latency_ms) AS max_latency_ms,
                   count(*) FILTER (
                       WHERE raw_query_deleted_at IS NULL
                         AND query_raw_ciphertext IS NOT NULL
                         AND query_raw_encrypted_dek IS NOT NULL
                         AND query_raw_encrypted_dek_iv IS NOT NULL
                         AND query_raw_encrypted_dek_auth_tag IS NOT NULL
                         AND query_raw_key_id IS NOT NULL
                         AND query_raw_iv IS NOT NULL
                         AND query_raw_auth_tag IS NOT NULL
                         AND query_raw_algorithm IS NOT NULL
                   ) AS encrypted_count,
                   count(*) FILTER (
                       WHERE raw_query_deleted_at IS NOT NULL
                   ) AS redacted_count
            FROM runtime_logs
            WHERE service_id = :service_id
              AND created_at >= now() - (CAST(:window_hours AS integer) * interval '1 hour')
            """
        ),
        params,
    ).mappings().one()
    metrics["request_count"] = int(summary["request_count"] or 0)
    metrics["latency_ms"] = {
        "p50": _optional_int(summary["p50"]),
        "p95": _optional_int(summary["p95"]),
        "max": _optional_int(summary["max_latency_ms"]),
    }
    metrics["raw_query_retention"] = {
        "encrypted_count": int(summary["encrypted_count"] or 0),
        "redacted_count": int(summary["redacted_count"] or 0),
    }
    metrics["decision_counts"] = _decision_counts(session, params)
    metrics["error_counts"] = _named_counts(
        session,
        """
        SELECT error_code AS name,
               count(*) AS count
        FROM runtime_logs
        WHERE service_id = :service_id
          AND created_at >= now() - (CAST(:window_hours AS integer) * interval '1 hour')
          AND error_code IS NOT NULL
        GROUP BY error_code
        ORDER BY error_code
        """,
        params,
    )
    metrics["top_route_keys"] = _top_route_keys(
        session,
        params | {"top_route_limit": top_route_limit},
    )
    return metrics


def raw_text_key_summary_from_counts(
    *,
    service_id: str,
    active_key_id: str | None,
    counts: Mapping[str, object],
) -> dict[str, Any]:
    runtime_logs = [
        {"key_id": key_id, "count": count}
        for key_id, count in _key_counts(
            counts.get("runtime_logs"),
            active_key_id=active_key_id,
        ).items()
    ]
    redacted_count = int(cast("int | None", counts.get("runtime_logs_redacted")) or 0)
    if redacted_count:
        runtime_logs.append(
            {
                "key_id": None,
                "count": redacted_count,
                "state": "raw_query_redacted",
            }
        )
    return {
        "service_id": service_id,
        "active_key_id": active_key_id,
        "intent_examples": [
            {"key_id": key_id, "count": count}
            for key_id, count in _key_counts(
                counts.get("intent_examples"),
                active_key_id=active_key_id,
            ).items()
        ],
        "runtime_logs": runtime_logs,
    }


def safe_audit_log_item(audit_log: models.AuditLog) -> dict[str, Any]:
    return {
        "audit_id": str(audit_log.audit_id),
        "event_type": audit_log.event_type,
        "actor_id": audit_log.actor_id,
        "service_id": audit_log.service_id,
        "trace_id": audit_log.trace_id,
        "target_type": audit_log.target_type,
        "target_id": audit_log.target_id,
        "view_reason": audit_log.view_reason,
        "source_ip": audit_log.source_ip,
        "created_at": audit_log.created_at,
    }


def _decision_counts(session: Session, params: Mapping[str, object]) -> dict[str, int]:
    counts = {decision: 0 for decision in DECISION_COUNT_KEYS}
    counts.update(
        _named_counts(
            session,
            """
            SELECT decision AS name,
                   count(*) AS count
            FROM runtime_logs
            WHERE service_id = :service_id
              AND created_at >= now() - (CAST(:window_hours AS integer) * interval '1 hour')
              AND decision IS NOT NULL
            GROUP BY decision
            ORDER BY decision
            """,
            params,
        )
    )
    return counts


def _top_route_keys(
    session: Session,
    params: Mapping[str, object],
) -> list[dict[str, Any]]:
    rows = session.execute(
        text(
            """
            SELECT route_key,
                   count(*) AS count
            FROM runtime_logs
            WHERE service_id = :service_id
              AND created_at >= now() - (CAST(:window_hours AS integer) * interval '1 hour')
              AND route_key IS NOT NULL
            GROUP BY route_key
            ORDER BY count(*) DESC, route_key
            LIMIT :top_route_limit
            """
        ),
        params,
    ).mappings()
    return [
        {"route_key": row["route_key"], "count": int(row["count"])}
        for row in rows
    ]


def _named_counts(
    session: Session,
    query: str,
    params: Mapping[str, object],
) -> dict[str, int]:
    rows = session.execute(text(query), params).mappings()
    return {
        cast("str", row["name"]): int(row["count"])
        for row in rows
        if row["name"] is not None
    }


def _key_counts(value: object, *, active_key_id: str | None) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    return {
        str(key): int(count)
        for key, count in sorted(
            value.items(),
            key=lambda item: (str(item[0]) != active_key_id, str(item[0])),
        )
    }


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)
