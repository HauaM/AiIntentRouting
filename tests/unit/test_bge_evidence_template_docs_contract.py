from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_bge_m3_evidence_template_documents_closed_network_contract() -> None:
    text = (ROOT / "docs/ops/bge-m3-evidence-template.md").read_text(
        encoding="utf-8"
    )

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
        "pending-host-access blocks pilot go/no-go",
    ):
        assert expected in text
