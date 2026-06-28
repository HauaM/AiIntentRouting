"""Embedding benchmark diagnostics for closed-network model readiness."""

from __future__ import annotations

import json
import resource
import statistics
import time
from dataclasses import asdict, dataclass

from intent_routing.embedding.provider import EmbeddingProvider


@dataclass(frozen=True, slots=True)
class EmbeddingBenchmarkCase:
    query: str


@dataclass(frozen=True, slots=True)
class EmbeddingBenchmarkResult:
    model_version: str
    dimension: int
    batch_size: int
    max_tokens: int
    query_count: int
    repeats: int
    latency_ms: dict[str, float]
    elapsed_ms: float
    max_rss_mb: float


def run_embedding_benchmark(
    provider: EmbeddingProvider,
    texts: list[str],
    *,
    max_tokens: int,
    repeats: int,
    batch_size: int,
) -> EmbeddingBenchmarkResult:
    """Run a small embedding benchmark over masked pilot queries."""
    if provider.dimension != 1024:
        raise ValueError("BGE-M3 dense embedding dimension must be 1024.")
    if max_tokens < 1:
        raise ValueError("max_tokens must be at least 1.")
    if repeats < 1:
        raise ValueError("repeats must be at least 1.")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1.")
    if not texts:
        raise ValueError("benchmark requires at least one query.")

    latencies_ms: list[float] = []
    started = time.perf_counter()
    for _ in range(repeats):
        measurement_started = time.perf_counter()
        embeddings = provider.embed_texts(texts, max_tokens=max_tokens)
        measurement_elapsed = time.perf_counter() - measurement_started
        if len(embeddings) != len(texts):
            raise ValueError("Embedding provider must return one vector per query.")
        latencies_ms.append(measurement_elapsed * 1000)
    elapsed_ms = (time.perf_counter() - started) * 1000

    return EmbeddingBenchmarkResult(
        model_version=provider.model_version,
        dimension=provider.dimension,
        batch_size=batch_size,
        max_tokens=max_tokens,
        query_count=len(texts),
        repeats=repeats,
        latency_ms={
            "min": min(latencies_ms),
            "p50": statistics.median(latencies_ms),
            "p95": _percentile(latencies_ms, 95),
            "max": max(latencies_ms),
        },
        elapsed_ms=elapsed_ms,
        max_rss_mb=_max_rss_mb(),
    )


def render_benchmark_json(result: EmbeddingBenchmarkResult) -> str:
    return json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n"


def render_benchmark_markdown(result: EmbeddingBenchmarkResult) -> str:
    return "\n".join(
        [
            "# BGE-M3 Benchmark",
            "",
            f"- Model version: `{result.model_version}`",
            f"- Dimension: `{result.dimension}`",
            f"- Batch size: `{result.batch_size}`",
            f"- Max tokens: `{result.max_tokens}`",
            f"- Query count: `{result.query_count}`",
            f"- Repeats: `{result.repeats}`",
            f"- p50 latency: `{result.latency_ms['p50']:.2f} ms`",
            f"- p95 latency: `{result.latency_ms['p95']:.2f} ms`",
            f"- Elapsed: `{result.elapsed_ms:.2f} ms`",
            f"- Max RSS: `{result.max_rss_mb:.2f} MB`",
            "",
            "The benchmark must be run with a local model path in closed-network mode.",
            "",
        ]
    )


def _percentile(values: list[float], percentile: int) -> float:
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    rank = (len(sorted_values) - 1) * (percentile / 100)
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    weight = rank - lower_index
    lower = sorted_values[lower_index]
    upper = sorted_values[upper_index]
    return lower + ((upper - lower) * weight)


def _max_rss_mb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return max(rss / 1024, 0.001)
