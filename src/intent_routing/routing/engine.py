from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Protocol

from intent_routing.domain.enums import Decision, RiskType
from intent_routing.domain.schemas import FallbackPolicy, RiskPayload
from intent_routing.policy.risk import RiskEvaluation
from intent_routing.policy.service_policy import ServiceOffTopicPolicy
from intent_routing.routing.scoring import (
    CandidateScore,
    DecisionComposer,
    RoutingDecisionResult,
    ThresholdConfig,
    compute_intent_confidence,
)


@dataclass(frozen=True, slots=True)
class ActiveReleaseContext:
    release_version: str
    service_id: str | None = None
    policy_version: str | None = None
    intent_catalog_version: str | None = None
    model_version: str | None = None
    vector_index_version: str | None = None
    test_run_id: str | None = None
    threshold_preset: str = "balanced"
    threshold: float | None = None
    threshold_value: float | None = None
    clarify_margin: float = 0.08
    min_candidate_score: float = 0.55
    fallback_score: float = 0.45
    policy: Mapping[str, object] = field(default_factory=dict)
    catalog_snapshot: Mapping[str, object] = field(default_factory=dict)
    max_input_tokens: int = 256
    off_topic_policy: ServiceOffTopicPolicy | None = None

    def __post_init__(self) -> None:
        if self.threshold is None and self.threshold_value is not None:
            object.__setattr__(self, "threshold", self.threshold_value)


@dataclass(frozen=True, slots=True)
class RouteInput:
    query: str
    service_id: str
    route_scope: RouteScope
    release: ActiveReleaseContext


@dataclass(frozen=True, slots=True)
class RouteScope:
    allowed_intents: list[str]
    allowed_route_keys: list[str]


@dataclass(frozen=True, slots=True)
class IntentCandidate:
    intent_id: str
    display_name: str
    domain: str
    route_key: str
    include_keywords: tuple[str, ...] = ()
    exclude_keywords: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SemanticMatch:
    positive_scores: list[float] = field(default_factory=list)
    negative_scores: list[float] = field(default_factory=list)


class RiskEvaluator(Protocol):
    def evaluate(self, query: str) -> RiskEvaluation: ...


CandidateLoader = Callable[[str, ActiveReleaseContext], list[IntentCandidate]]
SemanticSearch = Callable[
    [str, list[IntentCandidate], ActiveReleaseContext],
    Mapping[str, SemanticMatch],
]


class RoutingEngine:
    def __init__(
        self,
        *,
        risk_policy: RiskEvaluator,
        candidate_loader: CandidateLoader,
        semantic_search: SemanticSearch,
        composer: DecisionComposer | None = None,
    ) -> None:
        self.risk_policy = risk_policy
        self.candidate_loader = candidate_loader
        self.semantic_search = semantic_search
        self.composer = composer

    def route(self, route_input: RouteInput) -> RoutingDecisionResult:
        risk_evaluation = self.risk_policy.evaluate(route_input.query)
        if risk_evaluation.matched:
            risk_type = risk_evaluation.risk_type or RiskType.abuse
            return RoutingDecisionResult(
                decision=Decision.risk,
                risk=RiskPayload(
                    risk_type=risk_type,
                    action=risk_evaluation.action or "block",
                    message=risk_evaluation.message or "Blocked by risk policy.",
                ),
                decision_state={
                    "decision_reason": "risk_policy_match",
                    "risk_type": risk_type.value,
                    "action": risk_evaluation.action or "block",
                },
            )

        candidates = list(self.candidate_loader(route_input.service_id, route_input.release))
        semantic_matches = self.semantic_search(route_input.query, candidates, route_input.release)
        scored_candidates = [
            self._score_candidate(
                route_input.query,
                candidate,
                semantic_matches.get(candidate.intent_id),
            )
            for candidate in candidates
        ]
        composer = self.composer or DecisionComposer(
            ThresholdConfig(
                preset=route_input.release.threshold_preset,
                threshold=route_input.release.threshold,
                clarify_margin=route_input.release.clarify_margin,
                min_candidate_score=route_input.release.min_candidate_score,
                fallback_score=route_input.release.fallback_score,
            )
        )
        semantic_decision = composer.compose(
            scored_candidates,
            allowed_intents=set(route_input.route_scope.allowed_intents),
            allowed_route_keys=set(route_input.route_scope.allowed_route_keys),
        )
        if semantic_decision.decision == Decision.confident:
            return semantic_decision

        off_topic_decision = self._off_topic_decision(route_input)
        if off_topic_decision is not None:
            return off_topic_decision
        return semantic_decision

    def _off_topic_decision(self, route_input: RouteInput) -> RoutingDecisionResult | None:
        off_topic_policy = route_input.release.off_topic_policy
        if off_topic_policy is None:
            return None

        off_topic_evaluation = off_topic_policy.evaluate(route_input.query)
        if not off_topic_evaluation.matched:
            return None

        fallback_policy = off_topic_evaluation.fallback_policy or FallbackPolicy(
            type="client_fallback",
            retryable=False,
            recommended_action="handoff_to_default_channel",
            message=off_topic_evaluation.message,
        )
        return RoutingDecisionResult(
            decision=Decision.off_topic,
            fallback_policy=fallback_policy,
            decision_state={
                "decision_reason": "off_topic_policy_match",
                "matched_keywords": [
                    keyword
                    for keyword in off_topic_policy.keywords
                    if keyword.casefold() in route_input.query.casefold()
                ],
            },
        )

    def _score_candidate(
        self,
        query: str,
        candidate: IntentCandidate,
        semantic_match: SemanticMatch | None,
    ) -> CandidateScore:
        normalized_query = query.casefold()
        include_count = self._keyword_match_count(normalized_query, candidate.include_keywords)
        exclude_count = self._keyword_match_count(normalized_query, candidate.exclude_keywords)
        breakdown = compute_intent_confidence(
            positive_scores=(
                list(semantic_match.positive_scores) if semantic_match is not None else []
            ),
            negative_scores=(
                list(semantic_match.negative_scores) if semantic_match is not None else []
            ),
            include_keyword_match_count=include_count,
            exclude_keyword_match_count=exclude_count,
        )
        return CandidateScore(
            intent_id=candidate.intent_id,
            display_name=candidate.display_name,
            domain=candidate.domain,
            route_key=candidate.route_key,
            confidence=breakdown.confidence,
            positive_score=breakdown.positive_score,
            negative_score=breakdown.negative_score,
            include_keyword_match_count=include_count,
            exclude_keyword_match_count=exclude_count,
            keyword_boost=breakdown.keyword_boost,
            keyword_penalty=breakdown.keyword_penalty,
            negative_penalty=breakdown.negative_penalty,
        )

    def _keyword_match_count(self, normalized_query: str, keywords: tuple[str, ...]) -> int:
        match_count = 0
        for keyword in keywords:
            normalized_keyword = keyword.strip()
            if normalized_keyword and normalized_keyword.casefold() in normalized_query:
                match_count += 1
        return match_count
