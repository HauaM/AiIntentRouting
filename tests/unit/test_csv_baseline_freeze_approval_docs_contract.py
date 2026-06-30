from pathlib import Path

from intent_routing.ops.rehearsal import SecretScanResult, scan_evidence_directory

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "docs/pilot/csv-baseline-freeze-approval-template.md"
TEMPLATE_PATH = "docs/pilot/csv-baseline-freeze-approval-template.md"


def test_csv_baseline_freeze_approval_template_contains_required_contract() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    for expected in (
        TEMPLATE_PATH,
        "CSV Baseline Freeze Approval Template",
        "it-helpdesk-pilot-baseline.json",
        "standard 50-row",
        "balanced",
        "allowed_new_failures: 0",
        "allowed_new_reviews: 0",
        "CSV baseline comparison PASS",
        "refresh not approved",
        (
            "Accepted behavior change: none; if behavior changed, stop and "
            "attach a policy-approved refresh approval instead."
        ),
        "approval ID",
        "release owner",
        "QA or security reviewer",
        "no raw query text",
        "no secret-bearing fields",
        "release-ticket.md",
    ):
        assert expected in text

    assert "Behavior change accepted: yes / no" not in text


def test_csv_baseline_freeze_approval_template_is_secret_scan_safe(
    tmp_path: Path,
) -> None:
    result = scan_evidence_directory(tmp_path, extra_paths=[TEMPLATE])

    assert result == SecretScanResult(passed=True, findings=[])


def test_csv_baseline_freeze_template_is_linked_from_required_docs() -> None:
    for path in (
        ROOT / "docs/pilot/csv-baseline-refresh-policy.md",
        ROOT / "docs/pilot/README.md",
        ROOT / "docs/ops/pilot-handoff-release-ticket-template.md",
        ROOT / "docs/ops/pilot-launch-readiness-checklist.md",
    ):
        text = path.read_text(encoding="utf-8")

        assert TEMPLATE_PATH in text
