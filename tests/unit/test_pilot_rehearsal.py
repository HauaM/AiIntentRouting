from __future__ import annotations

import json
from datetime import UTC, datetime

from intent_routing.ops.rehearsal import (
    EvidenceFile,
    RehearsalManifest,
    RehearsalStep,
    SecretScanResult,
    manifest_passed,
    render_rehearsal_json,
    render_rehearsal_markdown,
    scan_evidence_directory,
)


def test_manifest_fails_when_required_step_fails() -> None:
    manifest = _manifest(
        steps=[
            RehearsalStep(
                name="readiness",
                status="fail",
                required=True,
                summary="readyz failed",
                evidence_files=[],
                error_message="503",
            )
        ],
    )

    assert manifest_passed(manifest) is False


def test_manifest_passes_when_required_steps_pass_and_optional_step_skips() -> None:
    manifest = _manifest(
        steps=[
            RehearsalStep(
                name="readiness",
                status="pass",
                required=True,
                summary="ready",
                evidence_files=[
                    EvidenceFile(
                        path="evidence/readiness.json",
                        kind="json",
                        required=True,
                        secret_safe=True,
                    )
                ],
                error_message=None,
            ),
            RehearsalStep(
                name="latency-deep-dive",
                status="skip",
                required=False,
                summary="not needed for this preset",
                evidence_files=[],
                error_message=None,
            ),
        ],
    )

    assert manifest_passed(manifest) is True


def test_manifest_json_and_markdown_are_secret_safe() -> None:
    manifest = _manifest(
        steps=[
            RehearsalStep(
                name="secret-safe-evidence",
                status="pass",
                required=True,
                summary="Authorization: Bearer REDACTED",
                evidence_files=[
                    EvidenceFile(
                        path="evidence/runtime.json",
                        kind="json",
                        required=True,
                        secret_safe=True,
                    )
                ],
                error_message="api_key=REDACTED",
            )
        ],
    )

    rendered_json = render_rehearsal_json(manifest)
    rendered_markdown = render_rehearsal_markdown(manifest)

    decoded = json.loads(rendered_json)
    assert decoded["final_status"] == "PASS"
    assert "api_key=REDACTED" not in rendered_json
    assert "Authorization: Bearer REDACTED" not in rendered_json
    assert "api_key=REDACTED" not in rendered_markdown
    assert "Authorization: Bearer REDACTED" not in rendered_markdown
    assert "REDACTED" in rendered_json
    assert "REDACTED" in rendered_markdown


def test_secret_scan_blocks_secret_state_and_raw_token_markers(tmp_path) -> None:
    (tmp_path / "pilot.state.secret.json").write_text(
        '{"state_path": "var/pilot/prod.state.secret.json"}\n',
        encoding="utf-8",
    )
    (tmp_path / "runtime.md").write_text(
        "\n".join(
            [
                "Authorization: Bearer irt_live_123",
                "RAW_TEXT_KEK_BASE64=abc",
                "RAW_TEXT_LEGACY_KEKS_JSON={}",
                "api_key=abc",
                "intent_routing_api_key",
                "query_raw=hello",
                "text_raw=hello",
                "encrypted_dek=abc",
                "ciphertext=abc",
                "irt_secret_local",
            ]
        ),
        encoding="utf-8",
    )

    result = scan_evidence_directory(tmp_path)

    assert result.passed is False
    markers = {finding.marker for finding in result.findings}
    assert ".secret.json" in markers
    assert "Authorization: Bearer" in markers
    assert "Bearer " in markers
    assert "RAW_TEXT_KEK_BASE64" in markers
    assert "RAW_TEXT_LEGACY_KEKS_JSON" in markers
    assert "api_key=" in markers
    assert "intent_routing_api_key" in markers
    assert "query_raw" in markers
    assert "text_raw" in markers
    assert "encrypted_dek" in markers
    assert "ciphertext" in markers
    assert "irt_live_" in markers
    assert "irt_secret" in markers
    assert all(finding.line_number >= 1 for finding in result.findings)


def test_secret_scan_allows_redacted_evidence_fields(tmp_path) -> None:
    (tmp_path / "evidence.json").write_text(
        json.dumps(
            {
                "authorization": "REDACTED",
                "api_key": "REDACTED",
                "query_raw": "REDACTED",
                "text_raw": "REDACTED",
                "encrypted_dek": "REDACTED",
                "ciphertext": "REDACTED",
                "nested": {
                    "RAW_TEXT_KEK_BASE64": "REDACTED",
                    "RAW_TEXT_LEGACY_KEKS_JSON": "REDACTED",
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "evidence.md").write_text(
        "\n".join(
            [
                "- .secret.json: `REDACTED`",
                "- Authorization: `REDACTED`",
                "- Authorization: Bearer: `REDACTED`",
                "- Bearer token: `REDACTED`",
                "- api_key: `REDACTED`",
                "- api_key=: `REDACTED`",
                "- intent_routing_api_key: `REDACTED`",
                "- query_raw: `REDACTED`",
                "- text_raw: `REDACTED`",
                "- encrypted_dek: `REDACTED`",
                "- ciphertext: `REDACTED`",
                "- irt_live_: `REDACTED`",
                "- irt_secret: `REDACTED`",
                "- RAW_TEXT_KEK_BASE64: `REDACTED`",
                "- RAW_TEXT_LEGACY_KEKS_JSON: `REDACTED`",
            ]
        ),
        encoding="utf-8",
    )

    result = scan_evidence_directory(tmp_path)

    assert result == SecretScanResult(passed=True, findings=[])


def _manifest(steps: list[RehearsalStep]) -> RehearsalManifest:
    return RehearsalManifest(
        service_id="intent-routing",
        environment="pilot",
        mode="dry-run",
        required_preset="balanced",
        started_at=datetime(2026, 6, 29, 1, 2, 3, tzinfo=UTC),
        completed_at=datetime(2026, 6, 29, 1, 3, 4, tzinfo=UTC),
        steps=steps,
        secret_scan=SecretScanResult(passed=True, findings=[]),
    )
