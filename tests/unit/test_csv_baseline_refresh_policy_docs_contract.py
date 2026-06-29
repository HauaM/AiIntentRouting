from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "docs/pilot/csv-baseline-refresh-policy.md"
README = ROOT / "docs/pilot/README.md"


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


def test_pilot_readme_declares_policy_source_of_truth_for_regression_gate() -> None:
    text = README.read_text(encoding="utf-8")

    assert (
        "docs/pilot/csv-baseline-refresh-policy.md is the source of truth for "
        "the CSV Baseline Regression Gate"
    ) in text
