# CI Verification

## Scope

GitHub CI verifies the baseline checks that can run without closed-network dependencies:

- Ruff linting with `uv run ruff check .`
- mypy type checking with `uv run mypy src tests`
- Alembic migration application with `uv run alembic upgrade head`
- Process-level pilot e2e smoke against a background Uvicorn API, using the `balanced` CSV gate
- pytest against PostgreSQL with pgvector using `uv run pytest -q`
- Runtime Compose configuration validation with `docker compose --profile runtime config`

## Out of Scope

The Sprint 4 CI baseline intentionally does not verify:

- The real BGE-M3 embedding model
- Closed-network secret manager integration
- The real Dify UI

CI uses `EMBEDDING_PROVIDER=fake` and local CI-only key material so no production secret is required.

## Local Reproduction

Run the same verification path locally before relying on GitHub CI:

```bash
set -euo pipefail

docker compose up -d postgres
export DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing
export TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing
export ADMIN_BOOTSTRAP_TOKEN=ci-admin-token
export ALLOWED_RUNTIME_ENVIRONMENTS=dev,qa,prod
export RAW_TEXT_KEK_ID=ci-kek-001
export RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
export RAW_TEXT_LEGACY_KEKS_JSON="{}"
export API_KEY_SECRET_KEK_ID=ci-api-key-secret-kek-001
export API_KEY_SECRET_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
export API_KEY_SECRET_LEGACY_KEKS_JSON="{}"
export EMBEDDING_PROVIDER=fake

uv run alembic upgrade head
uv run ruff check .
uv run mypy src tests

mkdir -p var/logs
uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000 > var/logs/api.log 2>&1 &
echo $! > var/logs/api.pid
trap 'kill "$(cat var/logs/api.pid)" 2>/dev/null || true' EXIT
ready=0
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/readyz; then
    ready=1
    break
  fi
  sleep 1
done
if [ "${ready}" -ne 1 ]; then
  cat var/logs/api.log
  exit 1
fi
SERVICE_ID="it-helpdesk-local-$(date +%s)"
uv run python scripts/run_pilot_e2e_smoke.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token "${ADMIN_BOOTSTRAP_TOKEN}" \
  --service-id "${SERVICE_ID}" \
  --environment dev \
  --state-path "var/pilot/${SERVICE_ID}.state.secret.json" \
  --csv-tier standard \
  --required-preset balanced \
  --out-dir "var/evidence/${SERVICE_ID}/e2e"
kill "$(cat var/logs/api.pid)" 2>/dev/null || true
trap - EXIT

uv run pytest -q
docker compose --profile runtime config
```

## Branch Protection

After Sprint 4, require the `CI / verify` check before merging into `main`.
Use `docs/ops/branch-protection.md` for the GitHub UI, GitHub CLI/API,
temporary bypass approval, and branch protection rollback procedure.
Use `docs/ops/branch-protection-evidence-template.md` to record the rule
snapshot, required check verification, artifact review, rollback or temporary
bypass record, and final branch protection state.

If the implementer does not have repository admin permission, create an
operator-not-permitted evidence request using
`docs/ops/branch-protection-evidence-template.md`.
operator-not-permitted does not satisfy pilot go/no-go.
An authorized operator must attach main-protection.json or explicitly approve a
blocked Conditional Go with owner and deadline.

## Artifact Policy

CI uploads non-secret pilot e2e evidence for 14 days, including the smoke evidence
index, threshold comparison reports, readiness reports, and `api.log`.

CI does not upload generated state secret files. The secret-bearing state remains
under `var/pilot/*.secret.json`, and artifact upload paths must not include
`var/pilot` or `*.secret.json`.

## Pilot Smoke Triage

If the pilot e2e smoke fails while unit tests pass, inspect:

- `pilot-e2e-smoke-index.md`
- The threshold comparison Markdown linked from the index
- `api.log`
