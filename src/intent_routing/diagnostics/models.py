from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CatalogVersionDiagnosticStats:
    intent_catalog_version: str
    display_version: str | None
    status: str
    reproducibility_status: str
    intent_count: int
    example_count: int
    embedding_count: int
    test_run_model_version: str | None
    test_run_vector_index_version: str | None
    ready_vector_index_version: str | None = None
    ready_vector_index_model_version: str | None = None


@dataclass(frozen=True, slots=True)
class DiagnosticIssue:
    code: str
    severity: str
    evidence: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TestRunDiagnostics:
    primary_issue: DiagnosticIssue | None
    issues: list[DiagnosticIssue]
    catalog_version: CatalogVersionDiagnosticStats
    result_counts: dict[str, int]
    actual_decision_counts: dict[str, int]

    @property
    def issue_codes(self) -> list[str]:
        return [issue.code for issue in self.issues]
