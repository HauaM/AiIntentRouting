# Closed-Network Deployment Runbook

This runbook is the Compose-based pilot deployment path for `INTENT_ROUTING_ENVIRONMENT=pilot`.
Use `docs/ops/intent-routing-local-runbook.md` for developer-local fake-embedding runs.

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

## 7. Pilot Seed And Evidence

Run the pilot readiness automation after the API is ready:

```bash
export SERVICE_ID=it-helpdesk-pilot-$(date +%Y%m%d%H%M%S)
export STATE_PATH="var/pilot/${SERVICE_ID}.state.secret.json"

uv run python scripts/run_pilot_readiness.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --environment pilot \
  --state-path ${STATE_PATH} \
  --csv-tier standard \
  --out-dir var/evidence/${SERVICE_ID}
```

The `standard` CSV tier is the 50-row pilot default. Use `minimum` for 30 rows, `high-confidence` for 100 rows, or `custom --csv <path>` for an operator-supplied dataset.

## 8. Operations Evidence And Security Lifecycle

After readiness evidence, export the operations evidence package:

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
