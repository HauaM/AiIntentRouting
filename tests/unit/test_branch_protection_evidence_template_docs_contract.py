from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_branch_protection_evidence_template_includes_required_terms() -> None:
    template = ROOT / "docs/ops/branch-protection-evidence-template.md"

    assert template.exists()
    template_text = template.read_text(encoding="utf-8")

    for expected in (
        "docs/ops/branch-protection-evidence-template.md",
        "main",
        "CI / verify",
        "Require status checks to pass before merging",
        "Require branches to be up to date before merging",
        "strict: true",
        'contexts: ["CI / verify"]',
        "workflow_dispatch",
        "temporary bypass approval",
        "rollback approval ID",
        "exact commit SHA",
        "pilot-e2e-evidence",
        "14 days",
        "no .secret.json",
        "final branch protection state",
    ):
        assert expected in template_text
