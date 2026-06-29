from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

PRESET_ORDER = ("strict", "balanced", "exploratory")


def render_threshold_report(
    service_id: str,
    runs: Mapping[str, Mapping[str, Any]],
    *,
    results_by_preset: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    required_gate: Mapping[str, Any] | None = None,
) -> str:
    missing_presets = [preset for preset in PRESET_ORDER if preset not in runs]
    if missing_presets:
        raise ValueError(
            "Missing threshold preset results for comparison: "
            + ", ".join(missing_presets)
        )

    lines = [
        f"# CSV Gate Threshold Comparison: {service_id}",
        "",
        "| preset | threshold | pass_rate | review_rate | risk_pass_rate | gate | test_run_id |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]

    findings: list[str] = []
    for preset in PRESET_ORDER:
        run = runs[preset]
        row = (
            "| {preset} | {threshold} | {pass_rate} | {review_rate} | "
            "{risk_pass_rate} | {gate} | {test_run_id} |"
        )
        lines.append(
            row.format(
                preset=preset,
                threshold=f"{float(run['threshold_value']):.2f}",
                pass_rate=_format_percent(run["pass_rate"]),
                review_rate=_format_percent(run["review_rate"]),
                risk_pass_rate=_format_percent(run["risk_pass_rate"]),
                gate="PASS" if bool(run["gate_passed"]) else "FAIL",
                test_run_id=run["test_run_id"],
            )
        )
        findings.extend(_collect_findings(preset, run))

    if required_gate is not None:
        lines.extend(_render_required_gate(required_gate))

    lines.extend(["", "## Findings"])
    if findings:
        lines.extend(findings)
    else:
        lines.append("- All presets passed without recommendations.")
    if results_by_preset is not None:
        lines.extend(_render_case_result_sections(results_by_preset))
    lines.append("")
    return "\n".join(lines)


def _collect_findings(preset: str, run: Mapping[str, Any]) -> list[str]:
    findings: list[str] = []
    for block_reason in run.get("block_reasons", []):
        findings.append(f"- `{preset}` block: {block_reason}")
    for recommendation in run.get("recommendations", []):
        findings.append(f"- `{preset}` recommendation: {recommendation}")
    return findings


def _format_percent(value: Any) -> str:
    return f"{float(value) * 100:.1f}%"


def _render_required_gate(required_gate: Mapping[str, Any]) -> list[str]:
    lines = [
        "",
        "## Required Gate",
        "",
        f"- Required preset: `{required_gate['required_preset']}`",
        f"- Gate: `{'PASS' if bool(required_gate['passed']) else 'FAIL'}`",
        f"- Pass rate: `{_format_percent(required_gate['pass_rate'])}`",
        f"- Risk pass rate: `{_format_percent(required_gate['risk_pass_rate'])}`",
    ]
    for block_reason in required_gate.get("block_reasons", []):
        lines.append(f"- Block: {block_reason}")
    return lines


def _render_case_result_sections(
    results_by_preset: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[str]:
    lines: list[str] = ["", "## Case Result Counts", ""]
    lines.extend(
        [
            "| preset | case_type | PASS | REVIEW | FAIL | total |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for preset in PRESET_ORDER:
        case_type_counts: dict[str, Counter[str]] = defaultdict(Counter)
        for row in results_by_preset.get(preset, []):
            case_type_counts[str(row.get("case_type", ""))][str(row.get("result", ""))] += 1
        for case_type in sorted(case_type_counts):
            counts = case_type_counts[case_type]
            total = counts["PASS"] + counts["REVIEW"] + counts["FAIL"]
            lines.append(
                f"| {preset} | {case_type} | {counts['PASS']} | {counts['REVIEW']} | "
                f"{counts['FAIL']} | {total} |"
            )

    failed_cases = _case_rows_with_result(results_by_preset, "FAIL")
    lines.extend(
        [
            "",
            "## Failed Cases",
            "",
            (
                "| preset | case_id | case_type | expected_decision | actual_decision | "
                "expected_intent | actual_intent | confidence | reason |"
            ),
            "| --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
        ]
    )
    if failed_cases:
        lines.extend(_format_case_row(row) for row in failed_cases)
    else:
        lines.append("| - | - | - | - | - | - | - | - | No failed cases. |")

    review_cases = _case_rows_with_result(results_by_preset, "REVIEW")
    lines.extend(
        [
            "",
            "## Review Cases",
            "",
            (
                "| preset | case_id | case_type | expected_decision | actual_decision | "
                "expected_intent | actual_intent | confidence | reason |"
            ),
            "| --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
        ]
    )
    if review_cases:
        lines.extend(_format_case_row(row) for row in review_cases)
    else:
        lines.append("| - | - | - | - | - | - | - | - | No review cases. |")
    return lines


def _case_rows_with_result(
    results_by_preset: Mapping[str, Sequence[Mapping[str, Any]]],
    result: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for preset in PRESET_ORDER:
        for row in results_by_preset.get(preset, []):
            if row.get("result") == result:
                rows.append({"preset": preset, **dict(row)})
    return rows


def _format_case_row(row: Mapping[str, Any]) -> str:
    return (
        f"| {_cell(row.get('preset'))} | {_cell(row.get('case_id'))} | "
        f"{_cell(row.get('case_type'))} | {_cell(row.get('expected_decision'))} | "
        f"{_cell(row.get('actual_decision'))} | {_cell(row.get('expected_intent'))} | "
        f"{_cell(row.get('actual_intent'))} | {_format_optional_percent(row.get('confidence'))} | "
        f"{_cell(row.get('reason'))} |"
    )


def _cell(value: Any) -> str:
    return "" if value is None else str(value)


def _format_optional_percent(value: Any) -> str:
    if value is None:
        return ""
    return _format_percent(value)
