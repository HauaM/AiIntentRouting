from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "docs/pilot/csv-baseline-refresh-policy.md"


def test_csv_baseline_refresh_policy_documents_required_contract() -> None:
    text = POLICY.read_text(encoding="utf-8")

    for expected in (
        "docs/pilot/csv-baseline-refresh-policy.md",
        "it-helpdesk-pilot-baseline.json",
        "standard 50-row",
        "balanced",
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
    ):
        assert expected in text
