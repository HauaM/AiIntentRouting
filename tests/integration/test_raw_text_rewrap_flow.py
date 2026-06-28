from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.security.encryption import EncryptedText, EnvelopeEncryptor
from intent_routing.security.keyring import RawTextKeyring
from intent_routing.security.rewrap import (
    intent_example_encrypted_text,
    runtime_log_encrypted_query,
)
from scripts import rewrap_raw_text

LEGACY_KEY_ID = "pilot-kek-20260628-001"
ACTIVE_KEY_ID = "pilot-kek-20260628-002"
APPROVAL_ID = "SEC-20260628-REWRAP-001"
ACTOR_ID = "security-operator"
LEAK_MARKERS = (
    "legacy example password reset text",
    "legacy runtime bearer token query",
    "irt_live_secret_api_key_value",
    "Bearer live-runtime-token",
    "RAW_TEXT_KEK_BASE64",
)


def test_dry_run_reports_legacy_counts_and_writes_no_data_changes(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy_kek = _kek(b"1")
    active_kek = _kek(b"2")
    service_id = _seed_rewrap_fixture(
        db_session,
        legacy_kek=legacy_kek,
        active_kek=active_kek,
    )
    before_examples = _example_envelopes(db_session, service_id)
    before_logs = _runtime_log_envelopes(db_session, service_id)
    _configure_keyring(monkeypatch, legacy_kek=legacy_kek, active_kek=active_kek)

    rewrap_raw_text.main(
        [
            "--service-id",
            service_id,
            "--actor-id",
            ACTOR_ID,
            "--report-dir",
            str(tmp_path),
            "--include",
            "both",
            "--batch-size",
            "2",
            "--limit",
            "20",
        ]
    )

    db_session.expire_all()
    run = _latest_run(db_session, service_id)
    report, markdown_report = _read_reports(tmp_path)
    assert run.dry_run is True
    assert run.status == "completed"
    assert run.rewrapped_count == 0
    assert run.scanned_count == 4
    assert run.skipped_count == 0
    assert run.source_key_ids == [LEGACY_KEY_ID]
    assert report["dry_run"] is True
    assert report["source_key_ids"] == [LEGACY_KEY_ID]
    assert report["included_tables"] == ["intent_examples", "runtime_logs"]
    assert report["scanned_count"] == 4
    assert report["rewrapped_count"] == 0
    assert report["skipped_count"] == 0
    assert report["plaintext_exported"] is False
    assert report["status"] == "completed"
    assert report["limit"] == 20
    assert report["batch_size"] == 2
    assert report["scanned_by_table"] == {
        "intent_examples": 2,
        "runtime_logs": 2,
    }
    assert report["key_counts"] == {
        "intent_examples": {
            "legacy": {LEGACY_KEY_ID: 2},
            "active": {ACTIVE_KEY_ID: 1},
            "total": 3,
        },
        "runtime_logs": {
            "legacy": {LEGACY_KEY_ID: 2},
            "active": {ACTIVE_KEY_ID: 1},
            "total": 3,
        },
    }
    assert report["before_key_counts"] == report["key_counts"]
    assert report["after_key_counts"] == report["before_key_counts"]
    assert report["failure_counts"] == {}
    assert f"| intent_examples | legacy | {LEGACY_KEY_ID} | 2 |" in markdown_report
    assert f"| intent_examples | active | {ACTIVE_KEY_ID} | 1 |" in markdown_report
    assert f"| runtime_logs | legacy | {LEGACY_KEY_ID} | 2 |" in markdown_report
    assert f"| runtime_logs | active | {ACTIVE_KEY_ID} | 1 |" in markdown_report
    assert _example_envelopes(db_session, service_id) == before_examples
    assert _runtime_log_envelopes(db_session, service_id) == before_logs


def test_execute_requires_approval_id_and_confirmed_active_key_id(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy_kek = _kek(b"3")
    active_kek = _kek(b"4")
    service_id = _seed_rewrap_fixture(
        db_session,
        legacy_kek=legacy_kek,
        active_kek=active_kek,
    )
    _configure_keyring(monkeypatch, legacy_kek=legacy_kek, active_kek=active_kek)
    required_args = [
        "--service-id",
        service_id,
        "--actor-id",
        ACTOR_ID,
        "--report-dir",
        str(tmp_path),
        "--include",
        "intent-examples",
        "--execute",
    ]

    with pytest.raises(SystemExit, match="--execute requires --approval-id"):
        rewrap_raw_text.main(required_args)

    with pytest.raises(
        SystemExit,
        match="--execute requires --confirm-active-key-id",
    ):
        rewrap_raw_text.main([*required_args, "--approval-id", APPROVAL_ID])

    with pytest.raises(SystemExit, match="must match active raw text key ID"):
        rewrap_raw_text.main(
            [
                *required_args,
                "--approval-id",
                APPROVAL_ID,
                "--confirm-active-key-id",
                LEGACY_KEY_ID,
            ]
        )

    assert _run_count(db_session, service_id) == 0


def test_execute_reencrypts_legacy_records_to_active_key_and_skips_active_records(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy_kek = _kek(b"5")
    active_kek = _kek(b"6")
    service_id = _seed_rewrap_fixture(
        db_session,
        legacy_kek=legacy_kek,
        active_kek=active_kek,
    )
    before_examples = _example_envelopes(db_session, service_id)
    before_logs = _runtime_log_envelopes(db_session, service_id)
    active_example_id = _active_example_id(db_session, service_id)
    active_trace_id = _active_trace_id(db_session, service_id)
    _configure_keyring(monkeypatch, legacy_kek=legacy_kek, active_kek=active_kek)

    rewrap_raw_text.main(
        [
            "--service-id",
            service_id,
            "--actor-id",
            ACTOR_ID,
            "--report-dir",
            str(tmp_path),
            "--include",
            "intent-examples",
            "--include",
            "runtime-logs",
            "--execute",
            "--approval-id",
            APPROVAL_ID,
            "--confirm-active-key-id",
            ACTIVE_KEY_ID,
            "--batch-size",
            "2",
            "--limit",
            "20",
        ]
    )

    db_session.expire_all()
    keyring = RawTextKeyring.from_values(
        active_key_id=ACTIVE_KEY_ID,
        active_kek_base64=active_kek,
        legacy_keks={LEGACY_KEY_ID: legacy_kek},
    )
    after_examples = _example_envelopes(db_session, service_id)
    after_logs = _runtime_log_envelopes(db_session, service_id)
    assert {envelope.key_id for envelope in after_examples.values()} == {ACTIVE_KEY_ID}
    assert {envelope.key_id for envelope in after_logs.values()} == {ACTIVE_KEY_ID}
    assert _example_plaintexts(db_session, service_id, keyring) == [
        "legacy example password reset text",
        "legacy example vpn access text",
        "active example billing text",
    ]
    assert _runtime_log_plaintexts(db_session, service_id, keyring) == [
        "legacy runtime bearer token query Bearer live-runtime-token",
        "legacy runtime api key query irt_live_secret_api_key_value",
        "active runtime query",
    ]
    assert after_examples[active_example_id] == before_examples[active_example_id]
    assert after_logs[active_trace_id] == before_logs[active_trace_id]
    assert any(
        after_examples[example_id].ciphertext != envelope.ciphertext
        for example_id, envelope in before_examples.items()
        if example_id != active_example_id
    )
    assert any(
        after_logs[trace_id].ciphertext != envelope.ciphertext
        for trace_id, envelope in before_logs.items()
        if trace_id != active_trace_id
    )
    run = _latest_run(db_session, service_id)
    assert run.dry_run is False
    assert run.approval_id == APPROVAL_ID
    assert run.scanned_count == 4
    assert run.rewrapped_count == 4
    assert run.skipped_count == 0
    report, markdown_report = _read_reports(tmp_path)
    assert report["status"] == "completed"
    assert report["before_key_counts"] == {
        "intent_examples": {
            "legacy": {LEGACY_KEY_ID: 2},
            "active": {ACTIVE_KEY_ID: 1},
            "total": 3,
        },
        "runtime_logs": {
            "legacy": {LEGACY_KEY_ID: 2},
            "active": {ACTIVE_KEY_ID: 1},
            "total": 3,
        },
    }
    assert report["after_key_counts"] == {
        "intent_examples": {
            "legacy": {},
            "active": {ACTIVE_KEY_ID: 3},
            "total": 3,
        },
        "runtime_logs": {
            "legacy": {},
            "active": {ACTIVE_KEY_ID: 3},
            "total": 3,
        },
    }
    assert report["key_counts"] == report["before_key_counts"]
    assert report["failure_counts"] == {}
    assert report["scanned_by_table"] == {
        "intent_examples": 2,
        "runtime_logs": 2,
    }
    assert f"| Before | intent_examples | legacy | {LEGACY_KEY_ID} | 2 |" in markdown_report
    assert f"| After | intent_examples | active | {ACTIVE_KEY_ID} | 3 |" in markdown_report
    assert f"| After | runtime_logs | legacy | {LEGACY_KEY_ID} | 0 |" in markdown_report
    audit_log = db_session.scalar(
        select(models.AuditLog)
        .where(models.AuditLog.service_id == service_id)
        .where(models.AuditLog.event_type == "raw_text.rewrap.executed")
    )
    assert audit_log is not None
    assert audit_log.actor_id == ACTOR_ID
    assert audit_log.target_id == run.rewrap_run_id
    assert audit_log.after_state == {
        "approval_id": APPROVAL_ID,
        "rewrap_run_id": run.rewrap_run_id,
        "rewrapped_count": 4,
        "scanned_count": 4,
        "skipped_count": 0,
        "failed_count": 0,
        "target_key_id": ACTIVE_KEY_ID,
    }


def test_execute_reports_secret_safe_failures_when_legacy_key_material_is_missing(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy_kek = _kek(b"9")
    active_kek = _kek(b"a")
    service_id = _seed_rewrap_fixture(
        db_session,
        legacy_kek=legacy_kek,
        active_kek=active_kek,
    )
    before_examples = _example_envelopes(db_session, service_id)
    before_logs = _runtime_log_envelopes(db_session, service_id)
    _configure_active_keyring_only(monkeypatch, active_kek=active_kek)

    rewrap_raw_text.main(
        [
            "--service-id",
            service_id,
            "--actor-id",
            ACTOR_ID,
            "--report-dir",
            str(tmp_path),
            "--include",
            "both",
            "--execute",
            "--approval-id",
            APPROVAL_ID,
            "--confirm-active-key-id",
            ACTIVE_KEY_ID,
        ]
    )

    db_session.expire_all()
    run = _latest_run(db_session, service_id)
    report, markdown_report = _read_reports(tmp_path)
    assert run.status == "completed_with_failures"
    assert run.failed_count == 4
    assert run.rewrapped_count == 0
    assert run.skipped_count == 0
    assert report["status"] == "completed_with_failures"
    assert report["failed_count"] == 4
    assert report["failure_counts"] == {
        "intent_examples": {
            LEGACY_KEY_ID: {
                "missing_key_material": 2,
            },
        },
        "runtime_logs": {
            LEGACY_KEY_ID: {
                "missing_key_material": 2,
            },
        },
    }
    assert report["before_key_counts"] == report["after_key_counts"]
    assert _example_envelopes(db_session, service_id) == before_examples
    assert _runtime_log_envelopes(db_session, service_id) == before_logs
    assert (
        f"| intent_examples | {LEGACY_KEY_ID} | missing_key_material | 2 |"
        in markdown_report
    )
    serialized_report = json.dumps(report, ensure_ascii=False, sort_keys=True)
    for marker in (*LEAK_MARKERS, legacy_kek, active_kek, "query_raw", "text_raw"):
        assert marker not in serialized_report
        assert marker not in markdown_report


def test_dry_run_reports_missing_legacy_key_material_before_execute(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy_kek = _kek(b"f")
    active_kek = _kek(b"g")
    service_id = _seed_rewrap_fixture(
        db_session,
        legacy_kek=legacy_kek,
        active_kek=active_kek,
    )
    before_examples = _example_envelopes(db_session, service_id)
    before_logs = _runtime_log_envelopes(db_session, service_id)
    _configure_active_keyring_only(monkeypatch, active_kek=active_kek)

    rewrap_raw_text.main(
        [
            "--service-id",
            service_id,
            "--actor-id",
            ACTOR_ID,
            "--report-dir",
            str(tmp_path),
            "--include",
            "both",
            "--dry-run",
        ]
    )

    db_session.expire_all()
    run = _latest_run(db_session, service_id)
    report, markdown_report = _read_reports(tmp_path)
    assert run.dry_run is True
    assert run.status == "completed_with_failures"
    assert run.failed_count == 4
    assert run.rewrapped_count == 0
    assert report["status"] == "completed_with_failures"
    assert report["failure_counts"] == {
        "intent_examples": {
            LEGACY_KEY_ID: {
                "missing_key_material": 2,
            },
        },
        "runtime_logs": {
            LEGACY_KEY_ID: {
                "missing_key_material": 2,
            },
        },
    }
    assert _example_envelopes(db_session, service_id) == before_examples
    assert _runtime_log_envelopes(db_session, service_id) == before_logs
    serialized_report = json.dumps(report, ensure_ascii=False, sort_keys=True)
    for marker in (*LEAK_MARKERS, legacy_kek, active_kek):
        assert marker not in serialized_report
        assert marker not in markdown_report


def test_limited_execute_reports_partial_remaining_when_legacy_keys_remain(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy_kek = _kek(b"d")
    active_kek = _kek(b"e")
    service_id = _seed_rewrap_fixture(
        db_session,
        legacy_kek=legacy_kek,
        active_kek=active_kek,
    )
    _configure_keyring(monkeypatch, legacy_kek=legacy_kek, active_kek=active_kek)

    rewrap_raw_text.main(
        [
            "--service-id",
            service_id,
            "--actor-id",
            ACTOR_ID,
            "--report-dir",
            str(tmp_path),
            "--include",
            "both",
            "--execute",
            "--approval-id",
            APPROVAL_ID,
            "--confirm-active-key-id",
            ACTIVE_KEY_ID,
            "--limit",
            "1",
        ]
    )

    db_session.expire_all()
    run = _latest_run(db_session, service_id)
    report, _markdown_report = _read_reports(tmp_path)
    assert run.status == "partial_remaining"
    assert report["status"] == "partial_remaining"
    assert report["scanned_by_table"] == {
        "intent_examples": 1,
        "runtime_logs": 1,
    }
    assert report["rewrapped_count"] == 2
    assert report["skipped_count"] == 0
    assert report["after_key_counts"] == {
        "intent_examples": {
            "legacy": {LEGACY_KEY_ID: 1},
            "active": {ACTIVE_KEY_ID: 2},
            "total": 3,
        },
        "runtime_logs": {
            "legacy": {LEGACY_KEY_ID: 1},
            "active": {ACTIVE_KEY_ID: 2},
            "total": 3,
        },
    }


def test_execute_requires_explicit_database_url_before_creating_run(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy_kek = _kek(b"b")
    active_kek = _kek(b"c")
    service_id = _seed_rewrap_fixture(
        db_session,
        legacy_kek=legacy_kek,
        active_kek=active_kek,
    )
    _configure_keyring(monkeypatch, legacy_kek=legacy_kek, active_kek=active_kek)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)

    with pytest.raises(SystemExit, match="--execute requires DATABASE_URL"):
        rewrap_raw_text.main(
            [
                "--service-id",
                service_id,
                "--actor-id",
                ACTOR_ID,
                "--report-dir",
                str(tmp_path),
                "--include",
                "both",
                "--execute",
                "--approval-id",
                APPROVAL_ID,
                "--confirm-active-key-id",
                ACTIVE_KEY_ID,
            ]
        )

    assert _run_count(db_session, service_id) == 0


def test_reports_run_records_and_audit_records_contain_no_sensitive_material(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy_kek = _kek(b"7")
    active_kek = _kek(b"8")
    service_id = _seed_rewrap_fixture(
        db_session,
        legacy_kek=legacy_kek,
        active_kek=active_kek,
    )
    _configure_keyring(monkeypatch, legacy_kek=legacy_kek, active_kek=active_kek)

    rewrap_raw_text.main(
        [
            "--service-id",
            service_id,
            "--actor-id",
            ACTOR_ID,
            "--report-dir",
            str(tmp_path),
            "--include",
            "both",
            "--execute",
            "--approval-id",
            APPROVAL_ID,
            "--confirm-active-key-id",
            ACTIVE_KEY_ID,
        ]
    )

    db_session.expire_all()
    run = _latest_run(db_session, service_id)
    audit_log = db_session.scalar(
        select(models.AuditLog)
        .where(models.AuditLog.service_id == service_id)
        .where(models.AuditLog.event_type == "raw_text.rewrap.executed")
    )
    serialized_records = json.dumps(
        {
            "run_report": run.report,
            "audit_after_state": audit_log.after_state if audit_log else None,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    report_payload = "\n".join(
        path.read_text(encoding="utf-8") for path in tmp_path.iterdir()
    )
    for marker in (*LEAK_MARKERS, legacy_kek, active_kek, "query_raw", "text_raw"):
        assert marker not in serialized_records
        assert marker not in report_payload


def _seed_rewrap_fixture(
    db_session: Session,
    *,
    legacy_kek: str,
    active_kek: str,
) -> str:
    now = datetime.now(UTC)
    service_id = f"it-helpdesk-pilot-{uuid4().hex}"
    repository = IntentRoutingRepository(db_session)
    repository.create_service(
        service_id=service_id,
        display_name="IT Helpdesk Pilot",
        environment="dev",
        default_threshold_preset="balanced",
        max_input_tokens=256,
        status="active",
        created_by="test",
        created_at=now,
        updated_at=now,
    )
    repository.create_intent(
        service_id=service_id,
        intent_id="password-reset",
        domain="it",
        display_name="Password reset",
        description="Password reset help",
        route_key="it.password_reset",
        status="active",
        include_keywords=[],
        exclude_keywords=[],
        created_by="test",
        updated_by="test",
        created_at=now,
        updated_at=now,
    )
    legacy_encryptor = EnvelopeEncryptor(
        kek_id=LEGACY_KEY_ID,
        kek_base64=legacy_kek,
    )
    active_encryptor = EnvelopeEncryptor(
        kek_id=ACTIVE_KEY_ID,
        kek_base64=active_kek,
    )
    _create_example(
        repository,
        service_id=service_id,
        encrypted=legacy_encryptor.encrypt_text("legacy example password reset text"),
        masked="legacy example [REDACTED]",
        created_at=now,
    )
    _create_example(
        repository,
        service_id=service_id,
        encrypted=legacy_encryptor.encrypt_text("legacy example vpn access text"),
        masked="legacy example vpn",
        created_at=now + timedelta(seconds=1),
    )
    _create_example(
        repository,
        service_id=service_id,
        encrypted=active_encryptor.encrypt_text("active example billing text"),
        masked="active example billing",
        created_at=now + timedelta(seconds=2),
    )
    _create_runtime_log(
        repository,
        service_id=service_id,
        trace_id=f"trace-legacy-1-{uuid4().hex}",
        encrypted=legacy_encryptor.encrypt_text(
            "legacy runtime bearer token query Bearer live-runtime-token"
        ),
        masked="legacy runtime bearer token [REDACTED]",
        created_at=now,
    )
    _create_runtime_log(
        repository,
        service_id=service_id,
        trace_id=f"trace-legacy-2-{uuid4().hex}",
        encrypted=legacy_encryptor.encrypt_text(
            "legacy runtime api key query irt_live_secret_api_key_value"
        ),
        masked="legacy runtime api key [REDACTED]",
        created_at=now + timedelta(seconds=1),
    )
    _create_runtime_log(
        repository,
        service_id=service_id,
        trace_id=f"trace-active-{uuid4().hex}",
        encrypted=active_encryptor.encrypt_text("active runtime query"),
        masked="active runtime query",
        created_at=now + timedelta(seconds=2),
    )
    db_session.commit()
    return service_id


def _create_example(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    encrypted: EncryptedText,
    masked: str,
    created_at: datetime,
) -> None:
    repository.create_example(
        service_id=service_id,
        intent_id="password-reset",
        example_type="positive",
        text_raw_ciphertext=encrypted.ciphertext,
        text_raw_encrypted_dek=encrypted.encrypted_dek,
        text_raw_encrypted_dek_iv=encrypted.encrypted_dek_iv,
        text_raw_encrypted_dek_auth_tag=encrypted.encrypted_dek_auth_tag,
        text_raw_key_id=encrypted.key_id,
        text_raw_iv=encrypted.iv,
        text_raw_auth_tag=encrypted.auth_tag,
        text_raw_algorithm=encrypted.algorithm,
        text_masked=masked,
        embedding=None,
        source="rewrap-test",
        test_case_id=None,
        approved=True,
        created_by="rewrap-test",
        created_at=created_at,
    )


def _create_runtime_log(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    trace_id: str,
    encrypted: EncryptedText,
    masked: str,
    created_at: datetime,
) -> None:
    repository.insert_runtime_log(
        trace_id=trace_id,
        service_id=service_id,
        latency_ms=10,
        query_raw_ciphertext=encrypted.ciphertext,
        query_raw_encrypted_dek=encrypted.encrypted_dek,
        query_raw_encrypted_dek_iv=encrypted.encrypted_dek_iv,
        query_raw_encrypted_dek_auth_tag=encrypted.encrypted_dek_auth_tag,
        query_raw_key_id=encrypted.key_id,
        query_raw_iv=encrypted.iv,
        query_raw_auth_tag=encrypted.auth_tag,
        query_raw_algorithm=encrypted.algorithm,
        query_masked=masked,
        created_at=created_at,
    )


def _configure_keyring(
    monkeypatch: pytest.MonkeyPatch,
    *,
    legacy_kek: str,
    active_kek: str,
) -> None:
    monkeypatch.setenv("RAW_TEXT_KEK_ID", ACTIVE_KEY_ID)
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", active_kek)
    monkeypatch.setenv(
        "RAW_TEXT_LEGACY_KEKS_JSON",
        json.dumps({LEGACY_KEY_ID: legacy_kek}, sort_keys=True),
    )


def _configure_active_keyring_only(
    monkeypatch: pytest.MonkeyPatch,
    *,
    active_kek: str,
) -> None:
    monkeypatch.setenv("RAW_TEXT_KEK_ID", ACTIVE_KEY_ID)
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", active_kek)
    monkeypatch.setenv("RAW_TEXT_LEGACY_KEKS_JSON", "{}")


def _kek(byte: bytes) -> str:
    return base64.b64encode(byte * 32).decode("ascii")


def _latest_run(db_session: Session, service_id: str) -> models.RawTextRewrapRun:
    run = db_session.scalar(
        select(models.RawTextRewrapRun)
        .where(models.RawTextRewrapRun.service_id == service_id)
        .order_by(models.RawTextRewrapRun.started_at.desc())
    )
    assert run is not None
    return run


def _run_count(db_session: Session, service_id: str) -> int:
    return len(
        db_session.scalars(
            select(models.RawTextRewrapRun).where(
                models.RawTextRewrapRun.service_id == service_id
            )
        ).all()
    )


def _read_reports(report_dir: Path) -> tuple[dict[str, object], str]:
    reports = sorted(report_dir.glob("raw-text-rewrap-*.json"))
    assert len(reports) == 1
    markdown_reports = sorted(report_dir.glob("raw-text-rewrap-*.md"))
    assert len(markdown_reports) == 1
    return (
        json.loads(reports[0].read_text(encoding="utf-8")),
        markdown_reports[0].read_text(encoding="utf-8"),
    )


def _example_envelopes(
    db_session: Session,
    service_id: str,
) -> dict[str, EncryptedText]:
    examples = db_session.scalars(
        select(models.IntentExample)
        .where(models.IntentExample.service_id == service_id)
        .order_by(models.IntentExample.created_at, models.IntentExample.example_id)
    )
    return {
        str(example.example_id): intent_example_encrypted_text(example)
        for example in examples
    }


def _runtime_log_envelopes(
    db_session: Session,
    service_id: str,
) -> dict[str, EncryptedText]:
    runtime_logs = db_session.scalars(
        select(models.RuntimeLog)
        .where(models.RuntimeLog.service_id == service_id)
        .order_by(models.RuntimeLog.created_at, models.RuntimeLog.trace_id)
    )
    return {
        runtime_log.trace_id: encrypted
        for runtime_log in runtime_logs
        if (encrypted := runtime_log_encrypted_query(runtime_log)) is not None
    }


def _example_plaintexts(
    db_session: Session,
    service_id: str,
    keyring: RawTextKeyring,
) -> list[str]:
    examples = db_session.scalars(
        select(models.IntentExample)
        .where(models.IntentExample.service_id == service_id)
        .order_by(models.IntentExample.created_at, models.IntentExample.example_id)
    )
    return [
        keyring.decrypt_text(intent_example_encrypted_text(example))
        for example in examples
    ]


def _runtime_log_plaintexts(
    db_session: Session,
    service_id: str,
    keyring: RawTextKeyring,
) -> list[str]:
    runtime_logs = db_session.scalars(
        select(models.RuntimeLog)
        .where(models.RuntimeLog.service_id == service_id)
        .order_by(models.RuntimeLog.created_at, models.RuntimeLog.trace_id)
    )
    plaintexts = []
    for runtime_log in runtime_logs:
        encrypted = runtime_log_encrypted_query(runtime_log)
        assert encrypted is not None
        plaintexts.append(keyring.decrypt_text(encrypted))
    return plaintexts


def _active_example_id(db_session: Session, service_id: str) -> str:
    example_id = db_session.scalar(
        select(models.IntentExample.example_id)
        .where(models.IntentExample.service_id == service_id)
        .where(models.IntentExample.text_raw_key_id == ACTIVE_KEY_ID)
    )
    assert example_id is not None
    return str(example_id)


def _active_trace_id(db_session: Session, service_id: str) -> str:
    trace_id = db_session.scalar(
        select(models.RuntimeLog.trace_id)
        .where(models.RuntimeLog.service_id == service_id)
        .where(models.RuntimeLog.query_raw_key_id == ACTIVE_KEY_ID)
    )
    assert trace_id is not None
    return trace_id
