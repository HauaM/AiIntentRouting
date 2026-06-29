from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_branch_protection_docs_include_required_check_operations() -> None:
    branch_protection = ROOT / "docs/ops/branch-protection.md"

    assert branch_protection.exists()
    branch_protection_text = branch_protection.read_text(encoding="utf-8")

    for expected in (
        "CI / verify",
        "Require status checks to pass before merging",
        "Require branches to be up to date before merging",
        "main",
        "pull_request",
        "workflow_dispatch",
        "pilot-e2e-evidence",
        "14 days",
        "branch protection rollback",
        "temporary bypass approval",
        "no .secret.json",
    ):
        assert expected in branch_protection_text


def test_branch_protection_docs_linked_from_ops_and_readme() -> None:
    for path in (
        ROOT / "docs/ops/ci-verification.md",
        ROOT / "README.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "docs/ops/branch-protection.md" in text
