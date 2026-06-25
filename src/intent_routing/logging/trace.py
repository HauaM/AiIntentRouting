from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from os import environ
from time import perf_counter
from typing import cast
from uuid import uuid4

from fastapi import Request
from sqlalchemy.orm import Session

from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.db.session import session_scope
from intent_routing.domain.enums import ErrorCode
from intent_routing.routing.engine import ActiveReleaseContext
from intent_routing.routing.scoring import RoutingDecisionResult
from intent_routing.security.encryption import EnvelopeEncryptor
from intent_routing.security.pii import mask_pii

RUNTIME_ERROR_LOGGED_HEADER = "X-Intent-Runtime-Logged"
RuntimeLogSessionFactory = Callable[[], AbstractContextManager[Session]]


class RuntimeTraceConfigurationError(RuntimeError):
    """Raised when runtime logging cannot satisfy required encryption settings."""


@dataclass(frozen=True, slots=True)
class RuntimeErrorLog:
    code: ErrorCode
    category: str
    layer: str
    message: str
    retryable: bool


def build_trace_id() -> str:
    return f"irt-{uuid4().hex}"


def configure_runtime_log_session_factory(request: Request) -> RuntimeLogSessionFactory:
    factory = getattr(request.app.state, "runtime_log_session_factory", None)
    if callable(factory):
        return cast("RuntimeLogSessionFactory", factory)
    return session_scope


def begin_request_timer(request: Request) -> None:
    request.state.runtime_started_at = perf_counter()


def runtime_latency_ms(request: Request) -> int:
    started_at = getattr(request.state, "runtime_started_at", None)
    if not isinstance(started_at, float):
        return 0
    return max(0, int((perf_counter() - started_at) * 1000))


def should_log_runtime_error(
    request: Request,
    *,
    already_logged: bool,
    detail: object,
) -> bool:
    if request.url.path != "/v1/intent-route":
        return False
    if already_logged:
        return False
    return isinstance(detail, dict) and detail.get("status") == "error"


async def extract_runtime_query(request: Request) -> str | None:
    try:
        body = await request.body()
    except Exception:
        return None
    if not body:
        return None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    query = payload.get("query")
    return query if isinstance(query, str) else None


def log_runtime_preflight_error(
    request: Request,
    *,
    trace_id: str,
    request_id: str | None,
    error: RuntimeErrorLog,
    http_status: int,
    query_raw: str | None,
) -> None:
    session_factory = configure_runtime_log_session_factory(request)
    try:
        with session_factory() as session:
            repository = IntentRoutingRepository(session)
            RuntimeTraceLogger(repository).log_error(
                trace_id=trace_id,
                request_id=request_id,
                app_id=request.headers.get("X-App-Id"),
                service_id=request.headers.get("X-Service-Id"),
                release=None,
                error=error,
                http_status=http_status,
                latency_ms=runtime_latency_ms(request),
                query_raw=query_raw,
                decision="error",
            )
            session.commit()
    except Exception:
        return


class RuntimeTraceLogger:
    def __init__(self, repository: IntentRoutingRepository) -> None:
        self._repository = repository

    def log_success(
        self,
        *,
        trace_id: str,
        request_id: str | None,
        app_id: str,
        service_id: str,
        release: ActiveReleaseContext,
        decision: RoutingDecisionResult,
        query_raw: str,
        latency_ms: int,
    ) -> None:
        encrypted_query = _raw_text_encryptor().encrypt_text(query_raw)
        self._repository.insert_runtime_log(
            trace_id=trace_id,
            request_id=request_id,
            app_id=app_id,
            service_id=service_id,
            release_version=release.release_version,
            policy_version=release.policy_version,
            intent_catalog_version=release.intent_catalog_version,
            model_version=release.model_version,
            vector_index_version=release.vector_index_version,
            decision=decision.decision.value,
            intent_id=decision.intent_id,
            confidence=_decimal_or_none(decision.confidence),
            margin=_decimal_or_none(decision.margin),
            threshold_preset=release.threshold_preset,
            threshold_value=_decimal_or_none(release.threshold),
            route_key=decision.route_key,
            error_code=None,
            error_category=None,
            error_layer=None,
            http_status=None,
            retryable=None,
            latency_ms=latency_ms,
            query_raw_ciphertext=encrypted_query.ciphertext,
            query_raw_encrypted_dek=encrypted_query.encrypted_dek,
            query_raw_encrypted_dek_iv=encrypted_query.encrypted_dek_iv,
            query_raw_encrypted_dek_auth_tag=encrypted_query.encrypted_dek_auth_tag,
            query_raw_key_id=encrypted_query.key_id,
            query_raw_iv=encrypted_query.iv,
            query_raw_auth_tag=encrypted_query.auth_tag,
            query_raw_algorithm=encrypted_query.algorithm,
            query_masked=mask_pii(query_raw),
            created_at=datetime.now(UTC),
        )

    def log_error(
        self,
        *,
        trace_id: str,
        request_id: str | None,
        app_id: str | None,
        service_id: str | None,
        release: ActiveReleaseContext | None,
        error: RuntimeErrorLog,
        http_status: int,
        latency_ms: int,
        query_raw: str | None,
        decision: str | None = None,
    ) -> None:
        self._repository.insert_runtime_log(
            trace_id=trace_id,
            request_id=request_id,
            app_id=app_id,
            service_id=service_id,
            release_version=release.release_version if release is not None else None,
            policy_version=release.policy_version if release is not None else None,
            intent_catalog_version=(
                release.intent_catalog_version if release is not None else None
            ),
            model_version=release.model_version if release is not None else None,
            vector_index_version=release.vector_index_version if release is not None else None,
            decision=decision,
            intent_id=None,
            confidence=None,
            margin=None,
            threshold_preset=release.threshold_preset if release is not None else None,
            threshold_value=(
                _decimal_or_none(release.threshold) if release is not None else None
            ),
            route_key=None,
            error_code=error.code.value,
            error_category=error.category,
            error_layer=error.layer,
            http_status=http_status,
            retryable=error.retryable,
            latency_ms=latency_ms,
            query_raw_ciphertext=None,
            query_raw_encrypted_dek=None,
            query_raw_encrypted_dek_iv=None,
            query_raw_encrypted_dek_auth_tag=None,
            query_raw_key_id=None,
            query_raw_iv=None,
            query_raw_auth_tag=None,
            query_raw_algorithm=None,
            query_masked=mask_pii(query_raw) if query_raw is not None else None,
            created_at=datetime.now(UTC),
        )


def _raw_text_encryptor() -> EnvelopeEncryptor:
    kek_base64 = environ.get("RAW_TEXT_KEK_BASE64")
    if kek_base64 is None or not kek_base64.strip():
        raise RuntimeTraceConfigurationError("Raw text encryption key is not configured.")
    try:
        return EnvelopeEncryptor(
            kek_id=environ.get("RAW_TEXT_KEK_ID", "local-kek-001"),
            kek_base64=kek_base64,
        )
    except ValueError as exc:
        raise RuntimeTraceConfigurationError("Raw text encryption key is invalid.") from exc


def _decimal_or_none(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(round(value, 6)))
