from pathlib import Path

from intent_routing.ops.rehearsal import (
    SECRET_MARKERS,
    SecretScanResult,
    scan_evidence_directory,
)

ROOT = Path(__file__).resolve().parents[2]


def _compact(text: str) -> str:
    return " ".join(text.split())


def test_bge_m3_evidence_template_documents_closed_network_contract() -> None:
    text = (ROOT / "docs/ops/bge-m3-evidence-template.md").read_text(
        encoding="utf-8"
    )
    compact_text = _compact(text)

    for expected in (
        "docs/ops/bge-m3-evidence-template.md",
        "verify_bge_m3_package.py",
        "benchmark_bge_m3.py",
        "run_pilot_rehearsal.py",
        "--mode closed-network",
        "--run-bge-benchmark",
        "BGE_M3_MODEL_PATH",
        "BGE_M3_MODEL_SHA256",
        "/models/bge-m3",
        "dimension: 1024",
        "batch_size: 16",
        "max_tokens: 256",
        "latency_ms.p50",
        "latency_ms.p95",
        "max_rss_mb",
        "offline_required",
        "measured-pass",
        "measured-fail",
        "pending-host-access",
        "pending-host-access exception approval",
        "exception approval ID",
        "exception owner",
        "expires before pilot traffic",
        "next measurement date",
        "pending-host-access blocks pilot go/no-go",
    ):
        assert expected in text

    for expected in (
        (
            "pending-host-access requires an exception approval ID, an owner, "
            "and a next measurement date."
        ),
        (
            "pending-host-access may support documentation closure, but it "
            "blocks closed-network pilot traffic."
        ),
        (
            "Conditional Go with pending-host-access must state that Dify or "
            "closed-network traffic remains blocked until measured-pass "
            "evidence is attached."
        ),
        (
            "Decision impact: Conditional Go cannot send closed-network pilot "
            "traffic until measured-pass is attached."
        ),
    ):
        assert expected in compact_text


def test_bge_m3_evidence_template_is_secret_scan_safe(tmp_path: Path) -> None:
    doc = ROOT / "docs/ops/bge-m3-evidence-template.md"
    text = doc.read_text(encoding="utf-8")

    for marker in SECRET_MARKERS:
        assert marker not in text

    result = scan_evidence_directory(tmp_path, extra_paths=[doc])

    assert result == SecretScanResult(passed=True, findings=[])


def test_bge_m3_evidence_template_is_linked_from_closed_network_runbooks() -> None:
    for path in (
        ROOT / "docs/ops/bge-m3-closed-network.md",
        ROOT / "docs/ops/closed-network-deployment.md",
        ROOT / "docs/ops/pilot-rehearsal.md",
    ):
        text = path.read_text(encoding="utf-8")

        assert "docs/ops/bge-m3-evidence-template.md" in text
        assert "pending-host-access" in text
        assert "pilot go/no-go" in text
        assert "blocked" in text
