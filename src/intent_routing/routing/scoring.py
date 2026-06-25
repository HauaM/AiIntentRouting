from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from intent_routing.domain.enums import Decision, ThresholdPreset
from intent_routing.domain.schemas import (
    ClarifyCandidate,
    ClarifyPayload,
    FallbackPolicy,
    RiskPayload,
)

CLARIFY_MARGIN = 0.08
MIN_CANDIDATE_SCORE = 0.55
FALLBACK_SCORE = 0.45
MAX_CLARIFY_CANDIDATES = 3
THRESHOLD_PRESETS: dict[ThresholdPreset, float] = {
    ThresholdPreset.strict: ThresholdPreset.strict.threshold,
    ThresholdPreset.balanced: ThresholdPreset.balanced.threshold,
    ThresholdPreset.exploratory: ThresholdPreset.exploratory.threshold,
}


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    positive_score: float
    negative_score: float
    keyword_boost: float
    keyword_penalty: float
    negative_penalty: float
    confidence: float


@dataclass(frozen=True, slots=True)
class CandidateScore:
    intent_id: str
    display_name: str
    domain: str
    route_key: str
    confidence: float


@dataclass(frozen=True, slots=True)
class RoutingDecisionResult:
    decision: Decision
    domain: str | None = None
    intent_id: str | None = None
    confidence: float | None = None
    margin: float | None = None
    route_key: str | None = None
    fallback_policy: FallbackPolicy | None = None
    clarify_question: str | None = None
    clarify: ClarifyPayload | None = None
    risk: RiskPayload | None = None


@dataclass(frozen=True, slots=True)
class ThresholdConfig:
    preset: str | ThresholdPreset = ThresholdPreset.balanced
    threshold: float | None = None
    clarify_margin: float = CLARIFY_MARGIN
    min_candidate_score: float = MIN_CANDIDATE_SCORE
    fallback_score: float = FALLBACK_SCORE
    max_clarify_candidates: int = MAX_CLARIFY_CANDIDATES

    def __post_init__(self) -> None:
        preset = (
            self.preset
            if isinstance(self.preset, ThresholdPreset)
            else ThresholdPreset(self.preset)
        )
        object.__setattr__(self, "preset", preset)
        if self.threshold is None:
            object.__setattr__(self, "threshold", THRESHOLD_PRESETS[preset])

    @property
    def resolved_threshold(self) -> float:
        threshold = self.threshold
        if threshold is None:
            preset = (
                self.preset
                if isinstance(self.preset, ThresholdPreset)
                else ThresholdPreset(self.preset)
            )
            return THRESHOLD_PRESETS[preset]
        return threshold


def compute_intent_confidence(
    positive_scores: list[float],
    negative_scores: list[float],
    include_keyword_match_count: int,
    exclude_keyword_match_count: int,
) -> ScoreBreakdown:
    positive_score = max(positive_scores, default=0.0)
    negative_score = max(negative_scores, default=0.0)
    keyword_boost = min(0.08, 0.02 * include_keyword_match_count)
    keyword_penalty = min(0.12, 0.03 * exclude_keyword_match_count)
    negative_penalty = max(0.0, negative_score - 0.55) * 0.5
    confidence = _clamp(
        positive_score + keyword_boost - keyword_penalty - negative_penalty,
        0.0,
        1.0,
    )
    return ScoreBreakdown(
        positive_score=positive_score,
        negative_score=negative_score,
        keyword_boost=keyword_boost,
        keyword_penalty=keyword_penalty,
        negative_penalty=negative_penalty,
        confidence=confidence,
    )


@dataclass(slots=True)
class DecisionComposer:
    threshold_config: ThresholdConfig
    allowed_intents: set[str] | None = None
    allowed_route_keys: set[str] | None = None
    _clarify_message: str = field(default="Which of these best matches your request?", init=False)

    def compose(
        self,
        candidates: Iterable[CandidateScore],
        *,
        allowed_intents: set[str] | None = None,
        allowed_route_keys: set[str] | None = None,
    ) -> RoutingDecisionResult:
        ranked = sorted(candidates, key=lambda candidate: candidate.confidence, reverse=True)
        if not ranked:
            return self._fallback()

        top_candidate = ranked[0]
        margin = (
            top_candidate.confidence
            if len(ranked) == 1
            else top_candidate.confidence - ranked[1].confidence
        )
        if top_candidate.confidence < self.threshold_config.fallback_score:
            return self._fallback(top_candidate=top_candidate, margin=margin)

        if not self._is_authorized(
            top_candidate,
            allowed_intents=allowed_intents,
            allowed_route_keys=allowed_route_keys,
        ):
            return RoutingDecisionResult(
                decision=Decision.unauthorized,
                domain=top_candidate.domain,
                confidence=top_candidate.confidence,
                margin=margin,
                fallback_policy=FallbackPolicy(
                    type="client_fallback",
                    retryable=False,
                    recommended_action="deny_route",
                ),
            )

        if (
            top_candidate.confidence >= self.threshold_config.resolved_threshold
            and margin >= self.threshold_config.clarify_margin
        ):
            return self._decision(Decision.confident, top_candidate, margin)

        viable_candidates = [
            candidate
            for candidate in ranked
            if candidate.confidence >= self.threshold_config.min_candidate_score
        ]
        if len(viable_candidates) >= 2 and margin < self.threshold_config.clarify_margin:
            return self._clarify(
                reason="top_candidates_close",
                top_candidate=top_candidate,
                margin=margin,
                candidates=viable_candidates,
            )

        if (
            top_candidate.confidence >= self.threshold_config.min_candidate_score
            and top_candidate.confidence < self.threshold_config.resolved_threshold
        ):
            return self._clarify(
                reason="below_threshold",
                top_candidate=top_candidate,
                margin=margin,
                candidates=viable_candidates or [top_candidate],
            )

        return self._fallback(top_candidate=top_candidate, margin=margin)

    def _decision(
        self,
        decision: Decision,
        top_candidate: CandidateScore,
        margin: float,
    ) -> RoutingDecisionResult:
        return RoutingDecisionResult(
            decision=decision,
            domain=top_candidate.domain,
            intent_id=top_candidate.intent_id,
            confidence=top_candidate.confidence,
            margin=margin,
            route_key=top_candidate.route_key,
        )

    def _clarify(
        self,
        *,
        reason: str,
        top_candidate: CandidateScore,
        margin: float,
        candidates: list[CandidateScore],
    ) -> RoutingDecisionResult:
        clarify_candidates = [
            ClarifyCandidate(
                intent_id=candidate.intent_id,
                display_name=candidate.display_name,
                route_key=candidate.route_key,
                confidence=candidate.confidence,
            )
            for candidate in candidates[: self.threshold_config.max_clarify_candidates]
        ]
        return RoutingDecisionResult(
            decision=Decision.clarify,
            domain=top_candidate.domain,
            confidence=top_candidate.confidence,
            margin=margin,
            clarify_question=self._clarify_message,
            clarify=ClarifyPayload(
                reason=reason,
                message=self._clarify_message,
                candidates=clarify_candidates,
            ),
            fallback_policy=FallbackPolicy(
                type="client_fallback",
                retryable=True,
                recommended_action="ask_clarifying_question",
            ),
        )

    def _fallback(
        self,
        *,
        top_candidate: CandidateScore | None = None,
        margin: float | None = None,
    ) -> RoutingDecisionResult:
        return RoutingDecisionResult(
            decision=Decision.fallback,
            domain=top_candidate.domain if top_candidate is not None else None,
            confidence=top_candidate.confidence if top_candidate is not None else None,
            margin=margin,
            fallback_policy=FallbackPolicy(
                type="client_fallback",
                retryable=True,
                recommended_action="ask_for_rephrase",
                message="No confident intent match found.",
            ),
        )

    def _is_authorized(
        self,
        candidate: CandidateScore,
        *,
        allowed_intents: set[str] | None,
        allowed_route_keys: set[str] | None,
    ) -> bool:
        effective_allowed_intents = (
            self.allowed_intents if allowed_intents is None else allowed_intents
        )
        effective_allowed_route_keys = (
            self.allowed_route_keys if allowed_route_keys is None else allowed_route_keys
        )
        if effective_allowed_intents and candidate.intent_id not in effective_allowed_intents:
            return False
        if effective_allowed_route_keys and candidate.route_key not in effective_allowed_route_keys:
            return False
        return True
