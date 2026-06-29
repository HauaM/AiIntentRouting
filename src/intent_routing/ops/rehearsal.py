from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

REDACTED = "REDACTED"
VALID_STATUSES = {"pass", "fail", "skip"}
SECRET_MARKERS = (
    ".secret.json",
    "Authorization: Bearer",
    "Bearer ",
    "RAW_TEXT_KEK_BASE64",
    "RAW_TEXT_LEGACY_KEKS_JSON",
    "api_key=",
    "intent_routing_api_key",
    "query_raw",
    "text_raw",
    "encrypted_dek",
    "ciphertext",
    "irt_live_",
    "irt_secret",
)
@dataclass(frozen=True)
class EvidenceFile:
    path: str
    kind: str
    required: bool
    secret_safe: bool


@dataclass(frozen=True)
class RehearsalStep:
    name: str
    status: str
    required: bool
    summary: str
    evidence_files: list[EvidenceFile]
    error_message: str | None

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"invalid rehearsal step status: {self.status}")


@dataclass(frozen=True)
class SecretScanFinding:
    path: str
    marker: str
    line_number: int


@dataclass(frozen=True)
class SecretScanResult:
    passed: bool
    findings: list[SecretScanFinding]


@dataclass(frozen=True)
class RehearsalManifest:
    service_id: str
    environment: str
    mode: str
    required_preset: str
    started_at: datetime
    completed_at: datetime
    steps: list[RehearsalStep]
    secret_scan: SecretScanResult
    dify_workflow_version_identifier: str | None = None
    dify_ui_evidence_path: str | None = None


def render_rehearsal_json(manifest: RehearsalManifest) -> str:
    payload = _manifest_payload(manifest)
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_rehearsal_markdown(manifest: RehearsalManifest) -> str:
    payload = _manifest_payload(manifest)
    secret_scan = _mapping(payload.get("secret_scan"))
    lines = [
        f"# Pilot Rehearsal Manifest: {payload.get('service_id', 'unknown')}",
        "",
        f"- Environment: `{payload.get('environment', 'unknown')}`",
        f"- Mode: `{payload.get('mode', 'unknown')}`",
        f"- Required preset: `{payload.get('required_preset', 'unknown')}`",
        f"- Started at: `{payload.get('started_at', 'unknown')}`",
        f"- Completed at: `{payload.get('completed_at', 'unknown')}`",
        f"- Final status: **{payload.get('final_status', 'FAIL')}**",
        f"- Secret scan: **{'PASS' if secret_scan.get('passed') else 'FAIL'}**",
    ]
    if payload.get("dify_workflow_version_identifier") or payload.get(
        "dify_ui_evidence_path"
    ):
        lines.extend(
            [
                "",
                "## Dify Dry-Run Metadata",
                "",
                "- Dify workflow version identifier: `{version}`".format(
                    version=payload.get("dify_workflow_version_identifier")
                    or "not provided"
                ),
                "- Dify UI evidence path: `{path}`".format(
                    path=payload.get("dify_ui_evidence_path") or "not provided"
                ),
            ]
        )
    lines.extend(
        [
            "",
            "## Steps",
            "",
            "| step | status | required | summary | error |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for step in payload.get("steps", []):
        if not isinstance(step, Mapping):
            continue
        lines.append(
            "| {name} | {status} | {required} | {summary} | {error} |".format(
                name=step.get("name", "unknown"),
                status=str(step.get("status", "unknown")).upper(),
                required=str(bool(step.get("required"))).lower(),
                summary=step.get("summary", ""),
                error=step.get("error_message") or "",
            )
        )

    lines.extend(["", "## Evidence Files", "", "| step | path | kind | required | secret safe |"])
    lines.append("| --- | --- | --- | --- | --- |")
    for step in payload.get("steps", []):
        if not isinstance(step, Mapping):
            continue
        for evidence_file in step.get("evidence_files", []):
            if not isinstance(evidence_file, Mapping):
                continue
            lines.append(
                "| {step} | `{path}` | {kind} | {required} | {secret_safe} |".format(
                    step=step.get("name", "unknown"),
                    path=evidence_file.get("path", ""),
                    kind=evidence_file.get("kind", ""),
                    required=str(bool(evidence_file.get("required"))).lower(),
                    secret_safe=str(bool(evidence_file.get("secret_safe"))).lower(),
                )
            )

    lines.extend(["", "## Secret Scan Findings", ""])
    findings = secret_scan.get("findings")
    if findings:
        lines.extend(["| path | marker | line |", "| --- | --- | ---: |"])
        for finding in findings:
            if not isinstance(finding, Mapping):
                continue
            lines.append(
                "| `{path}` | `{marker}` | {line} |".format(
                    path=finding.get("path", ""),
                    marker=finding.get("marker", REDACTED),
                    line=finding.get("line_number", 0),
                )
            )
    else:
        lines.append("No findings.")
    lines.append("")
    return "\n".join(lines)


def scan_evidence_directory(
    root: Path, *, extra_paths: Iterable[Path] = ()
) -> SecretScanResult:
    if not root.exists():
        return SecretScanResult(
            passed=False,
            findings=[
                SecretScanFinding(
                    path=str(root),
                    marker="missing_evidence_directory",
                    line_number=0,
                )
            ],
        )
    if not root.is_dir():
        return SecretScanResult(
            passed=False,
            findings=[
                SecretScanFinding(
                    path=str(root),
                    marker="invalid_evidence_directory",
                    line_number=0,
                )
            ],
        )

    findings: list[SecretScanFinding] = []
    scanned_paths: set[Path] = set()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        findings.extend(_scan_evidence_file(root, path, scanned_paths))
    for path in extra_paths:
        if not path.exists():
            findings.append(
                SecretScanFinding(
                    path=str(path),
                    marker="missing_evidence_file",
                    line_number=0,
                )
            )
            continue
        if not path.is_file():
            findings.append(
                SecretScanFinding(
                    path=str(path),
                    marker="invalid_evidence_file",
                    line_number=0,
                )
            )
            continue
        findings.extend(_scan_evidence_file(root, path, scanned_paths))
    return SecretScanResult(passed=not findings, findings=findings)


def manifest_passed(manifest: RehearsalManifest) -> bool:
    if not manifest.secret_scan.passed:
        return False
    return all(step.status == "pass" for step in manifest.steps if step.required)


def _manifest_payload(manifest: RehearsalManifest) -> dict[str, Any]:
    payload = asdict(manifest)
    payload["started_at"] = _format_datetime(manifest.started_at)
    payload["completed_at"] = _format_datetime(manifest.completed_at)
    payload["final_status"] = "PASS" if manifest_passed(manifest) else "FAIL"
    return cast(dict[str, Any], _redact_manifest(payload))


def _format_datetime(value: datetime) -> str:
    return value.isoformat()


def _redact_manifest(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _redact_manifest(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_manifest(item) for item in value]
    if isinstance(value, str) and _contains_secret_marker(value):
        return REDACTED
    return value


def _scan_evidence_file(
    root: Path, path: Path, scanned_paths: set[Path]
) -> list[SecretScanFinding]:
    resolved_path = path.resolve()
    if resolved_path in scanned_paths:
        return []
    scanned_paths.add(resolved_path)
    display_path = _display_path(root, path)
    findings: list[SecretScanFinding] = []
    if ".secret.json" in path.name:
        findings.append(
            SecretScanFinding(path=display_path, marker=".secret.json", line_number=1)
        )
    findings.extend(_scan_file(path, display_path))
    return findings


def _display_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _scan_file(path: Path, display_path: str) -> list[SecretScanFinding]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if _json_evidence_is_redacted(text):
        return []

    findings: list[SecretScanFinding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if _line_is_redacted_evidence_field(line):
            continue
        for marker in _markers_in_text(line):
            findings.append(
                SecretScanFinding(
                    path=display_path,
                    marker=marker,
                    line_number=line_number,
                )
            )
    return findings


def _json_evidence_is_redacted(text: str) -> bool:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return False
    return _json_value_is_secret_safe(parsed)


def _json_value_is_secret_safe(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if _contains_secret_marker(key_text) and item != REDACTED:
                return False
            if not _json_value_is_secret_safe(item):
                return False
        return True
    if isinstance(value, list):
        return all(_json_value_is_secret_safe(item) for item in value)
    if isinstance(value, str):
        return value == REDACTED or not _contains_secret_marker(value)
    return True


def _line_is_redacted_evidence_field(line: str) -> bool:
    normalized = line.strip().strip(",")
    if REDACTED not in normalized or not _contains_secret_marker(normalized):
        return False
    field_name, separator, field_value = normalized.rpartition(":")
    return bool(separator and _contains_secret_marker(field_name)) and (
        field_value.strip(" `\"'") == REDACTED
    )


def _contains_secret_marker(text: str) -> bool:
    return any(marker in text for marker in SECRET_MARKERS)


def _markers_in_text(text: str) -> Iterable[str]:
    return (marker for marker in SECRET_MARKERS if marker in text)


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}
