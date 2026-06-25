from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from time import perf_counter
from typing import Annotated, Any, NoReturn, Protocol, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from intent_routing.api.dependencies import (
    AuthContext,
    get_runtime_environment,
    require_api_key,
)
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.db.session import session_scope
from intent_routing.domain.enums import Decision, ErrorCode
from intent_routing.domain.schemas import (
    ErrorEnvelope,
    ErrorInfo,
    FallbackPolicy,
    RuntimeRequest,
    RuntimeResponse,
)
from intent_routing.embedding.provider import EmbeddingProvider, get_embedding_provider
from intent_routing.logging.trace import (
    RuntimeErrorLog,
    RuntimeTraceConfigurationError,
    RuntimeTraceLogger,
    build_trace_id,
)
from intent_routing.policy.risk import RiskPolicy
from intent_routing.policy.service_policy import ServiceOffTopicPolicy
from intent_routing.routing.engine import (
    ActiveReleaseContext,
    IntentCandidate,
    RouteInput,
    RouteScope,
    RoutingEngine,
    SemanticMatch,
)
from intent_routing.routing.scoring import RoutingDecisionResult

router = APIRouter()


class ExampleSearch(Protocol):
    def __call__(
        self,
        repository: IntentRoutingRepository,
        service_id: str,
        query_embedding: list[float],
        *,
        limit: int,
    ) -> list[Any]: ...


@dataclass(frozen=True, slots=True)
class RuntimeApiError(Exception):
    status_code: int
    code: ErrorCode
    message: str
    retryable: bool
    category: str
    layer: str


def get_runtime_session() -> Iterator[Session]:
    with session_scope() as session:
        yield session


def get_example_search() -> ExampleSearch:
    return _search_examples


@router.post("/v1/intent-route", response_model=RuntimeResponse)
def intent_route(
    runtime_request: RuntimeRequest,
    auth: Annotated[AuthContext, Depends(require_api_key)],
    session: Annotated[Session, Depends(get_runtime_session)],
    environment: Annotated[str, Depends(get_runtime_environment)],
    example_search: Annotated[ExampleSearch, Depends(get_example_search)],
) -> RuntimeResponse:
    trace_id = build_trace_id()
    started_at = perf_counter()
    repository = IntentRoutingRepository(session)
    logger = RuntimeTraceLogger(repository)
    release: ActiveReleaseContext | None = None

    try:
        release = _load_active_release(
            repository,
            service_id=auth.service_id,
            environment=environment,
        )
        route_scope = RouteScope(
            allowed_intents=auth.allowed_intents,
            allowed_route_keys=auth.allowed_route_keys,
        )
        embedding_provider = _resolve_embedding_provider()
        engine = _routing_engine(
            repository=repository,
            release=release,
            embedding_provider=embedding_provider,
            example_search=example_search,
        )
        decision = engine.route(
            RouteInput(
                query=runtime_request.query,
                service_id=auth.service_id,
                route_scope=route_scope,
                release=release,
            )
        )
        response = _runtime_response(
            decision,
            trace_id=trace_id,
            request_id=auth.request_id,
            release_version=release.release_version,
        )
        logger.log_success(
            trace_id=trace_id,
            request_id=auth.request_id,
            app_id=auth.app_id,
            service_id=auth.service_id,
            release=release,
            decision=decision,
            query_raw=runtime_request.query,
            latency_ms=_latency_ms(started_at),
        )
        session.commit()
        return response
    except RuntimeApiError as exc:
        _log_and_raise(
            session=session,
            logger=logger,
            trace_id=trace_id,
            request_id=auth.request_id,
            app_id=auth.app_id,
            service_id=auth.service_id,
            release=release,
            query=runtime_request.query,
            error=RuntimeErrorLog(
                code=exc.code,
                category=exc.category,
                layer=exc.layer,
                message=exc.message,
                retryable=exc.retryable,
            ),
            http_status=exc.status_code,
            latency_ms=_latency_ms(started_at),
        )
    except RuntimeTraceConfigurationError:
        _log_and_raise(
            session=session,
            logger=logger,
            trace_id=trace_id,
            request_id=auth.request_id,
            app_id=auth.app_id,
            service_id=auth.service_id,
            release=release,
            query=runtime_request.query,
            error=RuntimeErrorLog(
                code=ErrorCode.INTERNAL_ERROR,
                category="internal_error",
                layer="runtime_logging",
                message="Runtime logging is temporarily unavailable.",
                retryable=False,
            ),
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            latency_ms=_latency_ms(started_at),
        )
    except Exception:
        _log_and_raise(
            session=session,
            logger=logger,
            trace_id=trace_id,
            request_id=auth.request_id,
            app_id=auth.app_id,
            service_id=auth.service_id,
            release=release,
            query=runtime_request.query,
            error=RuntimeErrorLog(
                code=ErrorCode.INTERNAL_ERROR,
                category="internal_error",
                layer="runtime_api",
                message="Routing could not be completed.",
                retryable=False,
            ),
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            latency_ms=_latency_ms(started_at),
        )


def _routing_engine(
    *,
    repository: IntentRoutingRepository,
    release: ActiveReleaseContext,
    embedding_provider: EmbeddingProvider,
    example_search: ExampleSearch,
) -> RoutingEngine:
    risk_policy_config = release.policy.get("risk_policy")
    risk_enabled = True
    if isinstance(risk_policy_config, Mapping):
        risk_enabled = bool(risk_policy_config.get("enabled", True))
    return RoutingEngine(
        risk_policy=RiskPolicy(enabled=risk_enabled),
        candidate_loader=lambda service_id, release: _load_candidates(
            repository,
            service_id=service_id,
            release=release,
        ),
        semantic_search=lambda query, candidates, release: _semantic_matches(
            repository,
            embedding_provider=embedding_provider,
            example_search=example_search,
            service_id=release.service_id or "",
            query=query,
            candidates=candidates,
            release=release,
        ),
    )


def _load_active_release(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    environment: str,
) -> ActiveReleaseContext:
    release = repository.get_active_release(service_id, environment)
    if release is None:
        raise RuntimeApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.ACTIVE_RELEASE_NOT_FOUND,
            message="No active release is available for this service.",
            retryable=False,
            category="configuration_error",
            layer="release_layer",
        )

    policy_version = repository.get_policy_version(service_id, release.policy_version)
    catalog_version = repository.get_catalog_version(service_id, release.intent_catalog_version)
    test_run = repository.get_test_run(release.test_run_id)
    service = repository.get_service(service_id)
    if (
        policy_version is None
        or catalog_version is None
        or test_run is None
        or not test_run.gate_passed
        or service is None
    ):
        raise RuntimeApiError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=ErrorCode.POLICY_LOAD_FAILED,
            message="Release dependencies are temporarily unavailable.",
            retryable=True,
            category="dependency_failure",
            layer="policy_layer",
        )

    off_topic_policy = _off_topic_policy(policy_version.off_topic_policy)
    return ActiveReleaseContext(
        release_version=release.release_version,
        service_id=service_id,
        policy_version=policy_version.policy_version,
        intent_catalog_version=catalog_version.intent_catalog_version,
        model_version=release.model_version,
        vector_index_version=release.vector_index_version,
        threshold_preset=policy_version.threshold_preset,
        threshold=float(policy_version.threshold_value),
        threshold_value=float(policy_version.threshold_value),
        clarify_margin=float(policy_version.clarify_margin),
        min_candidate_score=float(policy_version.min_candidate_score),
        fallback_score=float(policy_version.fallback_score),
        policy={
            "risk_policy": policy_version.risk_policy,
            "off_topic_policy": policy_version.off_topic_policy,
        },
        catalog_snapshot=catalog_version.snapshot,
        max_input_tokens=service.max_input_tokens,
        off_topic_policy=off_topic_policy,
    )


def _off_topic_policy(config: Mapping[str, Any]) -> ServiceOffTopicPolicy | None:
    enabled = bool(config.get("enabled"))
    keywords = [
        value
        for value in config.get("keywords", [])
        if isinstance(value, str)
    ]
    fallback_payload = config.get("fallback_policy")
    fallback_policy = None
    if isinstance(fallback_payload, Mapping):
        fallback_policy = FallbackPolicy.model_validate(dict(fallback_payload))
    return ServiceOffTopicPolicy(
        enabled=enabled,
        keywords=keywords,
        message=str(config.get("message", "Request is outside the service policy.")),
        fallback_policy=fallback_policy,
    )


def _load_candidates(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    release: ActiveReleaseContext,
) -> list[IntentCandidate]:
    snapshot = release.catalog_snapshot.get("intents")
    candidates = _candidates_from_snapshot(snapshot)
    if candidates:
        return candidates
    return [
        IntentCandidate(
            intent_id=intent.intent_id,
            display_name=intent.display_name,
            domain=intent.domain,
            route_key=intent.route_key,
            include_keywords=tuple(intent.include_keywords or []),
            exclude_keywords=tuple(intent.exclude_keywords or []),
        )
        for intent in repository.list_active_intents(service_id)
    ]


def _candidates_from_snapshot(snapshot: object) -> list[IntentCandidate]:
    if not isinstance(snapshot, Iterable) or isinstance(snapshot, (str, bytes, bytearray)):
        return []
    candidates: list[IntentCandidate] = []
    for item in snapshot:
        if not isinstance(item, Mapping):
            continue
        intent_id = item.get("intent_id")
        display_name = item.get("display_name")
        domain = item.get("domain")
        route_key = item.get("route_key")
        if not all(
            isinstance(value, str)
            for value in (intent_id, display_name, domain, route_key)
        ):
            continue
        resolved_intent_id = cast("str", intent_id)
        resolved_display_name = cast("str", display_name)
        resolved_domain = cast("str", domain)
        resolved_route_key = cast("str", route_key)
        candidates.append(
            IntentCandidate(
                intent_id=resolved_intent_id,
                display_name=resolved_display_name,
                domain=resolved_domain,
                route_key=resolved_route_key,
                include_keywords=tuple(_string_list(item.get("include_keywords"))),
                exclude_keywords=tuple(_string_list(item.get("exclude_keywords"))),
            )
        )
    return candidates


def _string_list(raw_values: object) -> list[str]:
    if not isinstance(raw_values, Iterable) or isinstance(raw_values, (str, bytes, bytearray)):
        return []
    return [value for value in raw_values if isinstance(value, str)]


def _semantic_matches(
    repository: IntentRoutingRepository,
    *,
    embedding_provider: EmbeddingProvider,
    example_search: ExampleSearch,
    service_id: str,
    query: str,
    candidates: list[IntentCandidate],
    release: ActiveReleaseContext,
) -> Mapping[str, SemanticMatch]:
    if not candidates:
        return {}

    try:
        embeddings = embedding_provider.embed_texts(
            [query],
            max_tokens=release.max_input_tokens,
        )
    except Exception as exc:
        raise RuntimeApiError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=ErrorCode.EMBEDDING_MODEL_UNAVAILABLE,
            message="Embedding dependency is temporarily unavailable.",
            retryable=True,
            category="dependency_failure",
            layer="embedding_layer",
        ) from exc
    if len(embeddings) != 1 or len(embeddings[0]) != embedding_provider.dimension:
        raise RuntimeApiError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=ErrorCode.EMBEDDING_MODEL_UNAVAILABLE,
            message="Embedding dependency is temporarily unavailable.",
            retryable=True,
            category="dependency_failure",
            layer="embedding_layer",
        )

    try:
        example_rows = example_search(
            repository,
            service_id,
            embeddings[0],
            limit=max(8, len(candidates) * 4),
        )
    except Exception as exc:
        raise RuntimeApiError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=ErrorCode.VECTOR_STORE_UNAVAILABLE,
            message="Vector search is temporarily unavailable.",
            retryable=True,
            category="dependency_failure",
            layer="semantic_layer",
        ) from exc

    candidate_ids = {candidate.intent_id for candidate in candidates}
    grouped: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {"positive": [], "negative": []}
    )
    for row in example_rows:
        intent_id = getattr(row, "intent_id", None)
        example_type = getattr(row, "example_type", None)
        similarity = getattr(row, "similarity", None)
        if (
            intent_id not in candidate_ids
            or example_type not in {"positive", "negative"}
            or not isinstance(similarity, float)
        ):
            continue
        grouped[intent_id][example_type].append(similarity)

    return {
        intent_id: SemanticMatch(
            positive_scores=payload["positive"],
            negative_scores=payload["negative"],
        )
        for intent_id, payload in grouped.items()
    }


def _search_examples(
    repository: IntentRoutingRepository,
    service_id: str,
    query_embedding: list[float],
    *,
    limit: int,
) -> list[Any]:
    return repository.search_approved_examples_by_embedding(
        service_id,
        query_embedding,
        limit=limit,
    )


def _resolve_embedding_provider() -> EmbeddingProvider:
    try:
        return get_embedding_provider()
    except Exception as exc:
        raise RuntimeApiError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=ErrorCode.EMBEDDING_MODEL_UNAVAILABLE,
            message="Embedding dependency is temporarily unavailable.",
            retryable=True,
            category="dependency_failure",
            layer="embedding_layer",
        ) from exc


def _runtime_response(
    decision: RoutingDecisionResult,
    *,
    trace_id: str,
    request_id: str | None,
    release_version: str,
) -> RuntimeResponse:
    return RuntimeResponse(
        trace_id=trace_id,
        request_id=request_id,
        decision=decision.decision,
        domain=decision.domain,
        intent_id=decision.intent_id if decision.decision == Decision.confident else None,
        confidence=decision.confidence,
        route_key=decision.route_key if decision.decision == Decision.confident else None,
        clarify_question=decision.clarify_question,
        fallback_policy=decision.fallback_policy,
        clarify=decision.clarify,
        risk=decision.risk,
        release_version=release_version,
    )


def _log_and_raise(
    *,
    session: Session,
    logger: RuntimeTraceLogger,
    trace_id: str,
    request_id: str | None,
    app_id: str | None,
    service_id: str | None,
    release: ActiveReleaseContext | None,
    query: str | None,
    error: RuntimeErrorLog,
    http_status: int,
    latency_ms: int,
) -> NoReturn:
    envelope = ErrorEnvelope(
        trace_id=trace_id,
        request_id=request_id,
        release_version=release.release_version if release is not None else None,
        error=ErrorInfo(
            code=error.code,
            message=error.message,
            retryable=error.retryable,
            category=error.category,
            layer=error.layer,
        ),
    )
    try:
        logger.log_error(
            trace_id=trace_id,
            request_id=request_id,
            app_id=app_id,
            service_id=service_id,
            release=release,
            error=error,
            http_status=http_status,
            latency_ms=latency_ms,
            query_raw=query,
        )
        session.commit()
    except Exception:
        session.rollback()
    raise HTTPException(
        status_code=http_status,
        detail=envelope.model_dump(mode="json", exclude_none=True),
    )


def _latency_ms(started_at: float) -> int:
    return max(0, int((perf_counter() - started_at) * 1000))
