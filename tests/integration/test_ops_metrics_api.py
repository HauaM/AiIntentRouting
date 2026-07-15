from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, or_
from sqlalchemy.orm import Session

from intent_routing.api.admin import get_admin_session
from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.main import create_app

SERVICE_ID = "it-helpdesk-pilot"
OTHER_SERVICE_ID = "hr-helpdesk-pilot"
ACTIVE_KEY_ID = "pilot-kek-20260628-002"
LEGACY_KEY_ID = "pilot-kek-20260628-001"
PARTIAL_KEY_ID = "pilot-kek-20260628-partial"
RAW_QUERY = "plain raw query with bearer token"
RAW_EXAMPLE_TEXT = "plain raw example text"
BEARER_TOKEN = "Bearer irt_runtime_secret_token"
API_KEY_SECRET = "irt_secret_task6_token"
KEK_BASE64 = "bm90LWEtcmVhbC1rZWstYnV0LXNlbnNpdGl2ZQ=="


def test_scoped_auditor_can_list_audit_logs_and_raw_text_key_summary_for_service(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = _seed_ops_state(db_session)
    client = _client(db_session, monkeypatch)

    audit_response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/audit-logs",
        headers=_auditor_headers(SERVICE_ID),
        params={"event_type": "raw_query.viewed", "trace_id": seed.trace_id},
    )
    summary_response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/security/raw-text-key-summary",
        headers=_auditor_headers(SERVICE_ID),
    )

    assert audit_response.status_code == 200
    assert audit_response.json() == [
        {
            "audit_id": seed.audit_id,
            "event_type": "raw_query.viewed",
            "actor_id": "auditor-user",
            "service_id": SERVICE_ID,
            "trace_id": seed.trace_id,
            "target_type": "runtime_log",
            "target_id": seed.trace_id,
            "view_reason": "approval=SEC-20260628-001; reason_redacted=true",
            "source_ip": "127.0.0.1",
            "created_at": "2026-06-28T00:00:00Z",
        }
    ]
    assert "before_state" not in audit_response.text
    assert "after_state" not in audit_response.text

    assert summary_response.status_code == 200
    assert summary_response.json() == {
        "service_id": SERVICE_ID,
        "active_key_id": ACTIVE_KEY_ID,
        "intent_examples": [
            {"key_id": ACTIVE_KEY_ID, "count": 2},
            {"key_id": LEGACY_KEY_ID, "count": 1},
        ],
        "runtime_logs": [
            {"key_id": ACTIVE_KEY_ID, "count": 3},
            {"key_id": LEGACY_KEY_ID, "count": 1},
            {"key_id": PARTIAL_KEY_ID, "count": 1},
            {"key_id": None, "count": 1, "state": "raw_query_redacted"},
        ],
    }


def test_scoped_auditor_cannot_read_another_service(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_ops_state(db_session)
    client = _client(db_session, monkeypatch)
    headers = _auditor_headers(SERVICE_ID)

    audit_response = client.get(
        f"/admin/v1/services/{OTHER_SERVICE_ID}/audit-logs",
        headers=headers,
    )
    summary_response = client.get(
        f"/admin/v1/services/{OTHER_SERVICE_ID}/security/raw-text-key-summary",
        headers=headers,
    )

    assert audit_response.status_code == 403
    assert audit_response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"
    assert summary_response.status_code == 403
    assert summary_response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"


def test_scoped_service_operator_can_read_runtime_metrics(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_ops_state(db_session)
    client = _client(db_session, monkeypatch)

    response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/runtime-metrics",
        headers=_operator_headers(SERVICE_ID),
        params={"window_hours": 24},
    )

    assert response.status_code == 200
    assert response.json() == {
        "service_id": SERVICE_ID,
        "window_hours": 24,
        "request_count": 4,
        "decision_counts": {
            "confident": 1,
            "clarify": 1,
            "fallback": 1,
            "off_topic": 0,
            "risk": 1,
            "unauthorized": 0,
        },
        "error_counts": {"AUTHENTICATION_FAILED": 1},
        "latency_ms": {"p50": 24, "p95": 141, "max": 141},
        "top_route_keys": [
            {"route_key": "it.api_timeout.manual_lookup", "count": 2},
            {"route_key": "it.password_reset.manual_lookup", "count": 1},
        ],
        "raw_query_retention": {
            "encrypted_count": 3,
            "incomplete_count": 0,
            "redacted_count": 1,
        },
    }


def test_runtime_metrics_and_key_summary_count_partial_material_without_key_id(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_ops_state(db_session)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(db_session)
    repository.insert_runtime_log(
        trace_id="irt-ops-metrics-partial-no-key",
        request_id="req-irt-ops-metrics-partial-no-key",
        app_id="ops-metrics-app",
        service_id=SERVICE_ID,
        release_version="rel-ops-metrics-001",
        policy_version="pol-ops-metrics-001",
        intent_catalog_version="cat-ops-metrics-001",
        decision="fallback",
        latency_ms=31,
        query_masked="partial no-key runtime query",
        query_raw_ciphertext=b"partial no-key ciphertext",
        created_at=now - timedelta(hours=1),
    )
    db_session.commit()
    client = _client(db_session, monkeypatch)

    metrics_response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/runtime-metrics",
        headers=_operator_headers(SERVICE_ID),
        params={"window_hours": 24},
    )
    summary_response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/security/raw-text-key-summary",
        headers=_auditor_headers(SERVICE_ID),
    )

    assert metrics_response.status_code == 200
    assert metrics_response.json()["raw_query_retention"] == {
        "encrypted_count": 4,
        "incomplete_count": 1,
        "redacted_count": 1,
    }
    assert summary_response.status_code == 200
    assert {"key_id": None, "count": 1, "state": "raw_query_incomplete"} in (
        summary_response.json()["runtime_logs"]
    )


def test_raw_text_key_summary_uses_default_active_key_id_when_env_is_omitted(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_ops_state(db_session)
    client = _client(db_session, monkeypatch, raw_text_kek_id=None)

    response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/security/raw-text-key-summary",
        headers=_auditor_headers(SERVICE_ID),
    )

    assert response.status_code == 200
    assert response.json()["active_key_id"] == "local-kek-001"


def test_service_developer_can_read_audit_logs_but_not_key_summary(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_ops_state(db_session)
    client = _client(db_session, monkeypatch)
    headers = _developer_headers(SERVICE_ID)

    audit_response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/audit-logs",
        headers=headers,
    )
    summary_response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/security/raw-text-key-summary",
        headers=headers,
    )

    assert audit_response.status_code == 200
    assert summary_response.status_code == 403
    assert summary_response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"


def test_system_admin_can_read_all_new_operations_endpoints(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_ops_state(db_session)
    client = _client(db_session, monkeypatch)
    headers = _admin_headers()

    audit_response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/audit-logs",
        headers=headers,
    )
    summary_response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/security/raw-text-key-summary",
        headers=headers,
    )
    metrics_response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/runtime-metrics",
        headers=headers,
    )

    assert audit_response.status_code == 200
    assert summary_response.status_code == 200
    assert metrics_response.status_code == 200


def test_new_operations_responses_do_not_expose_sensitive_material(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = _seed_ops_state(db_session)
    client = _client(db_session, monkeypatch)

    audit_response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/audit-logs",
        headers=_auditor_headers(SERVICE_ID),
        params={"trace_id": seed.trace_id},
    )
    summary_response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/security/raw-text-key-summary",
        headers=_auditor_headers(SERVICE_ID),
    )
    metrics_response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/runtime-metrics",
        headers=_operator_headers(SERVICE_ID),
    )

    assert audit_response.status_code == 200
    assert summary_response.status_code == 200
    assert metrics_response.status_code == 200
    serialized = json.dumps(
        {
            "audit": audit_response.json(),
            "summary": summary_response.json(),
            "metrics": metrics_response.json(),
        },
        ensure_ascii=False,
    )
    for forbidden in (
        "ciphertext",
        "encrypted_dek",
        "query_raw",
        "text_raw",
        RAW_QUERY,
        RAW_EXAMPLE_TEXT,
        BEARER_TOKEN,
        API_KEY_SECRET,
        KEK_BASE64,
    ):
        assert forbidden not in serialized


def test_audit_log_view_reason_is_sanitized(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_ops_state(db_session)
    client = _client(db_session, monkeypatch)

    response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/audit-logs",
        headers=_auditor_headers(SERVICE_ID),
        params={"trace_id": "irt-ops-metrics-secret-reason"},
    )

    assert response.status_code == 200
    assert response.json()[0]["view_reason"] == "approval=SEC-SECRET; reason_redacted=true"
    for forbidden in (
        BEARER_TOKEN,
        API_KEY_SECRET,
        KEK_BASE64,
        RAW_QUERY,
        "query_raw",
        "text_raw",
        "plain customer raw text",
        "some arbitrary plaintext secret",
        "details",
        "note",
    ):
        assert forbidden not in response.text


def test_raw_text_key_summary_counts_partial_envelope_without_valid_kek(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_ops_state(db_session)
    client = _client(
        db_session,
        monkeypatch,
        raw_text_kek_base64="not-valid-base64",
    )

    response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/security/raw-text-key-summary",
        headers=_auditor_headers(SERVICE_ID),
    )

    assert response.status_code == 200
    assert {"key_id": PARTIAL_KEY_ID, "count": 1} in response.json()["runtime_logs"]


class _SeedResult:
    def __init__(self, *, trace_id: str, audit_id: str) -> None:
        self.trace_id = trace_id
        self.audit_id = audit_id


def _client(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    *,
    raw_text_kek_id: str | None = ACTIVE_KEY_ID,
    raw_text_kek_base64: str | None = KEK_BASE64,
) -> TestClient:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    if raw_text_kek_id is None:
        monkeypatch.delenv("RAW_TEXT_KEK_ID", raising=False)
    else:
        monkeypatch.setenv("RAW_TEXT_KEK_ID", raw_text_kek_id)
    if raw_text_kek_base64 is None:
        monkeypatch.delenv("RAW_TEXT_KEK_BASE64", raising=False)
    else:
        monkeypatch.setenv("RAW_TEXT_KEK_BASE64", raw_text_kek_base64)
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    return TestClient(app)


def _admin_headers(**overrides: str) -> dict[str, str]:
    headers = {
        "X-Admin-Token": "local-admin-token",
        "X-Actor-Id": "admin-user",
        "X-Actor-Roles": "system_admin",
    }
    headers.update(overrides)
    return headers


def _auditor_headers(service_id: str) -> dict[str, str]:
    return _admin_headers(
        **{
            "X-Actor-Id": "auditor-user",
            "X-Actor-Roles": "auditor",
            "X-Service-Scope": service_id,
        }
    )


def _operator_headers(service_id: str) -> dict[str, str]:
    return _admin_headers(
        **{
            "X-Actor-Id": "operator-user",
            "X-Actor-Roles": "service_operator",
            "X-Service-Scope": service_id,
        }
    )


def _developer_headers(service_id: str) -> dict[str, str]:
    return _admin_headers(
        **{
            "X-Actor-Id": "developer-user",
            "X-Actor-Roles": "service_developer",
            "X-Service-Scope": service_id,
        }
    )


def _seed_ops_state(db_session: Session) -> _SeedResult:
    _purge_ops_state(db_session)
    repository = IntentRoutingRepository(db_session)
    now = datetime.now(UTC)
    created_at = now - timedelta(hours=1)
    audit_created_at = datetime(2026, 6, 28, tzinfo=UTC)

    _create_service(repository, SERVICE_ID, now)
    _create_service(repository, OTHER_SERVICE_ID, now)
    _create_intent(repository, service_id=SERVICE_ID, intent_id="intent-api-timeout", now=now)
    _create_intent(repository, service_id=OTHER_SERVICE_ID, intent_id="intent-hr", now=now)

    _create_example(repository, key_id=ACTIVE_KEY_ID, created_at=now)
    _create_example(repository, key_id=ACTIVE_KEY_ID, created_at=now)
    _create_example(repository, key_id=LEGACY_KEY_ID, created_at=now)

    traces = [
        _insert_runtime_log(
            repository,
            trace_id="irt-ops-metrics-001",
            decision="confident",
            route_key="it.api_timeout.manual_lookup",
            latency_ms=24,
            raw_key_id=ACTIVE_KEY_ID,
            created_at=created_at,
        ),
        _insert_runtime_log(
            repository,
            trace_id="irt-ops-metrics-002",
            decision="clarify",
            route_key="it.api_timeout.manual_lookup",
            latency_ms=80,
            raw_key_id=ACTIVE_KEY_ID,
            error_code="AUTHENTICATION_FAILED",
            created_at=created_at,
        ),
        _insert_runtime_log(
            repository,
            trace_id="irt-ops-metrics-003",
            decision="fallback",
            route_key="it.password_reset.manual_lookup",
            latency_ms=141,
            raw_key_id=LEGACY_KEY_ID,
            created_at=created_at,
        ),
        _insert_runtime_log(
            repository,
            trace_id="irt-ops-metrics-004",
            decision="risk",
            route_key=None,
            latency_ms=12,
            raw_key_id=None,
            raw_query_deleted_at=now,
            created_at=created_at,
        ),
    ]
    _insert_runtime_log(
        repository,
        trace_id="irt-ops-metrics-old",
        decision="confident",
        route_key="it.old.manual_lookup",
        latency_ms=999,
        raw_key_id=ACTIVE_KEY_ID,
        created_at=now - timedelta(days=7),
    )
    _insert_runtime_log(
        repository,
        trace_id="irt-ops-metrics-partial",
        decision="confident",
        route_key="it.partial.manual_lookup",
        latency_ms=55,
        raw_key_id=PARTIAL_KEY_ID,
        raw_envelope_complete=False,
        created_at=now - timedelta(days=7),
    )
    _insert_runtime_log(
        repository,
        trace_id="irt-ops-metrics-other",
        service_id=OTHER_SERVICE_ID,
        decision="confident",
        route_key="hr.benefits.manual_lookup",
        latency_ms=7,
        raw_key_id=ACTIVE_KEY_ID,
        created_at=created_at,
    )

    audit_log = repository.insert_audit_log(
        event_type="raw_query.viewed",
        actor_id="auditor-user",
        service_id=SERVICE_ID,
        trace_id=traces[0].trace_id,
        target_type="runtime_log",
        target_id=traces[0].trace_id,
        view_reason="approval=SEC-20260628-001; reason=장애 분석 ticket INC-20260628-001",
        source_ip="127.0.0.1",
        before_state={
            "query_raw": RAW_QUERY,
            "authorization": BEARER_TOKEN,
            "kek_base64": KEK_BASE64,
        },
        after_state={
            "query_raw_ciphertext": "ciphertext-value",
            "query_raw_encrypted_dek": "encrypted-dek-value",
            "text_raw": RAW_EXAMPLE_TEXT,
        },
        created_at=audit_created_at,
    )
    repository.insert_audit_log(
        event_type="raw_query.viewed",
        actor_id="auditor-user",
        service_id=SERVICE_ID,
        trace_id="irt-ops-metrics-secret-reason",
        target_type="runtime_log",
        target_id="irt-ops-metrics-secret-reason",
        view_reason=(
            "approval=SEC-SECRET; "
            f"reason=query_raw text_raw {RAW_QUERY}; "
            f"authorization={BEARER_TOKEN}; "
            f"api_key={API_KEY_SECRET}; "
            f"kek_base64={KEK_BASE64}; "
            "details=plain customer raw text; "
            "note=some arbitrary plaintext secret"
        ),
        source_ip="127.0.0.1",
        before_state=None,
        after_state=None,
        created_at=audit_created_at + timedelta(seconds=1),
    )
    repository.insert_audit_log(
        event_type="raw_query.viewed",
        actor_id="auditor-user",
        service_id=OTHER_SERVICE_ID,
        trace_id="irt-ops-metrics-other",
        target_type="runtime_log",
        target_id="irt-ops-metrics-other",
        view_reason="approval=SEC-OTHER; reason=other service",
        source_ip="127.0.0.1",
        before_state=None,
        after_state=None,
        created_at=audit_created_at,
    )
    db_session.commit()
    return _SeedResult(trace_id=traces[0].trace_id, audit_id=str(audit_log.audit_id))


def _create_service(
    repository: IntentRoutingRepository,
    service_id: str,
    now: datetime,
) -> None:
    repository.create_service(
        service_id=service_id,
        display_name=service_id,
        environment="prod",
        default_threshold_preset="balanced",
        max_input_tokens=256,
        status="active",
        created_by="ops-metrics-test",
        created_at=now,
        updated_at=now,
    )


def _create_intent(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    intent_id: str,
    now: datetime,
) -> None:
    repository.create_intent(
        service_id=service_id,
        intent_id=intent_id,
        domain="it",
        display_name=intent_id,
        description="ops metrics test intent",
        route_key=f"{intent_id}.manual_lookup",
        status="active",
        include_keywords=[],
        exclude_keywords=[],
        created_by="ops-metrics-test",
        updated_by="ops-metrics-test",
        created_at=now,
        updated_at=now,
    )


def _create_example(
    repository: IntentRoutingRepository,
    *,
    key_id: str,
    created_at: datetime,
) -> None:
    repository.create_example(
        service_id=SERVICE_ID,
        intent_id="intent-api-timeout",
        example_type="positive",
        text_raw_ciphertext=b"example-ciphertext",
        text_raw_encrypted_dek=b"example-encrypted-dek",
        text_raw_encrypted_dek_iv=b"example-dek-iv",
        text_raw_encrypted_dek_auth_tag=b"example-dek-auth-tag",
        text_raw_key_id=key_id,
        text_raw_iv=b"example-iv",
        text_raw_auth_tag=b"example-auth-tag",
        text_raw_algorithm="AES-256-GCM",
        text_masked="masked example",
        embedding=None,
        source="ops-metrics-test",
        test_case_id=None,
        approved=True,
        created_by="ops-metrics-test",
        created_at=created_at,
    )


def _insert_runtime_log(
    repository: IntentRoutingRepository,
    *,
    trace_id: str,
    decision: str,
    route_key: str | None,
    latency_ms: int,
    raw_key_id: str | None,
    created_at: datetime,
    service_id: str = SERVICE_ID,
    error_code: str | None = None,
    raw_query_deleted_at: datetime | None = None,
    raw_envelope_complete: bool = True,
) -> models.RuntimeLog:
    raw_envelope: dict[str, object] = {}
    if raw_key_id is not None and raw_query_deleted_at is None:
        raw_envelope["query_raw_key_id"] = raw_key_id
        if raw_envelope_complete:
            raw_envelope.update(
                {
                    "query_raw_ciphertext": b"runtime-ciphertext",
                    "query_raw_encrypted_dek": b"runtime-encrypted-dek",
                    "query_raw_encrypted_dek_iv": b"runtime-dek-iv",
                    "query_raw_encrypted_dek_auth_tag": b"runtime-dek-auth-tag",
                    "query_raw_iv": b"runtime-iv",
                    "query_raw_auth_tag": b"runtime-auth-tag",
                    "query_raw_algorithm": "AES-256-GCM",
                }
            )
    return repository.insert_runtime_log(
        trace_id=trace_id,
        request_id=f"req-{trace_id}",
        app_id="ops-metrics-app",
        service_id=service_id,
        release_version="rel-ops-metrics-001",
        policy_version="pol-ops-metrics-001",
        intent_catalog_version="cat-ops-metrics-001",
        model_version="emb-fake-v1",
        vector_index_version="vec-ops-metrics-001",
        test_run_id=None,
        decision=decision,
        intent_id="intent-api-timeout" if decision == "confident" else None,
        confidence=Decimal("0.93") if decision == "confident" else None,
        margin=Decimal("0.20") if decision == "confident" else None,
        threshold_preset="balanced",
        threshold_value=Decimal("0.80"),
        route_key=route_key,
        decision_state={"safe": True},
        error_code=error_code,
        error_category="auth" if error_code else None,
        error_layer="runtime" if error_code else None,
        http_status=401 if error_code else None,
        retryable=False if error_code else None,
        latency_ms=latency_ms,
        query_masked="masked runtime query",
        raw_query_deleted_at=raw_query_deleted_at,
        raw_query_deleted_by="retention-job" if raw_query_deleted_at else None,
        raw_query_delete_reason=(
            "raw query retention policy" if raw_query_deleted_at else None
        ),
        created_at=created_at,
        **raw_envelope,
    )


def _purge_ops_state(db_session: Session) -> None:
    service_ids = (SERVICE_ID, OTHER_SERVICE_ID)
    db_session.execute(
        delete(models.RuntimeLog).where(
            or_(
                models.RuntimeLog.service_id.in_(service_ids),
                models.RuntimeLog.app_id == "ops-metrics-app",
            )
        )
    )
    db_session.execute(delete(models.AuditLog).where(models.AuditLog.service_id.in_(service_ids)))
    db_session.execute(
        delete(models.IntentExample).where(models.IntentExample.service_id.in_(service_ids))
    )
    db_session.execute(delete(models.Intent).where(models.Intent.service_id.in_(service_ids)))
    db_session.execute(delete(models.Service).where(models.Service.service_id.in_(service_ids)))
    db_session.commit()
