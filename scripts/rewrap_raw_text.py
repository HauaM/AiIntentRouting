from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.db.session import create_db_engine
from intent_routing.security.encryption import EncryptedText
from intent_routing.security.keyring import load_raw_text_keyring
from intent_routing.security.rewrap import (
    apply_intent_example_encrypted_text,
    apply_runtime_log_encrypted_query,
    build_raw_text_rewrap_report,
    intent_example_encrypted_text,
    normalize_raw_text_rewrap_includes,
    raw_text_key_counts_by_table,
    raw_text_rewrap_audit_after_state,
    reencrypt_envelope,
    render_raw_text_rewrap_markdown,
    runtime_log_encrypted_query,
    source_key_ids_from_counts,
)

DEFAULT_BATCH_SIZE = 100
DEFAULT_LIMIT = 1000


@dataclass(frozen=True, slots=True)
class RawTextRewrapResult:
    report: dict[str, object]
    json_report_path: Path
    markdown_report_path: Path


@dataclass(frozen=True, slots=True)
class _RewrapCandidate:
    table_name: str
    record: models.IntentExample | models.RuntimeLog


@dataclass(slots=True)
class _RewrapCounts:
    scanned: int = 0
    rewrapped: int = 0
    skipped: int = 0
    failed: int = 0


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    keyring = load_raw_text_keyring()
    _validate_args(args, active_key_id=keyring.active_key_id)
    included_tables = normalize_raw_text_rewrap_includes(args.include)
    dry_run = not args.execute

    engine = create_db_engine(_database_url_from_env())
    try:
        with Session(engine) as session:
            result = run_raw_text_rewrap(
                session=session,
                service_id=args.service_id,
                actor_id=args.actor_id,
                report_dir=args.report_dir,
                included_tables=included_tables,
                dry_run=dry_run,
                approval_id=args.approval_id,
                batch_size=args.batch_size,
                limit=args.limit,
            )
    finally:
        engine.dispose()

    print(
        json.dumps(
            {
                "rewrap_run_id": result.report["rewrap_run_id"],
                "service_id": result.report["service_id"],
                "dry_run": result.report["dry_run"],
                "scanned_count": result.report["scanned_count"],
                "rewrapped_count": result.report["rewrapped_count"],
                "skipped_count": result.report["skipped_count"],
                "failed_count": result.report["failed_count"],
                "json_report_path": str(result.json_report_path),
                "markdown_report_path": str(result.markdown_report_path),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


def run_raw_text_rewrap(
    *,
    session: Session,
    service_id: str,
    actor_id: str,
    report_dir: Path,
    included_tables: Sequence[str],
    dry_run: bool,
    approval_id: str | None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    limit: int = DEFAULT_LIMIT,
) -> RawTextRewrapResult:
    if not included_tables:
        raise ValueError("at least one included table is required")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if not dry_run and approval_id is None:
        raise ValueError("approval_id is required for execute")

    keyring = load_raw_text_keyring()
    repository = IntentRoutingRepository(session)
    started_at = datetime.now(UTC)
    rewrap_run_id = _next_rewrap_run_id(session, started_at)
    key_counts = repository.count_raw_text_key_ids(service_id)
    source_key_ids = source_key_ids_from_counts(
        key_counts,
        included_tables=included_tables,
        active_key_id=keyring.active_key_id,
    )
    report_key_counts = raw_text_key_counts_by_table(
        key_counts,
        included_tables=included_tables,
        active_key_id=keyring.active_key_id,
    )
    run = repository.create_raw_text_rewrap_run(
        rewrap_run_id=rewrap_run_id,
        service_id=service_id,
        target_key_id=keyring.active_key_id,
        source_key_ids=source_key_ids,
        included_tables=list(included_tables),
        dry_run=dry_run,
        approval_id=approval_id,
        actor_id=actor_id,
        status="running",
        scanned_count=0,
        rewrapped_count=0,
        skipped_count=0,
        failed_count=0,
        report={},
        started_at=started_at,
        completed_at=None,
    )

    candidates = _list_candidates(
        repository,
        service_id=service_id,
        included_tables=included_tables,
        limit=limit,
    )
    counts = _process_candidates(
        candidates,
        keyring=keyring,
        dry_run=dry_run,
        batch_size=batch_size,
    )
    report = build_raw_text_rewrap_report(
        rewrap_run_id=rewrap_run_id,
        service_id=service_id,
        dry_run=dry_run,
        target_key_id=keyring.active_key_id,
        source_key_ids=source_key_ids,
        included_tables=included_tables,
        key_counts=report_key_counts,
        scanned_count=counts.scanned,
        rewrapped_count=counts.rewrapped,
        skipped_count=counts.skipped,
        failed_count=counts.failed,
    )
    completed_at = datetime.now(UTC)
    repository.complete_raw_text_rewrap_run(
        run,
        status="completed" if counts.failed == 0 else "completed_with_failures",
        scanned_count=counts.scanned,
        rewrapped_count=counts.rewrapped,
        skipped_count=counts.skipped,
        failed_count=counts.failed,
        report=report,
        completed_at=completed_at,
    )
    if not dry_run:
        assert approval_id is not None
        repository.insert_audit_log(
            event_type="raw_text.rewrap.executed",
            actor_id=actor_id,
            service_id=service_id,
            trace_id=None,
            target_type="raw_text_rewrap_run",
            target_id=rewrap_run_id,
            view_reason=None,
            source_ip=None,
            before_state=None,
            after_state=raw_text_rewrap_audit_after_state(
                report,
                approval_id=approval_id,
            ),
            created_at=completed_at,
        )

    json_report_path, markdown_report_path = _write_reports(report_dir, report)
    session.commit()
    return RawTextRewrapResult(
        report=report,
        json_report_path=json_report_path,
        markdown_report_path=markdown_report_path,
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run or execute raw text envelope rewraps."
    )
    parser.add_argument("--service-id", required=True)
    parser.add_argument("--actor-id", required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--approval-id")
    parser.add_argument("--confirm-active-key-id")
    parser.add_argument(
        "--include",
        action="append",
        choices=("intent-examples", "runtime-logs", "both"),
        required=True,
    )
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    return parser.parse_args(argv)


def _validate_args(args: argparse.Namespace, *, active_key_id: str) -> None:
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be at least 1")
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1")
    if not args.execute:
        return
    if not args.approval_id:
        raise SystemExit("--execute requires --approval-id")
    if not args.confirm_active_key_id:
        raise SystemExit("--execute requires --confirm-active-key-id")
    if args.confirm_active_key_id != active_key_id:
        raise SystemExit("--confirm-active-key-id must match active raw text key ID")


def _database_url_from_env() -> str | None:
    return os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")


def _next_rewrap_run_id(session: Session, now: datetime) -> str:
    prefix = f"rtr-{now:%Y%m%d}-"
    existing_run_ids = session.scalars(
        select(models.RawTextRewrapRun.rewrap_run_id).where(
            models.RawTextRewrapRun.rewrap_run_id.startswith(prefix)
        )
    )
    next_number = 1
    for run_id in existing_run_ids:
        suffix = run_id.removeprefix(prefix)
        if len(suffix) == 3 and suffix.isdecimal():
            next_number = max(next_number, int(suffix) + 1)
    return f"{prefix}{next_number:03d}"


def _list_candidates(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    included_tables: Sequence[str],
    limit: int,
) -> list[_RewrapCandidate]:
    candidates: list[_RewrapCandidate] = []
    remaining = limit
    if "intent_examples" in included_tables and remaining > 0:
        examples = repository.list_intent_examples_for_rewrap(
            service_id,
            limit=remaining,
        )
        candidates.extend(
            _RewrapCandidate(table_name="intent_examples", record=example)
            for example in examples
        )
        remaining -= len(examples)
    if "runtime_logs" in included_tables and remaining > 0:
        runtime_logs = repository.list_runtime_logs_for_rewrap(
            service_id,
            limit=remaining,
        )
        candidates.extend(
            _RewrapCandidate(table_name="runtime_logs", record=runtime_log)
            for runtime_log in runtime_logs
        )
    return candidates


def _process_candidates(
    candidates: Sequence[_RewrapCandidate],
    *,
    keyring: Any,
    dry_run: bool,
    batch_size: int,
) -> _RewrapCounts:
    counts = _RewrapCounts(scanned=len(candidates))
    for batch_start in range(0, len(candidates), batch_size):
        for candidate in candidates[batch_start : batch_start + batch_size]:
            encrypted = _candidate_encrypted_text(candidate)
            if encrypted is None:
                counts.failed += 1
                continue
            if encrypted.key_id == keyring.active_key_id:
                counts.skipped += 1
                continue
            if dry_run:
                continue
            try:
                rewrapped = reencrypt_envelope(encrypted, keyring)
            except Exception:
                counts.failed += 1
                continue
            _apply_candidate_encrypted_text(candidate, rewrapped)
            counts.rewrapped += 1
    return counts


def _candidate_encrypted_text(candidate: _RewrapCandidate) -> EncryptedText | None:
    if isinstance(candidate.record, models.IntentExample):
        return intent_example_encrypted_text(candidate.record)
    return runtime_log_encrypted_query(candidate.record)


def _apply_candidate_encrypted_text(
    candidate: _RewrapCandidate,
    encrypted: EncryptedText,
) -> None:
    if isinstance(candidate.record, models.IntentExample):
        apply_intent_example_encrypted_text(candidate.record, encrypted)
        return
    apply_runtime_log_encrypted_query(candidate.record, encrypted)


def _write_reports(report_dir: Path, report: dict[str, object]) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    rewrap_run_id = str(report["rewrap_run_id"])
    json_path = report_dir / f"raw-text-rewrap-{rewrap_run_id}.json"
    markdown_path = report_dir / f"raw-text-rewrap-{rewrap_run_id}.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_raw_text_rewrap_markdown(report),
        encoding="utf-8",
    )
    return json_path, markdown_path


if __name__ == "__main__":
    main()
