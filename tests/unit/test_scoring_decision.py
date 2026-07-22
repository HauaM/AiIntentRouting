from __future__ import annotations

from dataclasses import dataclass

import pytest

from intent_routing.domain.enums import Decision, RiskType
from intent_routing.domain.schemas import FallbackPolicy
from intent_routing.policy.risk import RiskEvaluation
from intent_routing.policy.service_policy import ServiceOffTopicPolicy
from intent_routing.routing.engine import (
    ActiveReleaseContext,
    IntentCandidate,
    RouteInput,
    RouteScope,
    RoutingEngine,
    SemanticMatch,
)
from intent_routing.routing.scoring import (
    CandidateScore,
    DecisionComposer,
    ThresholdConfig,
    compute_intent_confidence,
)


def test_custom_threshold_config_uses_explicit_threshold() -> None:
    config = ThresholdConfig(preset="custom", threshold=0.72)

    assert config.resolved_threshold == pytest.approx(0.72)


def test_confident_when_score_over_threshold_and_margin_wide() -> None:
    result = DecisionComposer(
        ThresholdConfig(preset="balanced", threshold=0.8, clarify_margin=0.08)
    ).compose(
        [
            CandidateScore(
                "it_api_timeout",
                "API Timeout",
                "IT",
                "it.api_timeout.manual_lookup",
                0.87,
            ),
            CandidateScore(
                "it_password_reset",
                "비밀번호 초기화",
                "IT",
                "it.password_reset.self_service",
                0.60,
            ),
        ]
    )

    assert result.decision == Decision.confident
    assert result.intent_id == "it_api_timeout"


def test_clarify_when_top_candidates_are_close() -> None:
    result = DecisionComposer(
        ThresholdConfig(preset="balanced", threshold=0.8, clarify_margin=0.08)
    ).compose(
        [
            CandidateScore(
                "it_api_timeout",
                "API Timeout",
                "IT",
                "it.api_timeout.manual_lookup",
                0.78,
            ),
            CandidateScore(
                "it_password_reset",
                "비밀번호 초기화",
                "IT",
                "it.password_reset.self_service",
                0.75,
            ),
        ]
    )

    assert result.decision == Decision.clarify
    assert result.clarify is not None
    assert len(result.clarify.candidates) == 2
    assert result.intent_id is None
    assert result.route_key is None


def test_fallback_when_no_candidate_reaches_floor() -> None:
    result = DecisionComposer(
        ThresholdConfig(preset="balanced", threshold=0.8, clarify_margin=0.08)
    ).compose(
        [
            CandidateScore(
                "it_api_timeout",
                "API Timeout",
                "IT",
                "it.api_timeout.manual_lookup",
                0.31,
            ),
        ]
    )

    assert result.decision == Decision.fallback
    assert result.intent_id is None
    assert result.route_key is None


def test_compute_intent_confidence_applies_contract_formula() -> None:
    result = compute_intent_confidence(
        positive_scores=[0.81, 0.76],
        negative_scores=[0.62, 0.4],
        include_keyword_match_count=3,
        exclude_keyword_match_count=1,
    )

    assert result.positive_score == pytest.approx(0.81)
    assert result.negative_score == pytest.approx(0.62)
    assert result.keyword_boost == pytest.approx(0.06)
    assert result.keyword_penalty == pytest.approx(0.03)
    assert result.negative_penalty == pytest.approx(0.035)
    assert result.confidence == pytest.approx(0.805)


@pytest.mark.parametrize(
    ("positive_scores", "negative_scores", "include_count", "exclude_count", "expected"),
    [
        ([0.99], [], 12, 0, 1.0),
        ([0.2], [0.95], 0, 12, 0.0),
    ],
)
def test_compute_intent_confidence_clamps_to_bounds(
    positive_scores: list[float],
    negative_scores: list[float],
    include_count: int,
    exclude_count: int,
    expected: float,
) -> None:
    result = compute_intent_confidence(
        positive_scores=positive_scores,
        negative_scores=negative_scores,
        include_keyword_match_count=include_count,
        exclude_keyword_match_count=exclude_count,
    )

    assert result.confidence == pytest.approx(expected)


def test_below_threshold_returns_clarify_with_max_three_candidates() -> None:
    result = DecisionComposer(
        ThresholdConfig(preset="balanced", threshold=0.8, clarify_margin=0.08)
    ).compose(
        [
            CandidateScore("intent-4", "Fourth", "IT", "it.intent_4.lookup", 0.68),
            CandidateScore("intent-2", "Second", "IT", "it.intent_2.lookup", 0.69),
            CandidateScore("intent-1", "First", "IT", "it.intent_1.lookup", 0.79),
            CandidateScore("intent-3", "Third", "IT", "it.intent_3.lookup", 0.67),
        ]
    )

    assert result.decision == Decision.clarify
    assert result.clarify is not None
    assert result.clarify.reason == "below_threshold"
    assert result.intent_id is None
    assert result.route_key is None
    assert [candidate.intent_id for candidate in result.clarify.candidates] == [
        "intent-1",
        "intent-2",
        "intent-4",
    ]


def test_single_keywordless_below_threshold_candidate_falls_back_as_outside_catalog_scope() -> None:
    result = DecisionComposer(
        ThresholdConfig(preset="balanced", threshold=0.8, clarify_margin=0.08)
    ).compose(
        [
            CandidateScore(
                "it_password_reset",
                "Password reset",
                "IT",
                "it.password_reset.self_service",
                0.59,
                include_keyword_match_count=0,
            ),
        ]
    )

    assert result.decision == Decision.fallback
    assert result.intent_id is None
    assert result.route_key is None
    assert result.decision_state is not None
    assert result.decision_state["decision_reason"] == "outside_catalog_scope"


def test_keyword_supported_single_candidate_still_clarifies_below_threshold() -> None:
    result = DecisionComposer(
        ThresholdConfig(preset="balanced", threshold=0.8, clarify_margin=0.08)
    ).compose(
        [
            CandidateScore(
                "it_api_timeout",
                "API Timeout",
                "IT",
                "it.api_timeout.manual_lookup",
                0.79,
                include_keyword_match_count=1,
            ),
        ]
    )

    assert result.decision == Decision.clarify
    assert result.clarify is not None
    assert result.clarify.reason == "below_threshold"
    assert result.intent_id is None
    assert result.route_key is None


def test_weak_close_keywordless_candidates_fall_back_as_outside_catalog_scope() -> None:
    result = DecisionComposer(
        ThresholdConfig(preset="balanced", threshold=0.8, clarify_margin=0.08)
    ).compose(
        [
            CandidateScore(
                "it_vpn_access",
                "VPN Access",
                "IT",
                "it.vpn_access.ticket_create",
                0.59,
                include_keyword_match_count=0,
            ),
            CandidateScore(
                "it_password_reset",
                "Password reset",
                "IT",
                "it.password_reset.self_service",
                0.58,
                include_keyword_match_count=0,
            ),
        ]
    )

    assert result.decision == Decision.fallback
    assert result.intent_id is None
    assert result.route_key is None
    assert result.decision_state is not None
    assert result.decision_state["decision_reason"] == "outside_catalog_scope"


def test_keyword_supported_weak_close_candidates_still_clarify() -> None:
    result = DecisionComposer(
        ThresholdConfig(preset="balanced", threshold=0.8, clarify_margin=0.08)
    ).compose(
        [
            CandidateScore(
                "it_vpn_access",
                "VPN Access",
                "IT",
                "it.vpn_access.ticket_create",
                0.59,
                include_keyword_match_count=1,
            ),
            CandidateScore(
                "it_password_reset",
                "Password reset",
                "IT",
                "it.password_reset.self_service",
                0.58,
                include_keyword_match_count=0,
            ),
        ]
    )

    assert result.decision == Decision.clarify
    assert result.clarify is not None
    assert result.clarify.reason == "top_candidates_close"


def test_two_viable_keywordless_candidates_still_clarify_when_close() -> None:
    result = DecisionComposer(
        ThresholdConfig(preset="balanced", threshold=0.8, clarify_margin=0.08)
    ).compose(
        [
            CandidateScore(
                "it_api_timeout",
                "API Timeout",
                "IT",
                "it.api_timeout.manual_lookup",
                0.78,
                include_keyword_match_count=0,
            ),
            CandidateScore(
                "it_password_reset",
                "Password reset",
                "IT",
                "it.password_reset.self_service",
                0.76,
                include_keyword_match_count=0,
            ),
        ]
    )

    assert result.decision == Decision.clarify
    assert result.clarify is not None
    assert result.clarify.reason == "top_candidates_close"
    assert [candidate.intent_id for candidate in result.clarify.candidates] == [
        "it_api_timeout",
        "it_password_reset",
    ]


def test_unauthorized_when_top_candidate_is_outside_scope() -> None:
    result = DecisionComposer(
        ThresholdConfig(preset="balanced", threshold=0.8, clarify_margin=0.08),
        allowed_intents={"it_password_reset"},
        allowed_route_keys={"it.password_reset.self_service"},
    ).compose(
        [
            CandidateScore(
                "it_api_timeout",
                "API Timeout",
                "IT",
                "it.api_timeout.manual_lookup",
                0.92,
            ),
            CandidateScore(
                "it_password_reset",
                "비밀번호 초기화",
                "IT",
                "it.password_reset.self_service",
                0.61,
            ),
        ]
    )

    assert result.decision == Decision.unauthorized
    assert result.intent_id is None
    assert result.route_key is None


def test_empty_allowlists_leave_composer_routing_unrestricted() -> None:
    result = DecisionComposer(
        ThresholdConfig(preset="balanced", threshold=0.8, clarify_margin=0.08),
        allowed_intents=set(),
        allowed_route_keys=set(),
    ).compose(
        [
            CandidateScore(
                "it_api_timeout",
                "API Timeout",
                "IT",
                "it.api_timeout.manual_lookup",
                0.92,
            ),
            CandidateScore(
                "it_password_reset",
                "비밀번호 초기화",
                "IT",
                "it.password_reset.self_service",
                0.61,
            ),
        ]
    )

    assert result.decision == Decision.confident
    assert result.intent_id == "it_api_timeout"
    assert result.route_key == "it.api_timeout.manual_lookup"


def test_compose_sorts_unsorted_candidates_by_confidence() -> None:
    result = DecisionComposer(
        ThresholdConfig(preset="balanced", threshold=0.8, clarify_margin=0.08)
    ).compose(
        [
            CandidateScore("intent-low", "Low", "IT", "it.intent_low.lookup", 0.59),
            CandidateScore("intent-top", "Top", "IT", "it.intent_top.lookup", 0.86),
            CandidateScore("intent-mid", "Mid", "IT", "it.intent_mid.lookup", 0.73),
        ]
    )

    assert result.decision == Decision.confident
    assert result.intent_id == "intent-top"
    assert result.margin == pytest.approx(0.13)


def test_confident_decision_exposes_compact_decision_state() -> None:
    result = DecisionComposer(
        ThresholdConfig(preset="balanced", threshold=0.8, clarify_margin=0.08)
    ).compose(
        [
            CandidateScore(
                "intent-top",
                "Top",
                "IT",
                "it.intent_top.lookup",
                0.86,
            ),
            CandidateScore(
                "intent-mid",
                "Mid",
                "IT",
                "it.intent_mid.lookup",
                0.73,
            ),
        ]
    )

    decision_state = getattr(result, "decision_state", None)

    assert isinstance(decision_state, dict)
    assert decision_state["decision_reason"] == "threshold_met"
    assert decision_state["selected_intent_id"] == "intent-top"
    assert decision_state["ranking"][0]["intent_id"] == "intent-top"
    assert decision_state["thresholds"]["threshold"] == pytest.approx(0.8)


def test_routing_engine_short_circuits_risk() -> None:
    candidate_loader_called = False

    class BlockingRiskPolicy:
        def evaluate(self, query: str) -> RiskEvaluation:
            assert query == "drop table users"
            return RiskEvaluation(
                matched=True,
                risk_type=RiskType.dangerous_command,
                action="block",
                message="Blocked by risk policy: dangerous_command",
            )

    def candidate_loader(_service_id: str, _release: ActiveReleaseContext) -> list[IntentCandidate]:
        nonlocal candidate_loader_called
        candidate_loader_called = True
        return []

    engine = RoutingEngine(
        risk_policy=BlockingRiskPolicy(),
        candidate_loader=candidate_loader,
        semantic_search=lambda *_args, **_kwargs: {},
        composer=DecisionComposer(ThresholdConfig(preset="balanced")),
    )

    result = engine.route(
        RouteInput(
            query="drop table users",
            service_id="svc-a",
            route_scope=RouteScope(allowed_intents=[], allowed_route_keys=[]),
            release=ActiveReleaseContext(release_version="rel-1"),
        )
    )

    assert result.decision == Decision.risk
    assert result.risk is not None
    assert result.risk.risk_type == RiskType.dangerous_command
    assert candidate_loader_called is False


def test_routing_engine_scores_candidates_and_returns_composer_result() -> None:
    engine = RoutingEngine(
        risk_policy=_AllowAllRiskPolicy(),
        candidate_loader=lambda _service_id, _release: [
            IntentCandidate(
                intent_id="it_password_reset",
                display_name="비밀번호 초기화",
                domain="IT",
                route_key="it.password_reset.self_service",
                include_keywords=("비밀번호", "초기화"),
            ),
            IntentCandidate(
                intent_id="it_api_timeout",
                display_name="API Timeout",
                domain="IT",
                route_key="it.api_timeout.manual_lookup",
                include_keywords=("api", "timeout"),
            ),
        ],
        semantic_search=lambda _query, _candidates, _release: {
            "it_password_reset": SemanticMatch(positive_scores=[0.84], negative_scores=[0.1]),
            "it_api_timeout": SemanticMatch(positive_scores=[0.61], negative_scores=[0.2]),
        },
        composer=DecisionComposer(ThresholdConfig(preset="balanced")),
    )

    result = engine.route(
        RouteInput(
            query="비밀번호 초기화가 필요합니다",
            service_id="svc-a",
            route_scope=RouteScope(allowed_intents=[], allowed_route_keys=[]),
            release=ActiveReleaseContext(
                release_version="rel-1",
                off_topic_policy=ServiceOffTopicPolicy(enabled=False, keywords=[], message=""),
            ),
        )
    )

    assert result.decision == Decision.confident
    assert result.intent_id == "it_password_reset"
    assert result.route_key == "it.password_reset.self_service"
    assert result.confidence == pytest.approx(0.88)


def test_registered_out_of_business_intent_can_route_confident_before_off_topic_policy() -> None:
    semantic_search_called = False

    def semantic_search(
        _query: str,
        _candidates: list[IntentCandidate],
        _release: ActiveReleaseContext,
    ) -> dict[str, SemanticMatch]:
        nonlocal semantic_search_called
        semantic_search_called = True
        return {
            "off_topic_other_subject": SemanticMatch(
                positive_scores=[0.94],
                negative_scores=[],
            )
        }

    engine = RoutingEngine(
        risk_policy=_AllowAllRiskPolicy(),
        candidate_loader=lambda _service_id, _release: [
            IntentCandidate(
                intent_id="off_topic_other_subject",
                display_name="서비스 범위 밖 안내",
                domain="support",
                route_key="support.off_topic.other_subject",
                include_keywords=("날씨", "점심", "주가"),
            )
        ],
        semantic_search=semantic_search,
        composer=DecisionComposer(ThresholdConfig(preset="balanced")),
    )

    result = engine.route(
        RouteInput(
            query="오늘 날씨 안내는 서비스 범위 밖 안내로 보내줘",
            service_id="svc-a",
            route_scope=RouteScope(allowed_intents=[], allowed_route_keys=[]),
            release=ActiveReleaseContext(
                release_version="rel-1",
                off_topic_policy=ServiceOffTopicPolicy(
                    enabled=True,
                    keywords=["날씨"],
                    message="서비스 범위 밖 문의입니다.",
                    fallback_policy=FallbackPolicy(
                        type="client_fallback",
                        retryable=False,
                        recommended_action="handoff_to_default_channel",
                    ),
                ),
            ),
        )
    )

    assert semantic_search_called is True
    assert result.decision == Decision.confident
    assert result.intent_id == "off_topic_other_subject"
    assert result.route_key == "support.off_topic.other_subject"


def test_routing_engine_returns_off_topic_when_no_confident_catalog_route_exists() -> None:
    semantic_search_called = False

    def semantic_search(
        _query: str,
        _candidates: list[IntentCandidate],
        _release: ActiveReleaseContext,
    ) -> dict[str, SemanticMatch]:
        nonlocal semantic_search_called
        semantic_search_called = True
        return {
            "it_password_reset": SemanticMatch(positive_scores=[0.2], negative_scores=[]),
        }

    engine = RoutingEngine(
        risk_policy=_AllowAllRiskPolicy(),
        candidate_loader=lambda _service_id, _release: [
            IntentCandidate(
                intent_id="it_password_reset",
                display_name="비밀번호 초기화",
                domain="IT",
                route_key="it.password_reset.self_service",
                include_keywords=("비밀번호", "초기화"),
            )
        ],
        semantic_search=semantic_search,
        composer=DecisionComposer(ThresholdConfig(preset="balanced")),
    )

    result = engine.route(
        RouteInput(
            query="오늘 날씨 어때",
            service_id="svc-a",
            route_scope=RouteScope(allowed_intents=[], allowed_route_keys=[]),
            release=ActiveReleaseContext(
                release_version="rel-1",
                off_topic_policy=ServiceOffTopicPolicy(
                    enabled=True,
                    keywords=["날씨"],
                    message="IT Helpdesk 범위 밖 문의입니다.",
                    fallback_policy=FallbackPolicy(
                        type="client_fallback",
                        retryable=False,
                        recommended_action="handoff_to_default_channel",
                    ),
                ),
            ),
        )
    )

    assert result.decision == Decision.off_topic
    assert result.fallback_policy is not None
    assert result.fallback_policy.recommended_action == "handoff_to_default_channel"
    assert semantic_search_called is True


def test_routing_engine_falls_back_when_single_candidate_lacks_keyword_signal() -> None:
    engine = RoutingEngine(
        risk_policy=_AllowAllRiskPolicy(),
        candidate_loader=lambda _service_id, _release: [
            IntentCandidate(
                intent_id="it_password_reset",
                display_name="Password reset",
                domain="IT",
                route_key="it.password_reset.self_service",
                include_keywords=("비밀번호", "계정 잠금", "password"),
            )
        ],
        semantic_search=lambda _query, _candidates, _release: {
            "it_password_reset": SemanticMatch(positive_scores=[0.59], negative_scores=[]),
        },
        composer=DecisionComposer(ThresholdConfig(preset="balanced")),
    )

    result = engine.route(
        RouteInput(
            query="회의실 예약 변경 방법을 알려주세요",
            service_id="svc-a",
            route_scope=RouteScope(allowed_intents=[], allowed_route_keys=[]),
            release=ActiveReleaseContext(
                release_version="rel-1",
                off_topic_policy=ServiceOffTopicPolicy(enabled=False, keywords=[], message=""),
            ),
        )
    )

    assert result.decision == Decision.fallback
    assert result.decision_state is not None
    assert result.decision_state["decision_reason"] == "outside_catalog_scope"
    assert result.decision_state["ranking"][0]["score_breakdown"][
        "include_keyword_match_count"
    ] == 0


def test_routing_engine_treats_empty_scope_as_unrestricted() -> None:
    engine = RoutingEngine(
        risk_policy=_AllowAllRiskPolicy(),
        candidate_loader=lambda _service_id, _release: [
            IntentCandidate(
                intent_id="it_api_timeout",
                display_name="API Timeout",
                domain="IT",
                route_key="it.api_timeout.manual_lookup",
                include_keywords=("api", "timeout"),
            )
        ],
        semantic_search=lambda _query, _candidates, _release: {
            "it_api_timeout": SemanticMatch(positive_scores=[0.92], negative_scores=[]),
        },
        composer=DecisionComposer(ThresholdConfig(preset="balanced")),
    )

    result = engine.route(
        RouteInput(
            query="api timeout issue",
            service_id="svc-a",
            route_scope=RouteScope(allowed_intents=[], allowed_route_keys=[]),
            release=ActiveReleaseContext(release_version="rel-1"),
        )
    )

    assert result.decision == Decision.confident
    assert result.intent_id == "it_api_timeout"
    assert result.route_key == "it.api_timeout.manual_lookup"


def _restricted_scope() -> RouteScope:
    return RouteScope(
        allowed_intents=["it_password_reset"],
        allowed_route_keys=["it.password_reset.self_service"],
    )


@dataclass(frozen=True)
class _AllowAllRiskPolicy:
    def evaluate(self, _query: str) -> RiskEvaluation:
        return RiskEvaluation(matched=False)
