from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_pilot_rehearsal_runbook_documents_required_concepts() -> None:
    text = (ROOT / "docs/ops/pilot-rehearsal.md").read_text(encoding="utf-8")

    for expected in (
        "run_pilot_rehearsal.py",
        "pilot-rehearsal-manifest.json",
        "pilot-rehearsal-manifest.md",
        "local mode",
        "closed-network mode",
        "verify_bge_m3_package.py",
        "benchmark_bge_m3.py",
        "run_pilot_e2e_smoke.py",
        "run_dify_smoke_matrix.py",
        "compare_csv_baseline.py",
        "export_ops_evidence.py",
        "secret scan",
        "raw query decrypt exception",
        "KEK rewrap dry-run",
        "runtime raw-query retention dry-run",
        "API key rotation overlap",
        "incident fallback",
        "no destructive security operation is executed by the wrapper",
    ):
        assert expected in text


def test_existing_ops_runbooks_link_pilot_rehearsal_as_sprint_5_path() -> None:
    for path in (
        ROOT / "docs/ops/security-operations.md",
        ROOT / "docs/ops/security-lifecycle.md",
        ROOT / "docs/ops/closed-network-deployment.md",
        ROOT / "docs/ops/bge-m3-closed-network.md",
        ROOT / "docs/ops/intent-routing-pilot-runbook.md",
    ):
        text = path.read_text(encoding="utf-8")

        assert "docs/ops/pilot-rehearsal.md" in text
        assert "top-level Sprint 5 execution path" in text
        assert "diagnostic" in text
