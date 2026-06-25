from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from intent_routing.api.dependencies import AuthContext, require_api_key
from intent_routing.domain.enums import Decision
from intent_routing.domain.schemas import FallbackPolicy, RuntimeRequest, RuntimeResponse
from intent_routing.security.api_keys import ApiKeyRecord, check_scope


def create_app() -> FastAPI:
    app = FastAPI(title="Intent Routing Service")

    @app.exception_handler(HTTPException)
    def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and exc.detail.get("status") == "error":
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/intent-route", response_model=RuntimeResponse)
    def intent_route(
        request: RuntimeRequest,
        auth: Annotated[AuthContext, Depends(require_api_key)],
    ) -> RuntimeResponse:
        trace_id = f"irt-{uuid4().hex}"
        candidate_route_key, candidate_intent_id = _candidate_scope(request.user_context)
        if candidate_route_key is not None or candidate_intent_id is not None:
            scope_record = _auth_scope_record(auth)
            scope_result = check_scope(
                scope_record,
                app_id=auth.app_id,
                service_id=auth.service_id,
                route_key=candidate_route_key,
                intent_id=candidate_intent_id,
            )
            if not scope_result.allowed:
                return RuntimeResponse(
                    trace_id=trace_id,
                    request_id=auth.request_id,
                    decision=Decision.unauthorized,
                    intent_id=candidate_intent_id,
                    route_key=candidate_route_key,
                    fallback_policy=FallbackPolicy(
                        type="client_fallback",
                        retryable=False,
                        recommended_action="deny_route",
                    ),
                )

        return RuntimeResponse(
            trace_id=trace_id,
            request_id=auth.request_id,
            decision=Decision.fallback,
            fallback_policy=FallbackPolicy(
                type="client_fallback",
                retryable=True,
                recommended_action="route_engine_pending",
                message="Runtime routing is not implemented yet.",
            ),
        )

    return app


def _candidate_scope(user_context: dict[str, Any]) -> tuple[str | None, str | None]:
    route_key = user_context.get("candidate_route_key")
    intent_id = user_context.get("candidate_intent_id")
    return (
        route_key if isinstance(route_key, str) else None,
        intent_id if isinstance(intent_id, str) else None,
    )


def _auth_scope_record(auth: AuthContext) -> ApiKeyRecord:
    return ApiKeyRecord(
        key_id=auth.key_id,
        key_hash="",
        key_fingerprint="",
        environment="",
        app_id=auth.app_id,
        service_id=auth.service_id,
        allowed_intents=auth.allowed_intents,
        allowed_route_keys=auth.allowed_route_keys,
        status="active",
        expires_at=datetime.now(UTC) + timedelta(seconds=1),
        revoked_at=None,
    )
