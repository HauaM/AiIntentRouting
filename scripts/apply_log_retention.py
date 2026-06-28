from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.db.session import create_db_engine
from intent_routing.ops.retention import (
    RuntimeRawQueryRetentionPlan,
    apply_runtime_raw_query_redaction,
    plan_runtime_raw_query_redaction,
)


@dataclass(frozen=True, slots=True)
class RuntimeRawQueryRetentionResult:
    report: dict[str, object]
    json_report_path: Path
    markdown_report_path: Path


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    database_url = _database_url_from_env()
    _validate_args(args, database_url=database_url)

    engine = create_db_engine(database_url)
    try:
        with Session(engine) as session:
            result = run_runtime_raw_query_retention(
                session=session,
                service_id=args.service_id,
                older_than_days=args.older_than_days,
                limit=args.limit,
                actor_id=args.actor_id,
                reason=args.reason,
                report_dir=args.report_dir,
                dry_run=not args.execute,
                approval_id=args.approval_id,
            )
    finally:
        engine.dispose()

    print(
        json.dumps(
            {
                "retention_run_id": result.report["retention_run_id"],
                "service_id": result.report["service_id"],
                "dry_run": result.report["dry_run"],
                "eligible_count": result.report["eligible_count"],
                "already_redacted_count": result.report["already_redacted_count"],
                "redacted_count": result.report["redacted_count"],
                "json_report_path": str(result.json_report_path),
                "markdown_report_path": str(result.markdown_report_path),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


def run_runtime_raw_query_retention(
    *,
    session: Session,
    service_id: str,
    older_than_days: int,
    limit: int,
    actor_id: str,
    reason: str,
    report_dir: Path,
    dry_run: bool,
    approval_id: str | None,
) -> RuntimeRawQueryRetentionResult:
    if older_than_days < 1:
        raise ValueError("older_than_days must be at least 1")
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if not dry_run and approval_id is None:
        raise ValueError("approval_id is required for execute")

    repository = IntentRoutingRepository(session)
    started_at = datetime.now(UTC)
    retention_run_id = f"rrq-{started_at:%Y%m%d%H%M%S%f}"
    plan = plan_runtime_raw_query_redaction(
        repository,
        service_id=service_id,
        older_than_days=older_than_days,
        limit=limit,
    )
    redacted_count = 0
    if not dry_run:
        redacted_count = apply_runtime_raw_query_redaction(
            repository,
            service_id=service_id,
            trace_ids=plan.eligible_trace_ids,
            actor_id=actor_id,
            reason=reason,
        )
    completed_at = datetime.now(UTC)
    report = _build_report(
        retention_run_id=retention_run_id,
        plan=plan,
        dry_run=dry_run,
        actor_id=actor_id,
        reason=reason,
        approval_id=approval_id,
        limit=limit,
        redacted_count=redacted_count,
        started_at=started_at,
        completed_at=completed_at,
    )
    json_report_path, markdown_report_path = _write_reports(report_dir, report)
    session.commit()
    return RuntimeRawQueryRetentionResult(
        report=report,
        json_report_path=json_report_path,
        markdown_report_path=markdown_report_path,
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run or execute runtime raw query retention redaction."
    )
    parser.add_argument("--service-id", required=True)
    parser.add_argument("--older-than-days", type=int, required=True)
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--actor-id", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--approval-id")
    return parser.parse_args(argv)


def _validate_args(args: argparse.Namespace, *, database_url: str | None) -> None:
    if args.older_than_days < 1:
        raise SystemExit("--older-than-days must be at least 1")
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1")
    if not args.execute:
        return
    if not args.approval_id:
        raise SystemExit("--execute requires --approval-id")
    if database_url is None:
        raise SystemExit("--execute requires DATABASE_URL or TEST_DATABASE_URL")


def _database_url_from_env() -> str | None:
    return os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")


def _build_report(
    *,
    retention_run_id: str,
    plan: RuntimeRawQueryRetentionPlan,
    dry_run: bool,
    actor_id: str,
    reason: str,
    approval_id: str | None,
    limit: int,
    redacted_count: int,
    started_at: datetime,
    completed_at: datetime,
) -> dict[str, object]:
    return {
        "retention_run_id": retention_run_id,
        "service_id": plan.service_id,
        "dry_run": dry_run,
        "status": "dry_run" if dry_run else "completed",
        "older_than_days": plan.older_than_days,
        "limit": limit,
        "eligible_trace_ids": list(plan.eligible_trace_ids),
        "eligible_count": len(plan.eligible_trace_ids),
        "already_redacted_count": plan.already_redacted_count,
        "redacted_count": redacted_count,
        "actor_id": actor_id,
        "approval_id": approval_id,
        "reason": reason,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "plaintext_exported": False,
    }


def _write_reports(report_dir: Path, report: dict[str, object]) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    retention_run_id = str(report["retention_run_id"])
    json_path = report_dir / f"runtime-raw-query-retention-{retention_run_id}.json"
    markdown_path = report_dir / f"runtime-raw-query-retention-{retention_run_id}.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def _render_markdown(report: dict[str, object]) -> str:
    trace_ids = report.get("eligible_trace_ids", [])
    trace_lines = ["| Trace ID |", "| --- |"]
    if isinstance(trace_ids, list) and trace_ids:
        trace_lines.extend(f"| {trace_id} |" for trace_id in trace_ids)
    else:
        trace_lines.append("| None |")
    return "\n".join(
        [
            "# Runtime Raw Query Retention Report",
            "",
            f"- Run ID: {report['retention_run_id']}",
            f"- Service ID: {report['service_id']}",
            f"- Dry run: {report['dry_run']}",
            f"- Status: {report['status']}",
            f"- Older than days: {report['older_than_days']}",
            f"- Limit: {report['limit']}",
            f"- Eligible count: {report['eligible_count']}",
            f"- Already redacted count: {report['already_redacted_count']}",
            f"- Redacted count: {report['redacted_count']}",
            f"- Actor ID: {report['actor_id']}",
            f"- Approval ID: {report['approval_id']}",
            f"- Reason: {report['reason']}",
            f"- Started at: {report['started_at']}",
            f"- Completed at: {report['completed_at']}",
            f"- Plaintext exported: {report['plaintext_exported']}",
            "",
            "## Eligible Trace IDs",
            "",
            *trace_lines,
            "",
        ]
    )


if __name__ == "__main__":
    main()
