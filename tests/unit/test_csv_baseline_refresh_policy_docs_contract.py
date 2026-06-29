from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "docs/pilot/csv-baseline-refresh-policy.md"
README = ROOT / "docs/pilot/README.md"
PILOT_REHEARSAL = ROOT / "docs/ops/pilot-rehearsal.md"


def _bash_block_after_heading(text: str, heading: str) -> str:
    section = text.split(heading, maxsplit=1)[1]
    after_fence = section.split("```bash\n", maxsplit=1)[1]
    return after_fence.split("\n```", maxsplit=1)[0]


def test_csv_baseline_refresh_policy_documents_required_contract() -> None:
    text = POLICY.read_text(encoding="utf-8")

    for expected in (
        "docs/pilot/csv-baseline-refresh-policy.md",
        "The current checked-in baseline is docs/pilot/it-helpdesk-pilot-baseline.json.",
        "It freezes the standard 50-row CSV for the balanced preset.",
        "it-helpdesk-pilot-baseline.json",
        "standard 50-row",
        "balanced",
        "allowed_new_failures remains 0.",
        "allowed_new_reviews remains 0.",
        "allowed_new_failures: 0",
        "allowed_new_reviews: 0",
        "Do not refresh the baseline merely to make a failing rehearsal pass.",
        "CSV diff",
        "catalog diff",
        "threshold policy diff",
        "approval ID",
        "risk_pass_rate",
        "compare_csv_baseline.py freeze",
        "compare_csv_baseline.py compare",
        "no raw query text",
        "Baseline JSON must not contain raw query text or secret-bearing fields.",
    ):
        assert expected in text


def test_csv_baseline_refresh_policy_pins_freeze_command_block() -> None:
    text = POLICY.read_text(encoding="utf-8")
    freeze_block = _bash_block_after_heading(text, "## Freeze Command")

    for expected in (
        "uv run python scripts/compare_csv_baseline.py freeze",
        "--threshold-report var/evidence/${SERVICE_ID}/rehearsal/e2e/${SERVICE_ID}-threshold-comparison.json",
        "--csv docs/pilot/it-helpdesk-pilot-cases.csv",
        "--preset balanced",
        "--baseline-id it-helpdesk-pilot-standard-YYYYMMDD",
        "--out docs/pilot/it-helpdesk-pilot-baseline.json",
    ):
        assert expected in freeze_block


def test_csv_baseline_refresh_policy_pins_compare_command_block() -> None:
    text = POLICY.read_text(encoding="utf-8")
    compare_block = _bash_block_after_heading(text, "## Compare Command")

    for expected in (
        "uv run python scripts/compare_csv_baseline.py compare",
        "--threshold-report var/evidence/${SERVICE_ID}/rehearsal/e2e/${SERVICE_ID}-threshold-comparison.json",
        "--baseline docs/pilot/it-helpdesk-pilot-baseline.json",
        "--csv docs/pilot/it-helpdesk-pilot-cases.csv",
        "--out-dir var/evidence/${SERVICE_ID}/rehearsal/csv-baseline",
    ):
        assert expected in compare_block


def test_pilot_readme_declares_policy_source_of_truth_for_regression_gate() -> None:
    text = README.read_text(encoding="utf-8")

    assert (
        "docs/pilot/csv-baseline-refresh-policy.md"
    ) in text
    assert (
        "is the source of truth for "
        "the CSV Baseline Regression Gate"
    ) in text


def test_pilot_rehearsal_runbook_links_csv_baseline_refresh_policy() -> None:
    text = PILOT_REHEARSAL.read_text(encoding="utf-8")

    assert "docs/pilot/csv-baseline-refresh-policy.md" in text
