from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from intent_routing.api.admin import router as admin_router
from intent_routing.api.dependencies import AuthContext, require_api_key
from intent_routing.domain.enums import Decision, ErrorCode
from intent_routing.domain.schemas import (
    ErrorEnvelope,
    ErrorInfo,
    FallbackPolicy,
    RuntimeRequest,
    RuntimeResponse,
)
from intent_routing.security.api_keys import ApiKeyRecord, check_scope


def create_app() -> FastAPI:
    app = FastAPI(title="Intent Routing Service")
    app.include_router(admin_router)

    @app.exception_handler(HTTPException)
    def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and exc.detail.get("status") == "error":
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    def validation_exception_handler(
        request: Request,
        _exc: RequestValidationError,
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-Id")
        return JSONResponse(
            status_code=422,
            content=ErrorEnvelope(
                trace_id=f"irt-{uuid4().hex}",
                request_id=request_id if request_id else None,
                error=ErrorInfo(
                    code=ErrorCode.INVALID_REQUEST,
                    message="Request validation failed.",
                    retryable=False,
                ),
            ).model_dump(mode="json", exclude_none=True),
        )

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

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )
        _document_validation_errors_as_error_envelope(openapi_schema)
        _document_intent_patch_request_without_explicit_nulls(openapi_schema)
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    return app


def _document_validation_errors_as_error_envelope(
    openapi_schema: dict[str, Any],
) -> None:
    components = openapi_schema.setdefault("components", {}).setdefault("schemas", {})
    for model in (FallbackPolicy, ErrorInfo, ErrorEnvelope):
        model_schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
        definitions = model_schema.pop("$defs", {})
        components.update(definitions)
        components[model.__name__] = model_schema

    components.pop("HTTPValidationError", None)
    components.pop("ValidationError", None)

    for path_item in openapi_schema.get("paths", {}).values():
        if not isinstance(path_item, dict):
            continue
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses")
            if not isinstance(responses, dict) or "422" not in responses:
                continue
            responses["422"] = {
                "description": "Validation Error",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorEnvelope"}
                    }
                },
            }


def _document_intent_patch_request_without_explicit_nulls(
    openapi_schema: dict[str, Any],
) -> None:
    schemas = openapi_schema.get("components", {}).get("schemas", {})
    intent_patch_schema = schemas.get("IntentPatchRequest")
    if not isinstance(intent_patch_schema, dict):
        return
    properties = intent_patch_schema.get("properties", {})
    if not isinstance(properties, dict):
        return

    for field_schema in properties.values():
        if isinstance(field_schema, dict):
            _remove_null_schema(field_schema)


def _remove_null_schema(schema: dict[str, Any]) -> None:
    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        non_null_options = [
            option
            for option in any_of
            if not (isinstance(option, dict) and option.get("type") == "null")
        ]
        if len(non_null_options) == 1 and isinstance(non_null_options[0], dict):
            schema.pop("anyOf")
            schema.update(non_null_options[0])
        else:
            schema["anyOf"] = non_null_options

    for value in schema.values():
        if isinstance(value, dict):
            _remove_null_schema(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _remove_null_schema(item)


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
