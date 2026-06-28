from typing import Any, cast

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from intent_routing.api.admin import router as admin_router
from intent_routing.api.runtime import router as runtime_router
from intent_routing.db.session import session_scope
from intent_routing.domain.enums import ErrorCode
from intent_routing.domain.schemas import ErrorEnvelope, ErrorInfo, FallbackPolicy
from intent_routing.health import build_readiness_payload
from intent_routing.logging.trace import (
    RUNTIME_ERROR_LOGGED_HEADER,
    RuntimeErrorLog,
    begin_request_timer,
    build_trace_id,
    extract_runtime_query,
    log_runtime_preflight_error,
    should_log_runtime_error,
)


def create_app() -> FastAPI:
    app = FastAPI(title="Intent Routing Service")
    app.state.runtime_log_session_factory = session_scope
    app.state.readiness_session_factory = session_scope
    app.include_router(admin_router)
    app.include_router(runtime_router)

    @app.middleware("http")
    async def record_request_timing(request: Request, call_next: Any) -> Response:
        begin_request_timer(request)
        return cast("Response", await call_next(request))

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        if should_log_runtime_error(
            request,
            already_logged=(
                exc.headers is not None
                and exc.headers.get(RUNTIME_ERROR_LOGGED_HEADER) == "1"
            ),
            detail=exc.detail,
        ):
            detail = exc.detail
            assert isinstance(detail, dict)
            error_payload = detail.get("error", {})
            trace_id = detail.get("trace_id")
            request_id = detail.get("request_id") or request.headers.get("X-Request-Id")
            error_code = _error_code_from_payload(error_payload)
            if isinstance(trace_id, str) and error_code is not None:
                query_raw = await extract_runtime_query(request)
                category, layer = _runtime_error_metadata(error_payload, error_code)
                log_runtime_preflight_error(
                    request,
                    trace_id=trace_id,
                    request_id=request_id if isinstance(request_id, str) else None,
                    error=RuntimeErrorLog(
                        code=error_code,
                        category=category,
                        layer=layer,
                        message=str(error_payload.get("message", "Request failed.")),
                        retryable=bool(error_payload.get("retryable", False)),
                    ),
                    http_status=exc.status_code,
                    query_raw=query_raw,
                    release_version=(
                        detail.get("release_version")
                        if isinstance(detail.get("release_version"), str)
                        else None
                    ),
                    encrypt_raw_query=_should_encrypt_runtime_fallback(detail, layer),
                )
        if isinstance(exc.detail, dict) and exc.detail.get("status") == "error":
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        _exc: RequestValidationError,
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-Id")
        envelope = ErrorEnvelope(
            trace_id=build_trace_id(),
            request_id=request_id if request_id else None,
            error=ErrorInfo(
                code=ErrorCode.INVALID_REQUEST,
                message="Request validation failed.",
                retryable=False,
            ),
        ).model_dump(mode="json", exclude_none=True)
        if should_log_runtime_error(request, already_logged=False, detail=envelope):
            query_raw = await extract_runtime_query(request)
            category, layer = _preflight_error_metadata(ErrorCode.INVALID_REQUEST)
            log_runtime_preflight_error(
                request,
                trace_id=str(envelope["trace_id"]),
                request_id=request_id if request_id else None,
                error=RuntimeErrorLog(
                    code=ErrorCode.INVALID_REQUEST,
                    category=category,
                    layer=layer,
                    message="Request validation failed.",
                    retryable=False,
                ),
                http_status=422,
                query_raw=query_raw,
            )
        return JSONResponse(
            status_code=422,
            content=envelope,
        )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz(request: Request) -> JSONResponse:
        payload = build_readiness_payload(request.app.state.readiness_session_factory)
        status_code = 200 if payload["status"] == "ready" else 503
        return JSONResponse(status_code=status_code, content=payload)

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )
        _document_validation_errors_as_error_envelope(openapi_schema)
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


def _error_code_from_payload(payload: object) -> ErrorCode | None:
    if not isinstance(payload, dict):
        return None
    raw_code = payload.get("code")
    if not isinstance(raw_code, str):
        return None
    try:
        return ErrorCode(raw_code)
    except ValueError:
        return None


def _preflight_error_metadata(code: ErrorCode) -> tuple[str, str]:
    if code == ErrorCode.AUTHENTICATION_FAILED:
        return ("authentication_error", "auth_layer")
    if code == ErrorCode.SERVICE_SCOPE_DENIED:
        return ("authorization_error", "auth_layer")
    if code == ErrorCode.INVALID_REQUEST:
        return ("validation_error", "request_layer")
    return ("request_error", "request_layer")


def _runtime_error_metadata(payload: object, code: ErrorCode) -> tuple[str, str]:
    if isinstance(payload, dict):
        category = payload.get("category")
        layer = payload.get("layer")
        if isinstance(category, str) and isinstance(layer, str):
            return (category, layer)
    return _preflight_error_metadata(code)


def _should_encrypt_runtime_fallback(detail: dict[str, Any], layer: str) -> bool:
    if layer == "runtime_logging":
        return False
    return isinstance(detail.get("release_version"), str)
