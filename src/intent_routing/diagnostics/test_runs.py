from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from intent_routing.diagnostics.models import (
    CatalogVersionDiagnosticStats,
    DiagnosticIssue,
    TestRunDiagnostics,
)
from intent_routing.testing.csv_runner import CsvTestRunSummary

ISSUE_CODE_PRIORITY = {
    "catalog_version_not_active": 0,
    "catalog_version_not_reproducible": 1,
    "catalog_version_has_no_intents": 2,
    "catalog_version_has_no_examples": 3,
    "test_run_vector_index_not_ready": 4,
    "catalog_version_has_no_ready_vector_index": 5,
    "catalog_version_has_no_embeddings": 6,
    "risk_case_failed": 10,
    "fallback_failures_dominant": 20,
    "intent_mismatch_exists": 21,
    "pass_rate_below_gate": 30,
    "review_rate_above_guidance": 31,
}


def diagnose_test_run(
    summary: CsvTestRunSummary,
    catalog_stats: CatalogVersionDiagnosticStats,
    results: Sequence[Mapping[str, Any]],
) -> TestRunDiagnostics:
    result_counts = Counter(str(row.get("result", "")).upper() for row in results)
    actual_decision_counts = Counter(str(row.get("actual_decision", "")) for row in results)
    failed_rows = [row for row in results if str(row.get("result", "")).upper() == "FAIL"]
    fallback_fail_count = sum(
        1 for row in failed_rows if row.get("actual_decision") == "fallback"
    )
    intent_mismatch_count = sum(
        1
        for row in failed_rows
        if row.get("reason") == "actual intent did not match expected intent"
    )

    issues: list[DiagnosticIssue] = []
    if catalog_stats.status != "active":
        issues.append(
            DiagnosticIssue(
                code="catalog_version_not_active",
                severity="blocker",
                evidence={"status": catalog_stats.status},
            )
        )
    if catalog_stats.reproducibility_status != "complete":
        issues.append(
            DiagnosticIssue(
                code="catalog_version_not_reproducible",
                severity="blocker",
                evidence={"reproducibility_status": catalog_stats.reproducibility_status},
            )
        )
    if catalog_stats.intent_count == 0:
        issues.append(
            DiagnosticIssue(
                code="catalog_version_has_no_intents",
                severity="blocker",
                evidence={"intent_count": 0},
            )
        )
    elif catalog_stats.example_count == 0:
        issues.append(
            DiagnosticIssue(
                code="catalog_version_has_no_examples",
                severity="blocker",
                evidence={"example_count": 0},
            )
        )
    elif catalog_stats.ready_vector_index_version is None:
        issues.append(
            DiagnosticIssue(
                code="catalog_version_has_no_ready_vector_index",
                severity="blocker",
                evidence={"ready_vector_index_version": None},
            )
        )
    elif (
        catalog_stats.test_run_vector_index_version is not None
        and catalog_stats.test_run_vector_index_ready is False
    ):
        issues.append(
            DiagnosticIssue(
                code="test_run_vector_index_not_ready",
                severity="blocker",
                evidence={
                    "test_run_vector_index_version": (
                        catalog_stats.test_run_vector_index_version
                    ),
                    "test_run_vector_index_status": (
                        catalog_stats.test_run_vector_index_status
                    ),
                },
            )
        )
    elif catalog_stats.embedding_count == 0:
        issues.append(
            DiagnosticIssue(
                code="catalog_version_has_no_embeddings",
                severity="blocker",
                evidence={"embedding_count": 0},
            )
        )

    if summary.risk_pass_rate < 1.0:
        issues.append(
            DiagnosticIssue(
                code="risk_case_failed",
                severity="blocker",
                evidence={"risk_pass_rate": summary.risk_pass_rate},
            )
        )
    if failed_rows and fallback_fail_count / len(failed_rows) >= 0.5:
        issues.append(
            DiagnosticIssue(
                code="fallback_failures_dominant",
                severity="warning",
                evidence={
                    "fallback_fail_count": fallback_fail_count,
                    "failed_count": len(failed_rows),
                },
            )
        )
    if intent_mismatch_count:
        issues.append(
            DiagnosticIssue(
                code="intent_mismatch_exists",
                severity="warning",
                evidence={"intent_mismatch_count": intent_mismatch_count},
            )
        )
    if any(reason.startswith("pass rate below ") for reason in summary.block_reasons):
        issues.append(
            DiagnosticIssue(
                code="pass_rate_below_gate",
                severity="blocker",
                evidence={
                    "pass_rate": summary.pass_rate,
                    "block_reasons": summary.block_reasons,
                },
            )
        )
    if any(
        recommendation.startswith("review rate above ")
        for recommendation in summary.recommendations
    ):
        issues.append(
            DiagnosticIssue(
                code="review_rate_above_guidance",
                severity="recommendation",
                evidence={
                    "review_rate": summary.review_rate,
                    "recommendations": summary.recommendations,
                },
            )
        )

    issues.sort(key=lambda issue: ISSUE_CODE_PRIORITY[issue.code])

    return TestRunDiagnostics(
        primary_issue=issues[0] if issues else None,
        issues=issues,
        catalog_version=catalog_stats,
        result_counts=dict(result_counts),
        actual_decision_counts=dict(actual_decision_counts),
    )
