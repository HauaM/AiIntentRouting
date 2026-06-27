from __future__ import annotations

from collections.abc import Mapping
from typing import Any

PRESET_ORDER = ("strict", "balanced", "exploratory")


def render_threshold_report(service_id: str, runs: Mapping[str, Mapping[str, Any]]) -> str:
    lines = [
        f"# CSV Gate Threshold Comparison: {service_id}",
        "",
        "| preset | threshold | pass_rate | review_rate | risk_pass_rate | gate | test_run_id |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]

    findings: list[str] = []
    for preset in PRESET_ORDER:
        run = runs.get(preset)
        if run is None:
            continue
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

    lines.extend(["", "## Findings"])
    if findings:
        lines.extend(findings)
    else:
        lines.append("- All presets passed without recommendations.")
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
