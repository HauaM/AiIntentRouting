from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from intent_routing.db import models
from intent_routing.db.session import create_db_engine
from intent_routing.ops.admin_client import AdminApiClient
from intent_routing.ops.evidence import (
    render_ops_evidence_json,
    render_ops_evidence_markdown,
)

DEFAULT_AUDIT_LIMIT = 50
DEFAULT_REWRAP_LIMIT = 5


def run_ops_evidence_export(
    *,
    base_url: str,
    admin_token: str,
    service_id: str,
    out_dir: Path,
    window_hours: int,
    actor_id: str,
    environment: str,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    if window_hours < 1:
        raise ValueError("window_hours must be at least 1")

    out_dir.mkdir(parents=True, exist_ok=True)
    readyz = _get_json(base_url, "/readyz", transport=transport)
    with AdminApiClient(
        base_url=base_url,
        admin_token=admin_token,
        actor_id=actor_id,
        actor_roles="system_admin",
        service_scope=service_id,
        transport=transport,
    ) as client:
        active_release = client.get(
            f"/admin/v1/services/{service_id}/releases/active",
            params={"environment": environment},
        )
        runtime_metrics = client.get(
            f"/admin/v1/services/{service_id}/runtime-metrics",
            params={"window_hours": window_hours},
        )
        raw_text_key_summary = client.get(
            f"/admin/v1/services/{service_id}/security/raw-text-key-summary"
        )
        audit_logs = client.get(
            f"/admin/v1/services/{service_id}/audit-logs",
            params={"limit": DEFAULT_AUDIT_LIMIT},
        )

    payload = {
        "service_id": service_id,
        "environment": environment,
        "collected_at": datetime.now(UTC).isoformat(),
        "window_hours": window_hours,
        "actor_id": actor_id,
        "readyz": readyz,
        "active_release": active_release,
        "runtime_metrics": runtime_metrics,
        "raw_text_key_summary": raw_text_key_summary,
        "latest_rewrap_runs": _latest_rewrap_run_summaries(
            service_id=service_id,
            limit=DEFAULT_REWRAP_LIMIT,
        ),
        "runtime_raw_query_retention": _raw_query_retention(runtime_metrics),
        "audit_evidence": {
            "count": len(audit_logs) if isinstance(audit_logs, list) else 0,
            "events": audit_logs if isinstance(audit_logs, list) else [],
        },
        "plaintext_exported": False,
    }
    json_path = out_dir / "ops-evidence.json"
    markdown_path = out_dir / "ops-evidence.md"
    json_path.write_text(render_ops_evidence_json(payload), encoding="utf-8")
    markdown_path.write_text(render_ops_evidence_markdown(payload), encoding="utf-8")
    return {
        "payload": payload,
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    admin_token = args.admin_token or os.environ.get("ADMIN_BOOTSTRAP_TOKEN")
    if not admin_token:
        raise SystemExit("--admin-token or ADMIN_BOOTSTRAP_TOKEN is required")
    result = run_ops_evidence_export(
        base_url=args.base_url,
        admin_token=admin_token,
        service_id=args.service_id,
        out_dir=args.out_dir,
        window_hours=args.window_hours,
        actor_id=args.actor_id,
        environment=args.environment,
    )
    print(
        json.dumps(
            {
                "json_path": result["json_path"],
                "markdown_path": result["markdown_path"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export redacted operations evidence for a service."
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--admin-token")
    parser.add_argument("--service-id", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--window-hours", type=int, default=24)
    parser.add_argument("--actor-id", default="ops-evidence")
    parser.add_argument(
        "--environment",
        default=os.environ.get("INTENT_ROUTING_ENVIRONMENT", "dev"),
        help="Release environment for active release lookup.",
    )
    return parser.parse_args(argv)


def _get_json(
    base_url: str,
    path: str,
    *,
    transport: httpx.BaseTransport | None,
) -> dict[str, Any]:
    with httpx.Client(
        base_url=base_url.rstrip("/"),
        timeout=8.0,
        transport=transport,
    ) as client:
        response = client.get(path)
    if response.status_code >= 400:
        raise RuntimeError(f"{response.status_code} HTTP_ERROR {response.text}")
    body = response.json()
    status_text = body.get("status") if isinstance(body, Mapping) else None
    return {
        "status_code": response.status_code,
        "status": status_text,
        "body": body,
    }


def _latest_rewrap_run_summaries(
    *,
    service_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    database_url = _database_url_from_env()
    if database_url is None:
        return []
    engine = create_db_engine(database_url)
    try:
        with Session(engine) as session:
            runs = list(
                session.scalars(
                    select(models.RawTextRewrapRun)
                    .where(models.RawTextRewrapRun.service_id == service_id)
                    .order_by(
                        models.RawTextRewrapRun.started_at.desc(),
                        models.RawTextRewrapRun.rewrap_run_id.desc(),
                    )
                    .limit(limit)
                )
            )
            return [_rewrap_run_summary(run) for run in runs]
    finally:
        engine.dispose()


def _rewrap_run_summary(run: models.RawTextRewrapRun) -> dict[str, Any]:
    return {
        "rewrap_run_id": run.rewrap_run_id,
        "service_id": run.service_id,
        "target_key_id": run.target_key_id,
        "source_key_ids": list(run.source_key_ids or []),
        "included_tables": list(run.included_tables or []),
        "dry_run": run.dry_run,
        "approval_id": run.approval_id,
        "actor_id": run.actor_id,
        "status": run.status,
        "scanned_count": run.scanned_count,
        "rewrapped_count": run.rewrapped_count,
        "skipped_count": run.skipped_count,
        "failed_count": run.failed_count,
        "started_at": _isoformat(run.started_at),
        "completed_at": _isoformat(run.completed_at),
    }


def _database_url_from_env() -> str | None:
    return os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")


def _raw_query_retention(metrics: Any) -> Mapping[str, Any]:
    if not isinstance(metrics, Mapping):
        return {"encrypted_count": 0, "redacted_count": 0}
    retention = metrics.get("raw_query_retention")
    if isinstance(retention, Mapping):
        return retention
    return {"encrypted_count": 0, "redacted_count": 0}


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


if __name__ == "__main__":
    main()
