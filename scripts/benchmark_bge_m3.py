from __future__ import annotations

import argparse
import csv
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from intent_routing.embedding.diagnostics import (
    render_benchmark_json,
    render_benchmark_markdown,
    run_embedding_benchmark,
)
from intent_routing.embedding.provider import (
    clear_embedding_provider_cache,
    get_embedding_provider,
)
from intent_routing.security.pii import mask_pii

DEFAULT_JSON_REPORT = "bge-m3-benchmark.json"
DEFAULT_MARKDOWN_REPORT = "bge-m3-benchmark.md"


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    result = benchmark_bge_m3(
        model_path=Path(args.model_path),
        csv_path=Path(args.csv),
        max_tokens=args.max_tokens,
        repeats=args.repeats,
        out_dir=Path(args.out_dir),
        batch_size=args.batch_size,
    )
    print(result["json_path"])
    print(result["markdown_path"])


def benchmark_bge_m3(
    *,
    model_path: Path,
    csv_path: Path,
    max_tokens: int,
    repeats: int,
    out_dir: Path,
    batch_size: int,
) -> dict[str, Any]:
    resolved_model_path = model_path.expanduser().resolve()
    if not resolved_model_path.exists():
        raise ValueError(
            "BGE_M3_MODEL_PATH must point to an existing local BGE-M3 model path."
        )

    _configure_bge_env(
        model_path=resolved_model_path,
        max_tokens=max_tokens,
        batch_size=batch_size,
    )
    clear_embedding_provider_cache()
    provider = get_embedding_provider()
    queries = _load_masked_queries(csv_path)
    provider.embed_texts(queries, max_tokens=max_tokens)
    result = run_embedding_benchmark(
        provider,
        queries,
        max_tokens=max_tokens,
        repeats=repeats,
        batch_size=batch_size,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / DEFAULT_JSON_REPORT
    markdown_path = out_dir / DEFAULT_MARKDOWN_REPORT
    json_path.write_text(render_benchmark_json(result), encoding="utf-8")
    markdown_path.write_text(render_benchmark_markdown(result), encoding="utf-8")
    return {
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
        "model_version": result.model_version,
        "dimension": result.dimension,
        "query_count": result.query_count,
    }


def _configure_bge_env(
    *,
    model_path: Path,
    max_tokens: int,
    batch_size: int,
) -> None:
    os.environ["EMBEDDING_PROVIDER"] = "bge-m3"
    os.environ["BGE_M3_MODEL_PATH"] = str(model_path)
    os.environ["BGE_M3_MAX_TOKENS"] = str(max_tokens)
    os.environ["BGE_M3_BATCH_SIZE"] = str(batch_size)


def _load_masked_queries(csv_path: Path) -> list[str]:
    with csv_path.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None or "query" not in reader.fieldnames:
            raise ValueError("benchmark CSV must include a query column.")
        queries = [
            mask_pii((row.get("query") or "").strip())
            for row in reader
            if (row.get("query") or "").strip()
        ]
    if not queries:
        raise ValueError("benchmark CSV must include at least one query.")
    return queries


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark local CPU-only BGE-M3 embedding readiness."
    )
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--batch-size", type=int, default=16)
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
