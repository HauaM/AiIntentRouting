from __future__ import annotations

import builtins
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest


def test_argument_parsing_does_not_import_flag_embedding(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    benchmark_module = _import_benchmark_module()
    _fail_on_flag_embedding_import(monkeypatch)

    args = benchmark_module._parse_args(
        [
            "--model-path",
            str(tmp_path / "model"),
            "--csv",
            str(tmp_path / "cases.csv"),
            "--max-tokens",
            "256",
            "--repeats",
            "3",
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )

    assert args.max_tokens == 256
    assert "FlagEmbedding" not in sys.modules


def test_benchmark_writes_json_and_markdown_reports(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    benchmark_module = _import_benchmark_module()
    model_path = tmp_path / "bge-m3"
    model_path.mkdir()
    csv_path = _write_cases_csv(tmp_path)
    out_dir = tmp_path / "benchmarks"
    provider = _RecordingProvider()

    monkeypatch.setattr(benchmark_module, "get_embedding_provider", lambda: provider)
    monkeypatch.setattr(benchmark_module, "clear_embedding_provider_cache", lambda: None)

    result = benchmark_module.benchmark_bge_m3(
        model_path=model_path,
        csv_path=csv_path,
        max_tokens=256,
        repeats=2,
        out_dir=out_dir,
        batch_size=16,
    )

    json_path = out_dir / "bge-m3-benchmark.json"
    markdown_path = out_dir / "bge-m3-benchmark.md"
    report = json.loads(json_path.read_text(encoding="utf-8"))

    assert result["json_path"] == str(json_path)
    assert result["markdown_path"] == str(markdown_path)
    assert report["model_version"] == "emb-bge-m3-test"
    assert report["dimension"] == 1024
    assert report["batch_size"] == 16
    assert report["max_tokens"] == 256
    assert report["query_count"] == 2
    assert report["repeats"] == 2
    assert report["latency_ms"]["p50"] >= 0
    assert report["latency_ms"]["p95"] >= 0
    assert report["elapsed_ms"] >= 0
    assert report["max_rss_mb"] > 0
    assert "BGE-M3 Benchmark" in markdown_path.read_text(encoding="utf-8")
    assert set(provider.max_tokens_seen) == {256}
    assert any("010-****-5678" in text for text in provider.texts_seen)
    assert all("1234-5678" not in text for text in provider.texts_seen)


def test_benchmark_rejects_missing_local_model_path(tmp_path: Path) -> None:
    benchmark_module = _import_benchmark_module()
    csv_path = _write_cases_csv(tmp_path)

    with pytest.raises(ValueError, match="BGE_M3_MODEL_PATH.*existing local"):
        benchmark_module.benchmark_bge_m3(
            model_path=tmp_path / "missing-model",
            csv_path=csv_path,
            max_tokens=256,
            repeats=1,
            out_dir=tmp_path / "benchmarks",
            batch_size=16,
        )


def test_diagnostics_rejects_non_1024_dimension() -> None:
    diagnostics_module = _import_diagnostics_module()
    provider = _RecordingProvider(dimension=768)

    with pytest.raises(ValueError, match="1024"):
        diagnostics_module.run_embedding_benchmark(
            provider,
            ["VPN 접속이 되지 않습니다"],
            max_tokens=256,
            repeats=1,
            batch_size=16,
        )


class _RecordingProvider:
    model_version = "emb-bge-m3-test"

    def __init__(self, *, dimension: int = 1024) -> None:
        self.dimension = dimension
        self.max_tokens_seen: list[int] = []
        self.texts_seen: list[str] = []

    def embed_texts(self, texts: list[str], *, max_tokens: int) -> list[list[float]]:
        self.max_tokens_seen.append(max_tokens)
        self.texts_seen.extend(texts)
        return [[1.0] + [0.0] * (self.dimension - 1) for _ in texts]


def _write_cases_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "cases.csv"
    csv_path.write_text(
        "\n".join(
            [
                "case_id,query,expected_intent,case_type,memo",
                "case-001,VPN 접속이 되지 않습니다,,fallback,benchmark case",
                "case-002,제 전화번호는 010-1234-5678 입니다,,fallback,masking case",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return csv_path


def _fail_on_flag_embedding_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def guarded_import(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> ModuleType:
        if name == "FlagEmbedding":
            raise AssertionError("FlagEmbedding must not import during argument parsing")
        return real_import(name, globals, locals, fromlist, level)

    sys.modules.pop("FlagEmbedding", None)
    monkeypatch.setattr(builtins, "__import__", guarded_import)


def _import_benchmark_module() -> ModuleType:
    import scripts.benchmark_bge_m3 as benchmark_module

    return benchmark_module


def _import_diagnostics_module() -> ModuleType:
    import intent_routing.embedding.diagnostics as diagnostics_module

    return diagnostics_module
