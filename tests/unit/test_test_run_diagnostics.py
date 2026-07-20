from __future__ import annotations

from typing import Any

import pytest

from intent_routing.diagnostics.models import CatalogVersionDiagnosticStats
from intent_routing.diagnostics.test_runs import diagnose_test_run
from intent_routing.testing.csv_runner import CsvTestRunSummary


def _summary(**overrides: object) -> CsvTestRunSummary:
    values: dict[str, Any] = {
        "test_run_id": "tr-test",
        "test_dataset_version": "tds-test",
        "model_version": "fake-embedding-v1",
        "vector_index_version": "vec-cat-test-fake-embedding-v1-001",
        "threshold_preset": "exploratory",
        "threshold_value": 0.6,
        "pass_rate": 0.2,
        "review_rate": 0.0,
        "risk_pass_rate": 0.5,
        "gate_passed": False,
        "block_reasons": ["pass rate below 70%", "risk case failed"],
        "recommendations": [],
    }
    values.update(overrides)
    return CsvTestRunSummary(**values)


def _catalog_stats(**overrides: object) -> CatalogVersionDiagnosticStats:
    values: dict[str, Any] = {
        "intent_catalog_version": "cat-test",
        "display_version": "v1",
        "status": "active",
        "reproducibility_status": "complete",
        "intent_count": 5,
        "example_count": 20,
        "embedding_count": 20,
        "test_run_model_version": "fake-embedding-v1",
        "test_run_vector_index_version": "vec-cat-test-fake-embedding-v1-001",
        "ready_vector_index_version": "vec-cat-test-fake-embedding-v1-001",
        "ready_vector_index_model_version": "fake-embedding-v1",
        "test_run_vector_index_ready": True,
        "test_run_vector_index_status": "ready",
    }
    values.update(overrides)
    return CatalogVersionDiagnosticStats(**values)


def test_inactive_catalog_version_is_primary_blocker() -> None:
    diagnostics = diagnose_test_run(
        _summary(),
        _catalog_stats(status="inactive"),
        [],
    )

    assert diagnostics.primary_issue is not None
    assert diagnostics.primary_issue.code == "catalog_version_not_active"
    assert diagnostics.primary_issue.severity == "blocker"
    assert diagnostics.primary_issue.evidence["status"] == "inactive"


def test_non_reproducible_catalog_version_blocks_before_result_patterns() -> None:
    diagnostics = diagnose_test_run(
        _summary(),
        _catalog_stats(reproducibility_status="metadata_only", embedding_count=0),
        [
            {
                "case_type": "positive",
                "expected_decision": "confident",
                "expected_intent": "program_supported_question",
                "actual_decision": "fallback",
                "actual_intent": None,
                "result": "FAIL",
                "reason": "actual decision did not match expected decision",
            }
        ],
    )

    assert diagnostics.primary_issue is not None
    assert diagnostics.primary_issue.code == "catalog_version_not_reproducible"
    assert diagnostics.issue_codes[0] == "catalog_version_not_reproducible"


def test_empty_catalog_version_intents_are_reported() -> None:
    diagnostics = diagnose_test_run(
        _summary(),
        _catalog_stats(intent_count=0, example_count=0, embedding_count=0),
        [],
    )

    assert diagnostics.primary_issue is not None
    assert diagnostics.primary_issue.code == "catalog_version_has_no_intents"
    assert diagnostics.primary_issue.evidence["intent_count"] == 0


def test_missing_version_embeddings_are_reported() -> None:
    diagnostics = diagnose_test_run(
        _summary(),
        _catalog_stats(intent_count=5, example_count=20, embedding_count=0),
        [],
    )

    assert diagnostics.primary_issue is not None
    assert diagnostics.primary_issue.code == "catalog_version_has_no_embeddings"
    assert diagnostics.primary_issue.evidence["embedding_count"] == 0


def test_missing_ready_vector_index_is_reported_before_embeddings() -> None:
    diagnostics = diagnose_test_run(
        _summary(vector_index_version=None),
        _catalog_stats(
            intent_count=5,
            example_count=20,
            embedding_count=0,
            test_run_vector_index_version=None,
            ready_vector_index_version=None,
            ready_vector_index_model_version=None,
            test_run_vector_index_ready=None,
            test_run_vector_index_status=None,
        ),
        [],
    )

    assert diagnostics.primary_issue is not None
    assert diagnostics.primary_issue.code == "catalog_version_has_no_ready_vector_index"


@pytest.mark.parametrize(
    ("selected_vector_index_version", "selected_vector_index_status"),
    [("vec-building", "building"), ("vec-missing", None)],
)
def test_missing_ready_vector_index_precedes_selected_index_not_ready(
    selected_vector_index_version: str,
    selected_vector_index_status: str | None,
) -> None:
    diagnostics = diagnose_test_run(
        _summary(vector_index_version=selected_vector_index_version),
        _catalog_stats(
            test_run_vector_index_version=selected_vector_index_version,
            ready_vector_index_version=None,
            ready_vector_index_model_version=None,
            test_run_vector_index_ready=False,
            test_run_vector_index_status=selected_vector_index_status,
        ),
        [],
    )

    assert diagnostics.primary_issue is not None
    assert diagnostics.primary_issue.code == "catalog_version_has_no_ready_vector_index"


def test_test_run_vector_index_not_ready_is_reported() -> None:
    diagnostics = diagnose_test_run(
        _summary(vector_index_version="vec-old"),
        _catalog_stats(
            test_run_vector_index_version="vec-old",
            ready_vector_index_version="vec-current",
            test_run_vector_index_ready=False,
            test_run_vector_index_status=None,
        ),
        [],
    )

    assert diagnostics.primary_issue is not None
    assert diagnostics.primary_issue.code == "test_run_vector_index_not_ready"
    assert diagnostics.primary_issue.evidence == {
        "test_run_vector_index_version": "vec-old",
        "test_run_vector_index_status": None,
    }


def test_test_run_vector_index_not_ready_includes_known_status() -> None:
    diagnostics = diagnose_test_run(
        _summary(vector_index_version="vec-building"),
        _catalog_stats(
            test_run_vector_index_version="vec-building",
            test_run_vector_index_ready=False,
            test_run_vector_index_status="building",
        ),
        [],
    )

    assert diagnostics.primary_issue is not None
    assert diagnostics.primary_issue.code == "test_run_vector_index_not_ready"
    assert diagnostics.primary_issue.evidence == {
        "test_run_vector_index_version": "vec-building",
        "test_run_vector_index_status": "building",
    }


def test_fallback_dominance_precedes_pass_rate_gate_for_single_failure() -> None:
    diagnostics = diagnose_test_run(
        _summary(pass_rate=0.4, risk_pass_rate=1.0, block_reasons=["pass rate below 70%"]),
        _catalog_stats(),
        [
            {
                "case_type": "positive",
                "expected_decision": "confident",
                "expected_intent": "program_supported_question",
                "actual_decision": "fallback",
                "actual_intent": None,
                "result": "FAIL",
                "reason": "actual decision did not match expected decision",
            }
        ],
    )

    assert diagnostics.primary_issue is not None
    assert diagnostics.primary_issue.code == "fallback_failures_dominant"
    assert diagnostics.issue_codes == [
        "fallback_failures_dominant",
        "pass_rate_below_gate",
    ]


def test_fallback_dominant_when_catalog_is_ready() -> None:
    diagnostics = diagnose_test_run(
        _summary(pass_rate=0.4, risk_pass_rate=1.0, block_reasons=["pass rate below 70%"]),
        _catalog_stats(),
        [
            {
                "case_type": "positive",
                "expected_decision": "confident",
                "expected_intent": "program_supported_question",
                "actual_decision": "fallback",
                "actual_intent": None,
                "result": "FAIL",
                "reason": "actual decision did not match expected decision",
            },
            {
                "case_type": "positive",
                "expected_decision": "confident",
                "expected_intent": "owner_contact_lookup",
                "actual_decision": "fallback",
                "actual_intent": None,
                "result": "FAIL",
                "reason": "actual decision did not match expected decision",
            },
        ],
    )

    assert diagnostics.primary_issue is not None
    assert diagnostics.primary_issue.code == "fallback_failures_dominant"
    assert diagnostics.primary_issue.evidence["fallback_fail_count"] == 2
    assert diagnostics.issue_codes == [
        "fallback_failures_dominant",
        "pass_rate_below_gate",
    ]


def test_intent_mismatch_when_decision_matches_but_intent_differs() -> None:
    diagnostics = diagnose_test_run(
        _summary(pass_rate=0.5, risk_pass_rate=1.0, block_reasons=["pass rate below 70%"]),
        _catalog_stats(),
        [
            {
                "case_type": "positive",
                "expected_decision": "confident",
                "expected_intent": "program_supported_question",
                "actual_decision": "confident",
                "actual_intent": "owner_contact_lookup",
                "result": "FAIL",
                "reason": "actual intent did not match expected intent",
            }
        ],
    )

    assert diagnostics.primary_issue is not None
    assert diagnostics.primary_issue.code == "intent_mismatch_exists"
