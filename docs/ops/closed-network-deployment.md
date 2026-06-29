# Closed-Network Deployment Runbook

This runbook is the Compose-based pilot deployment path for `INTENT_ROUTING_ENVIRONMENT=pilot`.
Use `docs/ops/intent-routing-local-runbook.md` for developer-local fake-embedding runs.
After the image, model, environment file, migration, and API are ready, use
`docs/ops/pilot-rehearsal.md` as the top-level Sprint 5 execution path before
Dify handoff. The lower-level commands in this runbook remain diagnostic steps
for isolating deployment, BGE-M3, readiness, or evidence failures.
Use `docs/ops/bge-m3-evidence-template.md` as the release-ticket record for the
closed-network BGE package, benchmark, rehearsal, offline runtime, and pilot
go/no-go decision.

## 1. Build Image

Build the runtime image on an approved build host:

```bash
docker compose --profile runtime build
```

The image installs the application with `uv sync --locked --extra embedding --no-dev`.
It must not download BGE-M3 model files during image build, application startup, or runtime.

## 2. Offline Transfer

Export the image for transfer into the closed network:

```bash
docker save intent-routing:local -o intent-routing-pilot-image.tar
sha256sum intent-routing-pilot-image.tar
```

Import it on the target host:

```bash
docker load -i intent-routing-pilot-image.tar
```

Record the image checksum in the pilot evidence package.

## 3. Model Path

Mount the approved local BGE-M3 model at:

```text
/models/bge-m3
```

The Compose runtime profile mounts `/models/bge-m3:/models/bge-m3:ro`.
The application must use `BGE_M3_MODEL_PATH=/models/bge-m3` and CPU-only inference.
Use `docs/ops/bge-m3-closed-network.md` for model package import, checksum evidence, and benchmark interpretation.

Before enabling any Dify traffic, run the package preflight and benchmark from that
runbook. `scripts/verify_bge_m3_package.py` must produce package checksum evidence
before `scripts/benchmark_bge_m3.py` is accepted as runtime readiness evidence.
Record the results in `docs/ops/bge-m3-evidence-template.md` with status
`measured-pass`, `measured-fail`, or `pending-host-access`. `pending-host-access`
is allowed only when the closed-network host is unavailable; it blocks actual
pilot go/no-go and is not acceptable for Dify traffic approval.

## 4. Environment File

Copy `.env.closed-network.example` to a real secret-managed environment file:

```bash
cp .env.closed-network.example .env.closed-network
chmod 600 .env.closed-network
```

Set:

```dotenv
INTENT_ROUTING_ENVIRONMENT=pilot
EMBEDDING_PROVIDER=bge-m3
BGE_M3_MODEL_PATH=/models/bge-m3
BGE_M3_BATCH_SIZE=16
BGE_M3_MAX_TOKENS=256
```

Replace `ADMIN_BOOTSTRAP_TOKEN`, `RAW_TEXT_KEK_ID`, `RAW_TEXT_KEK_BASE64`, and the database password with values from the approved internal secret manager.
Do not use `.env.closed-network.example` as the real secret file.

`BGE_M3_MAX_TOKENS=256` is the operator default. The runtime source of truth is the service row `max_input_tokens`; the Sprint 2 pilot seed creates services with `max_input_tokens=256`.

## 5. Start Database, Migration, And API

Point Compose at the real environment file:

```bash
export INTENT_ROUTING_ENV_FILE=.env.closed-network
docker compose --profile runtime up -d postgres migrate api
```

The startup order is:

1. `postgres` starts and passes `pg_isready`.
2. `migrate` runs `uv run alembic upgrade head`.
3. `api` starts only after migration completes.

## 6. Liveness And Readiness

Check liveness:

```bash
curl -s http://127.0.0.1:8000/healthz
```

Check readiness:

```bash
curl -s http://127.0.0.1:8000/readyz
```

`/healthz` verifies the process is up. `/readyz` verifies the dependencies required before Dify traffic is allowed.

## 7. Pilot Rehearsal Evidence

Run the Sprint 5 rehearsal wrapper after the API is ready. Closed-network mode
captures BGE-M3 package preflight, BGE-M3 benchmark, Sprint 4 e2e smoke, Dify
smoke matrix, CSV baseline comparison, ops evidence, and the rehearsal secret
scan in one manifest:

```bash
export SERVICE_ID=it-helpdesk-pilot-$(date +%Y%m%d%H%M%S)
export STATE_PATH="var/pilot/${SERVICE_ID}.state.secret.json"

uv run python scripts/run_pilot_rehearsal.py \
  --mode closed-network \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --environment pilot \
  --state-path ${STATE_PATH} \
  --csv-tier standard \
  --required-preset balanced \
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --bge-model-path /models/bge-m3 \
  --bge-expected-sha256 ${BGE_M3_MODEL_SHA256} \
  --run-bge-benchmark \
  --out-dir var/evidence/${SERVICE_ID}/rehearsal
```

The `standard` CSV tier is the 50-row pilot default. Use `minimum` for 30 rows, `high-confidence` for 100 rows, or `custom --csv <path>` for an operator-supplied dataset.
Do not connect Dify HTTP Request nodes to this API until the rehearsal manifest,
package preflight, benchmark, readiness, smoke, baseline, ops evidence, and
secret scan are all PASS in the pilot evidence package.

Closed-network measurement is documented for operators to execute on the target
host. Expected results are:

- `bge-m3-package.json exists`
- `bge-m3-package.md exists`
- `bge-m3-benchmark.json exists`
- `bge-m3-benchmark.md exists`
- `pilot-rehearsal-manifest.json final_status is PASS`
- `secret_scan.passed is true`
- `dimension is 1024`
- `batch_size is 16`
- `max_tokens is 256`

If the host is unavailable, fill `pending-host-access` in
`docs/ops/bge-m3-evidence-template.md`, attach that record to the release ticket,
and keep pilot go/no-go blocked. Pilot handoff requires `measured-pass` for
package preflight, benchmark, closed-network rehearsal, and secret scan.

## 8. Diagnostic Operations Evidence And Security Lifecycle

If the rehearsal `ops-evidence-export` step fails, run the operations evidence
export directly as a diagnostic:

```bash
uv run python scripts/export_ops_evidence.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --out-dir var/evidence/${SERVICE_ID}/ops \
  --window-hours 24 \
  --actor-id ops-evidence \
  --environment pilot
```

Expected outputs are `ops-evidence.json` and `ops-evidence.md`.
Use `docs/ops/security-lifecycle.md` for KEK rewrap, runtime raw-query retention, rollback, and secret leak checks.

## 9. Rollback

Rollback is image plus release oriented:

1. Restore the prior approved image.
2. Start the prior image with the same secret-managed environment file.
3. Activate the prior known-good `release_version` through the admin release rollback flow.

Do not mutate intent catalog data, policy versions, or test run rows as part of a rollback. Catalog and policy changes should remain auditable through release history.
