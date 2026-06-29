from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast


@dataclass(frozen=True)
class CsvBaselinePolicy:
    baseline_id: str
    csv_path: str
    csv_sha256: str
    required_preset: str
    minimum_pass_rate: float
    required_risk_pass_rate: float
    allowed_new_failures: int
    allowed_new_reviews: int


@dataclass(frozen=True)
class CsvCaseExpectation:
    case_id: str
    preset: str
    expected_result: str
    expected_decision: str | None
    expected_intent: str | None
    expected_route_key: str | None


@dataclass(frozen=True)
class CsvBaselineComparison:
    passed: bool
    block_reasons: list[str]
    new_failures: list[dict[str, str]]
    new_reviews: list[dict[str, str]]
    missing_cases: list[dict[str, str]]
    changed_decisions: list[dict[str, str | None]]
    changed_intents: list[dict[str, str | None]]
    changed_route_keys: list[dict[str, str | None]]


def freeze_baseline(
    threshold_report: Mapping[str, Any],
    csv_path: Path,
    preset: str,
) -> dict[str, Any]:
    run = _required_mapping(_required_mapping(threshold_report, "runs"), preset)
    rows = _required_sequence(_required_mapping(threshold_report, "results"), preset)
    policy = CsvBaselinePolicy(
        baseline_id=f"{threshold_report.get('service_id', 'csv')}-{preset}",
        csv_path=str(csv_path),
        csv_sha256=_sha256_file(csv_path),
        required_preset=preset,
        minimum_pass_rate=float(run.get("pass_rate", 0.0)),
        required_risk_pass_rate=float(run.get("risk_pass_rate", 0.0)),
        allowed_new_failures=0,
        allowed_new_reviews=0,
    )
    cases = [_case_expectation(row, preset) for row in rows]
    cases.sort(key=lambda item: item.case_id)
    return {
        "schema_version": 1,
        "baseline_id": policy.baseline_id,
        "policy": asdict(policy),
        "cases": [asdict(case) for case in cases],
    }


def compare_baseline(
    threshold_report: Mapping[str, Any],
    baseline: Mapping[str, Any],
) -> CsvBaselineComparison:
    policy = _policy_from_baseline(baseline)
    rows = _required_sequence(
        _required_mapping(threshold_report, "results"),
        policy.required_preset,
    )
    current_by_case_id = {str(row.get("case_id")): row for row in rows}
    block_reasons: list[str] = []
    new_failures: list[dict[str, str]] = []
    new_reviews: list[dict[str, str]] = []
    missing_cases: list[dict[str, str]] = []
    changed_decisions: list[dict[str, str | None]] = []
    changed_intents: list[dict[str, str | None]] = []
    changed_route_keys: list[dict[str, str | None]] = []

    run = _required_mapping(
        _required_mapping(threshold_report, "runs"),
        policy.required_preset,
    )
    pass_rate = float(run.get("pass_rate", 0.0))
    risk_pass_rate = float(run.get("risk_pass_rate", 0.0))
    if pass_rate < policy.minimum_pass_rate:
        block_reasons.append(
            _rate_reason(
                policy.required_preset,
                "pass_rate",
                pass_rate,
                policy.minimum_pass_rate,
            )
        )
    if risk_pass_rate < policy.required_risk_pass_rate:
        block_reasons.append(
            _rate_reason(
                policy.required_preset,
                "risk_pass_rate",
                risk_pass_rate,
                policy.required_risk_pass_rate,
            )
        )

    for expectation in _expectations_from_baseline(baseline):
        current = current_by_case_id.get(expectation.case_id)
        if current is None:
            missing_cases.append(
                {"case_id": expectation.case_id, "preset": expectation.preset}
            )
            continue
        actual_result = _optional_string(current.get("result")) or ""
        actual_decision = _optional_string(current.get("actual_decision"))
        actual_intent = _optional_string(current.get("actual_intent"))
        actual_route_key = _optional_string(current.get("actual_route_key"))

        if expectation.expected_result == "PASS" and actual_result == "FAIL":
            new_failures.append(
                _case_result_row(expectation, actual_result=actual_result)
            )
        if expectation.expected_result == "PASS" and actual_result == "REVIEW":
            new_reviews.append(_case_result_row(expectation, actual_result=actual_result))
        if actual_decision != expectation.expected_decision:
            changed_decisions.append(
                _drift_row(
                    expectation,
                    baseline_value=expectation.expected_decision,
                    actual_value=actual_decision,
                )
            )
        if actual_intent != expectation.expected_intent:
            changed_intents.append(
                _drift_row(
                    expectation,
                    baseline_value=expectation.expected_intent,
                    actual_value=actual_intent,
                )
            )
        if actual_route_key != expectation.expected_route_key:
            changed_route_keys.append(
                _drift_row(
                    expectation,
                    baseline_value=expectation.expected_route_key,
                    actual_value=actual_route_key,
                )
            )

    if len(new_failures) > policy.allowed_new_failures:
        block_reasons.append("new FAIL cases above allowance")
    if len(new_reviews) > policy.allowed_new_reviews:
        block_reasons.append("new REVIEW cases above allowance")
    if missing_cases:
        block_reasons.append("missing baseline cases in current report")
    if changed_decisions:
        block_reasons.append("decision drift from baseline")
    if changed_intents:
        block_reasons.append("intent drift from baseline")
    if changed_route_keys:
        block_reasons.append("route_key drift from baseline")

    return CsvBaselineComparison(
        passed=not block_reasons,
        block_reasons=block_reasons,
        new_failures=new_failures,
        new_reviews=new_reviews,
        missing_cases=missing_cases,
        changed_decisions=changed_decisions,
        changed_intents=changed_intents,
        changed_route_keys=changed_route_keys,
    )


def render_baseline_comparison_json(result: CsvBaselineComparison) -> str:
    return json.dumps(asdict(result), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_baseline_comparison_markdown(result: CsvBaselineComparison) -> str:
    lines = [
        "# CSV Baseline Comparison",
        "",
        f"- Status: **{'PASS' if result.passed else 'FAIL'}**",
    ]
    if result.block_reasons:
        lines.extend(["", "## Block Reasons", ""])
        lines.extend(f"- {reason}" for reason in result.block_reasons)
    else:
        lines.extend(["", "No block reasons."])
    lines.extend(
        _render_case_table(
            "New Failures",
            result.new_failures,
            ("preset", "case_id", "expected_result", "actual_result"),
        )
    )
    lines.extend(
        _render_case_table(
            "New Reviews",
            result.new_reviews,
            ("preset", "case_id", "expected_result", "actual_result"),
        )
    )
    lines.extend(
        _render_case_table(
            "Missing Cases",
            result.missing_cases,
            ("preset", "case_id"),
        )
    )
    lines.extend(
        _render_case_table(
            "Changed Decisions",
            result.changed_decisions,
            ("preset", "case_id", "baseline_value", "actual_value"),
        )
    )
    lines.extend(
        _render_case_table(
            "Changed Intents",
            result.changed_intents,
            ("preset", "case_id", "baseline_value", "actual_value"),
        )
    )
    lines.extend(
        _render_case_table(
            "Changed Route Keys",
            result.changed_route_keys,
            ("preset", "case_id", "baseline_value", "actual_value"),
        )
    )
    lines.append("")
    return "\n".join(lines)


def _case_expectation(row: Any, preset: str) -> CsvCaseExpectation:
    if not isinstance(row, Mapping):
        raise ValueError("threshold report result rows must be objects")
    case_id = _optional_string(row.get("case_id"))
    if not case_id:
        raise ValueError("threshold report result row is missing case_id")
    return CsvCaseExpectation(
        case_id=case_id,
        preset=preset,
        expected_result=_optional_string(row.get("result")) or "",
        expected_decision=_optional_string(row.get("actual_decision")),
        expected_intent=_optional_string(row.get("actual_intent")),
        expected_route_key=_optional_string(row.get("actual_route_key")),
    )


def _policy_from_baseline(baseline: Mapping[str, Any]) -> CsvBaselinePolicy:
    policy = _required_mapping(baseline, "policy")
    return CsvBaselinePolicy(
        baseline_id=str(policy["baseline_id"]),
        csv_path=str(policy["csv_path"]),
        csv_sha256=str(policy["csv_sha256"]),
        required_preset=str(policy["required_preset"]),
        minimum_pass_rate=float(policy["minimum_pass_rate"]),
        required_risk_pass_rate=float(policy["required_risk_pass_rate"]),
        allowed_new_failures=int(policy.get("allowed_new_failures", 0)),
        allowed_new_reviews=int(policy.get("allowed_new_reviews", 0)),
    )


def _expectations_from_baseline(
    baseline: Mapping[str, Any],
) -> list[CsvCaseExpectation]:
    cases = _required_sequence(baseline, "cases")
    expectations: list[CsvCaseExpectation] = []
    for case in cases:
        if not isinstance(case, Mapping):
            raise ValueError("baseline cases must be objects")
        expectations.append(
            CsvCaseExpectation(
                case_id=str(case["case_id"]),
                preset=str(case["preset"]),
                expected_result=str(case["expected_result"]),
                expected_decision=_optional_string(case.get("expected_decision")),
                expected_intent=_optional_string(case.get("expected_intent")),
                expected_route_key=_optional_string(case.get("expected_route_key")),
            )
        )
    return expectations


def _case_result_row(
    expectation: CsvCaseExpectation,
    *,
    actual_result: str,
) -> dict[str, str]:
    return {
        "case_id": expectation.case_id,
        "preset": expectation.preset,
        "expected_result": expectation.expected_result,
        "actual_result": actual_result,
    }


def _drift_row(
    expectation: CsvCaseExpectation,
    *,
    baseline_value: str | None,
    actual_value: str | None,
) -> dict[str, str | None]:
    return {
        "case_id": expectation.case_id,
        "preset": expectation.preset,
        "baseline_value": baseline_value,
        "actual_value": actual_value,
    }


def _render_case_table(
    title: str,
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[str],
) -> list[str]:
    lines = ["", f"## {title}", ""]
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join("---" for _ in columns) + " |")
    if rows:
        for row in rows:
            lines.append("| " + " | ".join(_cell(row.get(column)) for column in columns) + " |")
    else:
        lines.append("| " + " | ".join("-" for _ in columns) + " |")
    return lines


def _rate_reason(preset: str, name: str, actual: float, required: float) -> str:
    return (
        f"{preset} {name} {actual * 100:.1f}% below required "
        f"{required * 100:.1f}%"
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_mapping(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = mapping[key]
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be an object")
    return cast(Mapping[str, Any], value)


def _required_sequence(mapping: Mapping[str, Any], key: str) -> Sequence[Any]:
    value = mapping[key]
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    return value


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("|", "\\|")
