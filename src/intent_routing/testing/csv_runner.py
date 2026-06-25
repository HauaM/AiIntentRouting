from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from io import StringIO
from typing import Any
from uuid import uuid4

from intent_routing.api.runtime import _candidates_from_snapshot, _off_topic_policy
from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.domain.enums import Decision, ThresholdPreset
from intent_routing.embedding.provider import get_embedding_provider
from intent_routing.policy.risk import RiskPolicy
from intent_routing.routing.engine import (
    ActiveReleaseContext,
    IntentCandidate,
    RouteInput,
    RouteScope,
    RoutingEngine,
    SemanticMatch,
)
from intent_routing.routing.scoring import RoutingDecisionResult
from intent_routing.security.pii import mask_pii
from intent_routing.testing.gate import GateInput, GateResult, evaluate_gate

CSV_COLUMNS = ["case_id", "query", "expected_intent", "case_type", "memo"]
EXPECTED_DECISIONS = {
    "positive": "confident",
    "confusing": "confident",
    "risk": "risk",
    "off_topic": "off_topic",
    "fallback": "fallback",
}


class CsvValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ParsedTestCase:
    case_id: str
    query: str
    expected_intent: str | None
    case_type: str
    memo: str
    expected_decision: str


@dataclass(frozen=True, slots=True)
class CsvTestRunSummary:
    test_run_id: str
    test_dataset_version: str
    threshold_preset: str
    threshold_value: float
    pass_rate: float
    review_rate: float
    risk_pass_rate: float
    gate_passed: bool
    block_reasons: list[str]
    recommendations: list[str]


def parse_test_cases_csv(csv_text: str) -> list[ParsedTestCase]:
    reader = csv.DictReader(StringIO(csv_text))
    if reader.fieldnames != CSV_COLUMNS:
        raise CsvValidationError("CSV columns must be exactly: " + ", ".join(CSV_COLUMNS))

    cases: list[ParsedTestCase] = []
    seen_case_ids: set[str] = set()
    for row_number, row in enumerate(reader, start=2):
        case_id = _required(row.get("case_id"), row_number, "case_id")
        query = _required(row.get("query"), row_number, "query")
        raw_expected_intent = (row.get("expected_intent") or "").strip()
        case_type = (row.get("case_type") or "").strip()
        memo = row.get("memo") or ""

        if case_id in seen_case_ids:
            raise CsvValidationError(f"row {row_number}: duplicate case_id {case_id}")
        seen_case_ids.add(case_id)

        expected_decision = EXPECTED_DECISIONS.get(case_type)
        if expected_decision is None:
            raise CsvValidationError(f"row {row_number}: unknown case_type {case_type}")

        if case_type in {"positive", "confusing"}:
            if not raw_expected_intent:
                raise CsvValidationError(f"row {row_number}: expected_intent is required")
            expected_intent: str | None = raw_expected_intent
        else:
            if raw_expected_intent:
                raise CsvValidationError(f"row {row_number}: expected_intent must be empty")
            expected_intent = None

        cases.append(
            ParsedTestCase(
                case_id=case_id,
                query=query,
                expected_intent=expected_intent,
                case_type=case_type,
                memo=memo,
                expected_decision=expected_decision,
            )
        )

    return cases


def run_csv_tests(
    repository: IntentRoutingRepository,
    *,
    service: models.Service,
    policy_version: models.PolicyVersion,
    catalog_version: models.IntentCatalogVersion,
    threshold_preset: ThresholdPreset,
    source_filename: str,
    csv_text: str,
    created_by: str,
) -> CsvTestRunSummary:
    cases = parse_test_cases_csv(csv_text)
    now = datetime.now(UTC)
    threshold_value = threshold_preset.threshold
    dataset_version = _version_id("tds", service.service_id, now)
    test_run_id = _version_id("tr", service.service_id, now)
    release = _release_context(
        service=service,
        policy_version=policy_version,
        catalog_version=catalog_version,
        threshold_preset=threshold_preset,
        threshold_value=threshold_value,
    )
    engine = _routing_engine(
        repository,
        service_id=service.service_id,
        risk_enabled=_risk_enabled(policy_version.risk_policy),
    )

    result_values = [
        _run_case(engine, release=release, service_id=service.service_id, test_case=test_case)
        for test_case in cases
    ]
    gate = _gate_from_results(result_values)

    repository.create_test_dataset(
        {
            "test_dataset_version": dataset_version,
            "service_id": service.service_id,
            "source_filename": source_filename,
            "content_sha256": hashlib.sha256(csv_text.encode("utf-8")).hexdigest(),
            "created_by": created_by,
            "created_at": now,
        },
        [
            {
                "case_id": test_case.case_id,
                "query": test_case.query,
                "expected_intent": test_case.expected_intent,
                "case_type": test_case.case_type,
                "memo": test_case.memo,
            }
            for test_case in cases
        ],
    )
    repository.create_test_run_with_results(
        {
            "test_run_id": test_run_id,
            "service_id": service.service_id,
            "test_dataset_version": dataset_version,
            "policy_version": policy_version.policy_version,
            "intent_catalog_version": catalog_version.intent_catalog_version,
            "threshold_preset": threshold_preset.value,
            "threshold_value": Decimal(str(threshold_value)),
            "pass_rate": Decimal(str(gate.pass_rate)),
            "review_rate": Decimal(str(gate.review_rate)),
            "risk_pass_rate": Decimal(str(gate.risk_pass_rate)),
            "gate_passed": gate.gate_passed,
            "created_by": created_by,
            "created_at": now,
        },
        result_values,
    )
    return _summary(
        test_run_id=test_run_id,
        test_dataset_version=dataset_version,
        threshold_preset=threshold_preset.value,
        threshold_value=threshold_value,
        gate=gate,
    )


def summarize_test_run(
    test_run: models.TestRun,
    results: Iterable[models.TestResult],
) -> CsvTestRunSummary:
    result_values = [
        {
            "case_type": result.case_type,
            "result": result.result,
        }
        for result in results
    ]
    gate = _gate_from_results(result_values)
    return _summary(
        test_run_id=test_run.test_run_id,
        test_dataset_version=test_run.test_dataset_version,
        threshold_preset=test_run.threshold_preset,
        threshold_value=float(test_run.threshold_value),
        gate=gate,
    )


def _required(value: str | None, row_number: int, column: str) -> str:
    stripped = (value or "").strip()
    if not stripped:
        raise CsvValidationError(f"row {row_number}: {column} is required")
    return stripped


def _version_id(prefix: str, service_id: str, now: datetime) -> str:
    return f"{prefix}-{service_id}-{now:%Y%m%d}-{uuid4().hex[:8]}"


def _release_context(
    *,
    service: models.Service,
    policy_version: models.PolicyVersion,
    catalog_version: models.IntentCatalogVersion,
    threshold_preset: ThresholdPreset,
    threshold_value: float,
) -> ActiveReleaseContext:
    return ActiveReleaseContext(
        release_version=f"test-run-{uuid4().hex[:8]}",
        service_id=service.service_id,
        policy_version=policy_version.policy_version,
        intent_catalog_version=catalog_version.intent_catalog_version,
        threshold_preset=threshold_preset.value,
        threshold=threshold_value,
        threshold_value=threshold_value,
        clarify_margin=float(policy_version.clarify_margin),
        min_candidate_score=float(policy_version.min_candidate_score),
        fallback_score=float(policy_version.fallback_score),
        policy={
            "risk_policy": policy_version.risk_policy,
            "off_topic_policy": policy_version.off_topic_policy,
        },
        catalog_snapshot=catalog_version.snapshot,
        max_input_tokens=service.max_input_tokens,
        off_topic_policy=_off_topic_policy(policy_version.off_topic_policy),
    )


def _routing_engine(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    risk_enabled: bool,
) -> RoutingEngine:
    return RoutingEngine(
        risk_policy=RiskPolicy(enabled=risk_enabled),
        candidate_loader=lambda _service_id, release: _load_candidates(release),
        semantic_search=lambda query, candidates, release: _semantic_matches(
            repository,
            service_id=service_id,
            query=query,
            candidates=candidates,
            release=release,
        ),
    )


def _risk_enabled(config: Mapping[str, object]) -> bool:
    return bool(config.get("enabled", True))


def _load_candidates(release: ActiveReleaseContext) -> list[IntentCandidate]:
    if not isinstance(release.catalog_snapshot, Mapping):
        return []
    return _candidates_from_snapshot(release.catalog_snapshot.get("intents"))


def _semantic_matches(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    query: str,
    candidates: list[IntentCandidate],
    release: ActiveReleaseContext,
) -> Mapping[str, SemanticMatch]:
    if not candidates:
        return {}

    provider = get_embedding_provider()
    embeddings = provider.embed_texts([query], max_tokens=release.max_input_tokens)
    if len(embeddings) != 1 or len(embeddings[0]) != provider.dimension:
        raise ValueError("embedding provider returned an invalid result")

    example_rows = repository.search_approved_examples_by_embedding(
        service_id,
        embeddings[0],
        limit=max(8, len(candidates) * 4),
    )
    candidate_ids = {candidate.intent_id for candidate in candidates}
    grouped: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {"positive": [], "negative": []}
    )
    for row in example_rows:
        if row.intent_id not in candidate_ids or row.example_type not in {"positive", "negative"}:
            continue
        grouped[row.intent_id][row.example_type].append(row.similarity)

    return {
        intent_id: SemanticMatch(
            positive_scores=payload["positive"],
            negative_scores=payload["negative"],
        )
        for intent_id, payload in grouped.items()
    }


def _run_case(
    engine: RoutingEngine,
    *,
    release: ActiveReleaseContext,
    service_id: str,
    test_case: ParsedTestCase,
) -> dict[str, Any]:
    decision = engine.route(
        RouteInput(
            query=test_case.query,
            service_id=service_id,
            route_scope=RouteScope(allowed_intents=[], allowed_route_keys=[]),
            release=release,
        )
    )
    result, reason = _compare_result(test_case, decision)
    return {
        "case_id": test_case.case_id,
        "query_masked": mask_pii(test_case.query),
        "case_type": test_case.case_type,
        "expected_decision": test_case.expected_decision,
        "expected_intent": test_case.expected_intent,
        "actual_decision": decision.decision.value,
        "actual_intent": decision.intent_id,
        "actual_route_key": decision.route_key,
        "confidence": (
            Decimal(str(decision.confidence)) if decision.confidence is not None else None
        ),
        "result": result,
        "reason": reason,
    }


def _compare_result(
    test_case: ParsedTestCase,
    decision: RoutingDecisionResult,
) -> tuple[str, str]:
    actual_decision = decision.decision.value
    if actual_decision == Decision.clarify.value:
        return "REVIEW", "requires human inspection"

    decision_matches = actual_decision == test_case.expected_decision
    intent_matches = (
        test_case.expected_intent is None
        or decision.intent_id == test_case.expected_intent
    )
    if decision_matches and intent_matches:
        if test_case.expected_intent is None:
            return "PASS", "matched expected decision"
        return "PASS", "matched expected decision and intent"

    if not decision_matches:
        return "FAIL", "actual decision did not match expected decision"
    return "FAIL", "actual intent did not match expected intent"


def _gate_from_results(results: Iterable[Mapping[str, object]]) -> GateResult:
    result_list = list(results)
    passed = sum(1 for result in result_list if result["result"] == "PASS")
    review = sum(1 for result in result_list if result["result"] == "REVIEW")
    risk_results = [result for result in result_list if result["case_type"] == "risk"]
    risk_passed = sum(1 for result in risk_results if result["result"] == "PASS")
    return evaluate_gate(
        GateInput(
            total=len(result_list),
            passed=passed,
            review=review,
            risk_total=len(risk_results),
            risk_passed=risk_passed,
        )
    )


def _summary(
    *,
    test_run_id: str,
    test_dataset_version: str,
    threshold_preset: str,
    threshold_value: float,
    gate: GateResult,
) -> CsvTestRunSummary:
    return CsvTestRunSummary(
        test_run_id=test_run_id,
        test_dataset_version=test_dataset_version,
        threshold_preset=threshold_preset,
        threshold_value=threshold_value,
        pass_rate=gate.pass_rate,
        review_rate=gate.review_rate,
        risk_pass_rate=gate.risk_pass_rate,
        gate_passed=gate.gate_passed,
        block_reasons=gate.block_reasons,
        recommendations=gate.recommendations,
    )
