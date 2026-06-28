# BGE-M3 Closed-Network Runbook

This runbook defines the pilot operating contract for switching from fake embeddings
to CPU-only BGE-M3 in a closed network.

## Model Import Package

The approved model package should contain:

- BGE-M3 model files copied from the approved internal artifact source.
- A package or directory SHA-256 checksum.
- The source approval record and import date.
- The target runtime path, normally `/models/bge-m3`.

Do not download model files during image build, application startup, benchmark runs,
or runtime request handling. The model must already exist on the closed-network host.

## Runtime Path Contract

Set these variables in the real secret-managed environment file:

```dotenv
EMBEDDING_PROVIDER=bge-m3
BGE_M3_MODEL_PATH=/models/bge-m3
BGE_M3_MODEL_SHA256=<approved-checksum-or-empty-if-recorded-externally>
BGE_M3_BATCH_SIZE=16
BGE_M3_MAX_TOKENS=256
```

`BGE_M3_MODEL_PATH` must point to an existing local directory mounted read-only into
the API container. The Compose runtime profile mounts:

```text
/models/bge-m3:/models/bge-m3:ro
```

The application provider forces Hugging Face offline flags and uses CPU mode. Missing
optional dependencies or missing model files must fail clearly during benchmark or first
embedding use, before pilot traffic is approved.

## Pilot Token Length

The pilot default max length is 256 tokens.

- Operator env default: `BGE_M3_MAX_TOKENS=256`.
- Runtime source of truth: `services.max_input_tokens`.
- Sprint 2 pilot seed default: `max_input_tokens=256`.

Benchmark evidence should show `max_tokens: 256`.

## Benchmark Command

Run the benchmark after the model path is mounted and before Dify traffic is enabled:

```bash
EMBEDDING_PROVIDER=bge-m3 \
BGE_M3_MODEL_PATH=/models/bge-m3 \
BGE_M3_BATCH_SIZE=16 \
uv run python scripts/benchmark_bge_m3.py \
  --model-path /models/bge-m3 \
  --csv docs/pilot/it-helpdesk-pilot-cases.csv \
  --max-tokens 256 \
  --repeats 3 \
  --out-dir var/benchmarks
```

The script writes:

```text
var/benchmarks/bge-m3-benchmark.json
var/benchmarks/bge-m3-benchmark.md
```

Attach both files to the pilot handoff evidence package.

## Evidence Interpretation

The benchmark report must show:

- `model_version`: `emb-bge-m3-local` or checksum-derived `emb-bge-m3-<sha>`.
- `dimension`: `1024`.
- `batch_size`: normally `16`.
- `max_tokens`: `256`.
- `query_count`: number of masked CSV queries.
- `latency_ms.p50` and `latency_ms.p95`: CPU-only embedding latency for the test host.
- `max_rss_mb`: process memory high-water mark during the benchmark run.

The benchmark is a readiness and sizing signal, not a formal production SLO. If p95
latency or memory is unacceptable for the pilot host, reduce `BGE_M3_BATCH_SIZE`, rerun
the benchmark, and attach the before/after reports.

## Failure Handling

- Missing model path: mount the approved model directory and rerun.
- Missing `FlagEmbedding` or model runtime dependencies: rebuild the image with the
  `embedding` optional dependency group and rerun.
- Wrong dimension: reject the model package and re-import the approved BGE-M3 artifact.
- Network download attempt: fail the readiness review. Runtime must operate offline.
