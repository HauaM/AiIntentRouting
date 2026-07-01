from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _compact(text: str) -> str:
    return " ".join(text.split())


def test_branch_protection_evidence_template_includes_required_terms() -> None:
    template = ROOT / "docs/ops/branch-protection-evidence-template.md"

    assert template.exists()
    template_text = template.read_text(encoding="utf-8")
    compact_text = _compact(template_text)

    for expected in (
        "docs/ops/branch-protection-evidence-template.md",
        "main",
        "CI / verify",
        "Require status checks to pass before merging",
        "Require branches to be up to date before merging",
        "strict: true",
        'checks: [{"context": "verify", "app_id": 15368}]',
        "workflow_dispatch",
        "temporary bypass approval",
        "rollback approval ID",
        "exact commit SHA",
        "pilot-e2e-evidence",
        "14 days",
        "no .secret.json",
        "final branch protection state",
        "authorized operator capture",
        "operator-not-permitted evidence request",
        "main-protection.json",
        "branch protection capture verified",
        "restore or confirm final branch protection state",
    ):
        assert expected in template_text

    for expected in (
        "apply evidence",
        "rollback evidence",
    ):
        assert expected in compact_text


def test_branch_protection_runbook_includes_evidence_closure_terms() -> None:
    runbook = ROOT / "docs/ops/branch-protection.md"

    assert runbook.exists()
    runbook_text = runbook.read_text(encoding="utf-8")
    compact_text = _compact(runbook_text)

    for expected in (
        "authorized operator capture",
        "operator-not-permitted evidence request",
        "main-protection.json",
        "branch protection capture verified",
        "restore or confirm final branch protection state",
    ):
        assert expected in runbook_text

    for expected in (
        "apply evidence",
        "rollback evidence",
    ):
        assert expected in compact_text


def test_branch_protection_evidence_template_is_linked_from_ops_docs() -> None:
    for path in (
        ROOT / "docs/ops/branch-protection.md",
        ROOT / "docs/ops/ci-verification.md",
    ):
        text = path.read_text(encoding="utf-8")
        compact_text = _compact(text)

        assert "docs/ops/branch-protection-evidence-template.md" in text
        assert "operator-not-permitted" in text
        assert "does not satisfy pilot go/no-go" in compact_text


def test_branch_protection_capture_verification_uses_structured_json_check() -> None:
    for path in (
        ROOT / "docs/ops/branch-protection-evidence-template.md",
        ROOT / "docs/ops/branch-protection.md",
    ):
        text = path.read_text(encoding="utf-8")

        for expected in (
            "json.load",
            "required_status_checks",
            "contexts",
            "checks",
            "CI / verify",
            "verify",
            "enforce_admins",
            "enabled",
        ):
            assert expected in text
