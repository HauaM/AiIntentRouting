# Sprint 2: Closed-Network Pilot Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Intent Routing Service ready for a closed-network pilot handoff by adding deployable packaging, readiness checks, security operations, automated evidence generation, Dify branch templates, BGE-M3 real-model validation, and expanded CSV gate coverage.

**Architecture:** Keep the Sprint 0/1 FastAPI service and admin/runtime APIs as the system of record. Add operator assets around the existing service: Docker/Compose runtime profile, environment contracts, readiness endpoints, security scripts, evidence/report helpers, Dify templates, BGE-M3 diagnostics, and richer pilot fixtures. The runtime routing path remains API key auth -> active release context -> policy/risk/off-topic checks -> exact pgvector semantic search -> decision response -> trace/audit persistence.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL 16 + pgvector, Docker/Compose, httpx, pytest, ruff, mypy, FlagEmbedding BGE-M3 CPU-only provider, application-level AES-256-GCM envelope encryption, Markdown/JSON evidence reports.

---

## Source Context

Sprint 2 starts from `main` after Sprint 1 has been merged.

- Latest known `main` HEAD: `67477cf docs: harden pilot operator contracts`
- Existing verification baseline: `ruff`, `mypy`, and `pytest` pass with 230 tests.
- Sprint 0 plan: `docs/superpowers/plans/2026-06-25-intent-routing-sprint-0.md`
- Sprint 1 plan: `docs/superpowers/plans/2026-06-26-intent-routing-sprint-1.md`
- Local runbook: `docs/ops/intent-routing-local-runbook.md`
- Pilot runbook: `docs/ops/intent-routing-pilot-runbook.md`
- Dify guide: `docs/integrations/dify-http-request-node.md`
- Runtime examples: `docs/api/openapi-runtime-examples.md`

Current implementation observations:

- `compose.yaml` currently contains only PostgreSQL with a pgvector image and healthcheck.
- `/healthz` is a liveness check and does not validate DB, migrations, pgvector, or embedding readiness.
- There is no `Dockerfile`, `.dockerignore`, closed-network env example, or Compose runtime profile.
- API key create and revoke endpoints already exist; rotation workflow is not automated.
- Admin auth uses `ADMIN_BOOTSTRAP_TOKEN` and trusted headers through `require_admin_context`.
- Raw query decrypt already requires `system_admin` or scoped `auditor`, `view_reason` length is enforced, and `raw_query.viewed` audit logs are written.
- BGE-M3 provider is CPU-only, lazy-loads the model, forces offline Hugging Face settings, and requires a local `BGE_M3_MODEL_PATH`.
- Runtime and CSV tests pass `service.max_input_tokens` into embedding calls; the pilot seed creates services with `max_input_tokens=256`.
- CSV runner supports `positive`, `confusing`, `risk`, `off_topic`, and `fallback` case types. It does not yet support an explicit `clarify` case type.
- `run_csv_gate.py` writes threshold summary reports, but does not fetch and render case-level results.

## Locked Pilot Decisions

These choices are fixed for Sprint 2 unless the product owner explicitly changes them:

- Closed-network pilot deployment uses Docker Compose, not Kubernetes/OpenShift.
- Closed-network runtime environment is `pilot`; `.env.closed-network.example` must use `INTENT_ROUTING_ENVIRONMENT=pilot`.
- CSV coverage is tiered:
  - `30`: minimum pilot gate dataset.
  - `50`: normal pilot dataset and the default Sprint 2 recommendation.
  - `100`: higher-confidence pilot dataset for stronger regression coverage.
  - `custom`: operator-supplied CSV path that follows the same header and coverage rules.

## Sprint 2 Scope

Deliverables:

- Closed-network Docker/Compose runtime profile with migration and runtime services.
- Closed-network environment contract and deployment runbook.
- `/readyz` readiness endpoint that validates dependencies needed before Dify traffic is allowed.
- API key rotation script and operator documentation.
- Admin token, KEK, and raw query decrypt approval/audit procedures.
- Fresh-DB pilot readiness automation that creates evidence reports without secrets.
- Dify HTTP Request node template plus branch playbook for every decision and timeout/error path.
- BGE-M3 real-model benchmark and closed-network model-path operating contract.
- Tiered pilot CSV expansion for 30, 50, 100, and custom datasets, including explicit `clarify` coverage and all seven global risk types.
- Threshold comparison report improvements with per-case failure/review tables.

Non-goals:

- No management UI.
- No Dify plugin packaging.
- No production IAM, OIDC, Keycloak, HMAC signing, or mTLS implementation.
- No HNSW, sparse retrieval, multi-vector retrieval, or LLM judge path.
- No external KMS/HSM integration code. Sprint 2 documents the KEK handoff and current single-active-KEK constraint.
- No KEK rewrap migration. Rewrapping existing encrypted DEKs should be a separate sprint because it changes cryptographic lifecycle behavior.
- No model download at application startup or runtime.

## Planned File Structure

Create:

```text
Dockerfile
.dockerignore
.env.closed-network.example
docs/ops/closed-network-deployment.md
docs/ops/security-operations.md
docs/ops/pilot-readiness-evidence.md
docs/ops/bge-m3-closed-network.md
docs/integrations/dify-http-request-node-template.json
docs/integrations/dify-branching-playbook.md
src/intent_routing/health.py
src/intent_routing/ops/readiness_report.py
src/intent_routing/embedding/diagnostics.py
scripts/rotate_api_key.py
scripts/run_pilot_readiness.py
scripts/benchmark_bge_m3.py
tests/unit/test_closed_network_packaging_contract.py
tests/unit/test_security_ops_docs_contract.py
tests/unit/test_api_key_rotation_script.py
tests/unit/test_readiness_report.py
tests/unit/test_dify_template_contract.py
tests/unit/test_bge_benchmark_script.py
tests/integration/test_readiness_api.py
tests/integration/test_api_key_rotation_flow.py
tests/integration/test_pilot_readiness_flow.py
```

Modify:

```text
compose.yaml
README.md
.env.example
docs/ops/intent-routing-local-runbook.md
docs/ops/intent-routing-pilot-runbook.md
docs/pilot/README.md
docs/pilot/it-helpdesk-pilot-cases.csv
docs/pilot/it-helpdesk-pilot-catalog.json
docs/integrations/dify-http-request-node.md
docs/api/openapi-runtime-examples.md
src/intent_routing/main.py
src/intent_routing/ops/admin_client.py
src/intent_routing/ops/reports.py
src/intent_routing/testing/csv_runner.py
scripts/run_csv_gate.py
scripts/smoke_runtime_dify.py
scripts/trace_audit_drill.py
tests/unit/test_env_contract.py
tests/unit/test_pilot_fixtures.py
tests/unit/test_ops_reports.py
tests/unit/test_operator_docs_contract.py
tests/unit/test_dify_smoke.py
```

File responsibilities:

- `Dockerfile`: build a runtime image that installs the app and starts Uvicorn without downloading models at runtime.
- `.env.closed-network.example`: document deploy-time variables for closed-network pilot use.
- `compose.yaml`: add `migrate` and `api` services under an explicit runtime profile while preserving local PostgreSQL behavior.
- `src/intent_routing/health.py`: isolate readiness checks from FastAPI route wiring.
- `scripts/rotate_api_key.py`: create a next API key, verify it, optionally revoke the old key, and write a secret state file plus non-secret rotation report.
- `scripts/run_pilot_readiness.py`: run the pilot runbook API path from a clean service/database state and write evidence reports.
- `src/intent_routing/ops/readiness_report.py`: deterministic JSON/Markdown rendering for readiness evidence.
- `scripts/benchmark_bge_m3.py`: run CPU-only BGE-M3 latency/memory checks against a local model path.
- `src/intent_routing/embedding/diagnostics.py`: reusable model diagnostics and timing helpers that tests can exercise without a real model.
- `docs/integrations/dify-http-request-node-template.json`: machine-checked template for the Dify HTTP Request node contract.

## Task 1: Closed-Network Packaging And Environment Contract

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`
- Create: `.env.closed-network.example`
- Create: `docs/ops/closed-network-deployment.md`
- Modify: `compose.yaml`
- Modify: `README.md`
- Modify: `docs/ops/intent-routing-local-runbook.md`
- Modify: `docs/ops/intent-routing-pilot-runbook.md`
- Test: `tests/unit/test_closed_network_packaging_contract.py`
- Test: `tests/unit/test_env_contract.py`
- Test: `tests/unit/test_operator_docs_contract.py`

- [ ] **Step 1: Write packaging contract tests**

  Add tests that assert:

  - `Dockerfile` exists.
  - `Dockerfile` uses Python 3.12, installs the package, sets `PYTHONUNBUFFERED=1`, and does not contain any raw secret value.
  - `.dockerignore` excludes `.git`, `.venv`, `var/`, `*.secret.json`, `.pytest_cache`, `.mypy_cache`, and `__pycache__/`.
  - `compose.yaml` contains `postgres`, `migrate`, and `api` services.
  - `api` has a runtime profile, reads `.env.closed-network.example` only as a documented template, mounts `/models/bge-m3` read-only, and exposes the application only through the configured internal port.
  - `migrate` runs `uv run alembic upgrade head` or the image equivalent command before the API is declared ready.
  - `.env.closed-network.example` includes `DATABASE_URL`, `INTENT_ROUTING_ENVIRONMENT`, `ADMIN_BOOTSTRAP_TOKEN`, `RAW_TEXT_KEK_ID`, `RAW_TEXT_KEK_BASE64`, `EMBEDDING_PROVIDER=bge-m3`, `BGE_M3_MODEL_PATH=/models/bge-m3`, `BGE_M3_BATCH_SIZE=16`, and `BGE_M3_MAX_TOKENS=256`.

  Run:

  ```bash
  uv run pytest tests/unit/test_closed_network_packaging_contract.py tests/unit/test_env_contract.py -v
  ```

  Expected before implementation: fail because the closed-network packaging files do not exist.

- [ ] **Step 2: Add runtime image**

  Implement `Dockerfile` with these constraints:

  - Base image: Python 3.12 slim variant.
  - Install only OS packages needed for runtime and PostgreSQL client health checks.
  - Install Python dependencies through the repository lock/tooling used by the project.
  - Do not run `FlagEmbedding` model downloads during image build.
  - Create and run as a non-root user.
  - Default command starts Uvicorn factory app:

  ```bash
  uv run uvicorn intent_routing.main:create_app --factory --host 0.0.0.0 --port 8000
  ```

- [ ] **Step 3: Add `.dockerignore`**

  Exclude development caches, git metadata, local virtualenvs, secret state files, and generated evidence:

  ```text
  .git
  .venv
  __pycache__
  .pytest_cache
  .mypy_cache
  .ruff_cache
  var
  *.secret.json
  ```

- [ ] **Step 4: Add closed-network env contract**

  Create `.env.closed-network.example` with non-secret sample values and explicit replacement markers:

  ```dotenv
  DATABASE_URL=postgresql+psycopg://intent:${INTENT_DB_PASSWORD}@postgres:5432/intent_routing
  INTENT_ROUTING_ENVIRONMENT=pilot
  ADMIN_BOOTSTRAP_TOKEN=replace-with-internal-secret-manager-value
  RAW_TEXT_KEK_ID=pilot-kek-20260628-001
  RAW_TEXT_KEK_BASE64=replace-with-32-byte-base64-kek-from-approved-secret-store
  EMBEDDING_PROVIDER=bge-m3
  BGE_M3_MODEL_PATH=/models/bge-m3
  BGE_M3_MODEL_SHA256=
  BGE_M3_BATCH_SIZE=16
  BGE_M3_MAX_TOKENS=256
  EMBED_EXAMPLES_FROM=masked
  ```

  Document that `BGE_M3_MAX_TOKENS` is an operator default and the runtime source of truth is `services.max_input_tokens`, seeded as `256` for the pilot.

- [ ] **Step 5: Extend Compose**

  Update `compose.yaml` so a closed-network operator can run:

  ```bash
  docker compose --profile runtime up -d postgres migrate api
  ```

  Required service behavior:

  - `postgres`: keep existing pgvector image and healthcheck.
  - `migrate`: uses the runtime image, depends on healthy `postgres`, runs Alembic once, exits successfully.
  - `api`: uses the runtime image, depends on successful `migrate`, mounts the BGE-M3 model path read-only, and has a healthcheck against `/readyz`.

- [ ] **Step 6: Write deployment runbook**

  Create `docs/ops/closed-network-deployment.md` with:

  - Image build command.
  - Offline image export/import command.
  - Model directory mount contract.
  - Env injection contract.
  - Migration order.
  - Liveness/readiness commands.
  - Rollback rule: revert to prior image plus prior active `release_version`; do not mutate catalog data during rollback.
  - Secret handling rule: `.env.closed-network.example` is a template and must not be used as the real secret file.

- [ ] **Step 7: Update existing docs**

  Update `README.md`, local runbook, and pilot runbook to link the new closed-network deployment runbook without changing the Sprint 1 local quick-start path.

- [ ] **Step 8: Verify packaging task**

  Run:

  ```bash
  uv run pytest tests/unit/test_closed_network_packaging_contract.py tests/unit/test_env_contract.py tests/unit/test_operator_docs_contract.py -v
  docker compose config
  ```

  Expected: tests pass and Compose config renders without invalid services.

- [ ] **Step 9: Commit**

  ```bash
  git add Dockerfile .dockerignore .env.closed-network.example compose.yaml README.md docs/ops tests/unit/test_closed_network_packaging_contract.py tests/unit/test_env_contract.py tests/unit/test_operator_docs_contract.py
  git commit -m "build: add closed-network runtime packaging"
  ```

**Acceptance Criteria:**

- Runtime image can be built without a model download.
- Compose has a reproducible `postgres -> migrate -> api` runtime profile.
- Closed-network env keys are documented and tested.
- Existing local runbook remains valid.

## Task 2: Readiness And Migration Checks

**Files:**
- Create: `src/intent_routing/health.py`
- Modify: `src/intent_routing/main.py`
- Modify: `compose.yaml`
- Modify: `docs/ops/closed-network-deployment.md`
- Test: `tests/integration/test_readiness_api.py`

- [ ] **Step 1: Write readiness tests**

  Add integration tests for:

  - `GET /healthz` returns `200 {"status":"ok"}` without opening a DB session.
  - `GET /readyz` returns HTTP 200 when DB connection, Alembic head, and pgvector extension checks pass.
  - `GET /readyz` returns HTTP 503 with `status=not_ready` when DB connection fails.
  - The readiness response never includes `DATABASE_URL`, API keys, KEK material, or raw exception strings.

  Run:

  ```bash
  uv run pytest tests/integration/test_readiness_api.py -v
  ```

  Expected before implementation: fail because `/readyz` does not exist.

- [ ] **Step 2: Implement health check helpers**

  Create `src/intent_routing/health.py` with focused helpers:

  - `check_database(session_factory)`: executes `SELECT 1`.
  - `check_alembic_head(session_factory)`: compares `alembic_version.version_num` with the repository Alembic head.
  - `check_pgvector(session_factory)`: verifies `vector` exists in `pg_extension`.
  - `readiness_payload(...)`: returns a deterministic payload with `status`, `checks`, and no secrets.

- [ ] **Step 3: Wire `/readyz`**

  Add `GET /readyz` in `src/intent_routing/main.py`.

  Response contract:

  ```json
  {
    "status": "ready",
    "checks": {
      "database": "ok",
      "alembic": "ok",
      "pgvector": "ok"
    }
  }
  ```

  Failure contract:

  ```json
  {
    "status": "not_ready",
    "checks": {
      "database": "failed",
      "alembic": "skipped",
      "pgvector": "skipped"
    }
  }
  ```

  Use HTTP 503 for `not_ready`.

- [ ] **Step 4: Update Compose healthcheck**

  Point the `api` service healthcheck to `/readyz` so Dify traffic is not routed before DB migrations and pgvector are available.

- [ ] **Step 5: Verify readiness task**

  Run:

  ```bash
  uv run pytest tests/integration/test_readiness_api.py tests/integration/test_runtime_api.py::test_healthz_returns_ok -v
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add src/intent_routing/health.py src/intent_routing/main.py compose.yaml docs/ops/closed-network-deployment.md tests/integration/test_readiness_api.py
  git commit -m "feat: add runtime readiness checks"
  ```

**Acceptance Criteria:**

- `/healthz` remains cheap liveness.
- `/readyz` blocks traffic until DB, migration state, and pgvector are ready.
- Readiness failures are safe for closed-network operators to paste into incident tickets.

## Task 3: Security Operations, API Key Rotation, And Raw Query Approval

**Files:**
- Create: `scripts/rotate_api_key.py`
- Create: `docs/ops/security-operations.md`
- Modify: `scripts/trace_audit_drill.py`
- Modify: `docs/ops/intent-routing-pilot-runbook.md`
- Modify: `src/intent_routing/ops/admin_client.py`
- Test: `tests/unit/test_security_ops_docs_contract.py`
- Test: `tests/unit/test_api_key_rotation_script.py`
- Test: `tests/unit/test_trace_audit_drill_contract.py`
- Test: `tests/integration/test_api_key_rotation_flow.py`

- [ ] **Step 1: Write security docs contract tests**

  Tests must assert that `docs/ops/security-operations.md` documents:

  - API key create, overlap, smoke, revoke, and rollback steps.
  - Admin token source, rotation, and restart requirement.
  - `system_admin`, `service_developer`, `service_operator`, and `auditor` role usage.
  - KEK storage in approved internal secret management and per-environment separation.
  - Current KEK limitation: changing `RAW_TEXT_KEK_ID` without a rewrap migration makes old raw text undecryptable.
  - Raw query decrypt requires approval ID, reason, scoped auditor or system admin, and audit evidence.

- [ ] **Step 2: Write rotation script unit tests**

  Use fake `AdminApiClient` and fake runtime smoke calls to verify:

  - The script reads the current Sprint 1 state file.
  - It creates a new API key for the same `service_id`, `environment`, and `app_id`.
  - It derives allowed intents and route keys from `docs/pilot/it-helpdesk-pilot-catalog.json` unless explicit CLI allowlists are passed.
  - It writes a new `.secret.json` file with mode `0600`.
  - It writes a non-secret rotation report under `var/reports`.
  - It does not print raw API key secret to stdout or report JSON.
  - With `--revoke-old`, it calls `/admin/v1/api-keys/{old_key_id}:revoke` only after the new key smoke succeeds.

- [ ] **Step 3: Implement `scripts/rotate_api_key.py`**

  CLI contract:

  ```bash
  uv run python scripts/rotate_api_key.py \
    --base-url http://127.0.0.1:8000 \
    --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
    --state ${STATE_PATH} \
    --catalog docs/pilot/it-helpdesk-pilot-catalog.json \
    --out-state var/pilot/${SERVICE_ID}.rotated.state.secret.json \
    --report-dir var/reports \
    --smoke-query "API timeout 500 에러가 납니다" \
    --revoke-old
  ```

  Behavior:

  - Actor: `api-key-rotation`.
  - Roles: `system_admin`.
  - New key expiration: default 365 days, configurable through `--expires-in-days`.
  - The report includes old `key_id`, new `key_id`, new key fingerprint, smoke `trace_id`, revoke status, and timestamps.
  - The report excludes `api_key`, `Authorization`, `RAW_TEXT_KEK_BASE64`, and query raw text.

- [ ] **Step 4: Add integration rotation flow**

  In `tests/integration/test_api_key_rotation_flow.py`:

  - Seed the pilot through TestClient.
  - Run a smoke request with the old key and assert 200.
  - Run rotation and assert the new state works.
  - If `--revoke-old` is enabled, assert the old key receives HTTP 401 `AUTHENTICATION_FAILED`.
  - Assert an `api_key.revoked` audit log exists for the old key.

- [ ] **Step 5: Extend trace audit drill**

  Update `scripts/trace_audit_drill.py` so raw decrypt mode accepts an approval ID:

  ```bash
  --approval-id SEC-20260628-001 --view-reason "장애 분석 ticket INC-20260628-001"
  ```

  The script should send a composed `view_reason` such as:

  ```text
  approval=SEC-20260628-001; reason=장애 분석 ticket INC-20260628-001
  ```

  It must continue printing only `raw_query_viewed=true` and never print the raw query.

- [ ] **Step 6: Write security operations runbook**

  Create `docs/ops/security-operations.md` with four sections:

  - API key lifecycle: issue, overlap, verify, revoke, rollback.
  - Admin token operations: source, rotation window, restart, verification, emergency rollback.
  - KEK operations: storage, per-environment keys, current single-active-KEK constraint, approved follow-up for DEK rewrap.
  - Raw query decrypt: approval, scoped role, command, evidence, retention.

- [ ] **Step 7: Verify security task**

  Run:

  ```bash
  uv run pytest tests/unit/test_security_ops_docs_contract.py tests/unit/test_api_key_rotation_script.py tests/unit/test_trace_audit_drill_contract.py tests/integration/test_api_key_rotation_flow.py -v
  ```

- [ ] **Step 8: Commit**

  ```bash
  git add scripts/rotate_api_key.py scripts/trace_audit_drill.py src/intent_routing/ops/admin_client.py docs/ops/security-operations.md docs/ops/intent-routing-pilot-runbook.md tests/unit/test_security_ops_docs_contract.py tests/unit/test_api_key_rotation_script.py tests/unit/test_trace_audit_drill_contract.py tests/integration/test_api_key_rotation_flow.py
  git commit -m "feat: add security operations workflows"
  ```

**Acceptance Criteria:**

- API key rotation is executable without exposing the new secret outside the secret state file.
- Old key revocation is audited and verified.
- Admin token and KEK procedures are explicit about current implementation limits.
- Raw query decrypt has a concrete approval/evidence path.

## Task 4: Fresh-DB Pilot Readiness Evidence Automation

**Files:**
- Create: `src/intent_routing/ops/readiness_report.py`
- Create: `scripts/run_pilot_readiness.py`
- Create: `docs/ops/pilot-readiness-evidence.md`
- Modify: `scripts/run_csv_gate.py`
- Modify: `docs/ops/intent-routing-pilot-runbook.md`
- Test: `tests/unit/test_readiness_report.py`
- Test: `tests/integration/test_pilot_readiness_flow.py`

- [ ] **Step 1: Extract CSV gate function**

  Refactor `scripts/run_csv_gate.py` so the CLI keeps the same behavior and a function can be imported:

  ```python
  run_threshold_comparison(
      base_url: str,
      admin_token: str,
      state_path: Path,
      csv_path: Path,
      out_dir: Path,
  ) -> ThresholdComparisonResult
  ```

  The result must include summary runs, report paths, and per-preset `test_run_id` values.

- [ ] **Step 2: Write readiness report tests**

  In `tests/unit/test_readiness_report.py`, assert that JSON and Markdown evidence include:

  - Service ID.
  - Environment.
  - Health and readiness statuses.
  - Migration check result.
  - Seeded release version.
  - Threshold comparison table.
  - Smoke decisions for `confident`, `risk`, `off_topic`, `fallback`, and `clarify`.
  - Trace/audit drill result.
  - Final checklist with PASS/FAIL.

  Assert that reports do not contain `api_key`, `Authorization`, `RAW_TEXT_KEK_BASE64`, raw query text, or `.secret.json` content.

- [ ] **Step 3: Implement report renderer**

  Create `src/intent_routing/ops/readiness_report.py` with deterministic renderers:

  - `render_readiness_json(payload)`.
  - `render_readiness_markdown(payload)`.
  - `redact_secret_values(payload)`.

  The JSON file is the machine-readable evidence. The Markdown file is the operator-facing checklist.

- [ ] **Step 4: Implement `scripts/run_pilot_readiness.py`**

  CLI contract:

  ```bash
  uv run python scripts/run_pilot_readiness.py \
    --base-url http://127.0.0.1:8000 \
    --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
    --service-id ${SERVICE_ID} \
    --environment ${INTENT_ROUTING_ENVIRONMENT} \
    --state-path ${STATE_PATH} \
    --csv-tier standard \
    --out-dir var/evidence/${SERVICE_ID}
  ```

  CSV tier behavior:

  - `--csv-tier minimum` uses `docs/pilot/it-helpdesk-pilot-cases-30.csv`.
  - `--csv-tier standard` uses `docs/pilot/it-helpdesk-pilot-cases-50.csv` and is the default.
  - `--csv-tier high-confidence` uses `docs/pilot/it-helpdesk-pilot-cases-100.csv`.
  - `--csv-tier custom --csv <path>` uses the supplied CSV path.

  Workflow:

  1. Call `/healthz`.
  2. Call `/readyz`.
  3. Run `seed_pilot.py` logic through import, not shell.
  4. Run threshold comparison through the extracted function.
  5. Run runtime smoke cases for confident, risk, off_topic, fallback, and clarify.
  6. Run masked trace listing.
  7. Optionally run raw decrypt audit only when `--raw-decrypt-trace-id` and approval fields are supplied.
  8. Write `readiness-report.json` and `readiness-report.md`.

- [ ] **Step 5: Add integration test**

  In `tests/integration/test_pilot_readiness_flow.py`:

  - Use TestClient and a clean SQLAlchemy session.
  - Seed a unique service ID.
  - Run the readiness workflow.
  - Assert generated reports exist.
  - Assert balanced CSV gate passes and risk pass rate is 100%.
  - Assert evidence contains no raw API key or raw query.

- [ ] **Step 6: Update runbook**

  Add a fresh-DB manual sequence to `docs/ops/intent-routing-pilot-runbook.md`:

  ```bash
  docker compose down -v
  docker compose up -d postgres
  uv run alembic upgrade head
  uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000
  uv run python scripts/run_pilot_readiness.py ...
  ```

- [ ] **Step 7: Verify evidence task**

  Run:

  ```bash
  uv run pytest tests/unit/test_readiness_report.py tests/integration/test_pilot_readiness_flow.py -v
  ```

- [ ] **Step 8: Commit**

  ```bash
  git add src/intent_routing/ops/readiness_report.py scripts/run_pilot_readiness.py scripts/run_csv_gate.py docs/ops/pilot-readiness-evidence.md docs/ops/intent-routing-pilot-runbook.md tests/unit/test_readiness_report.py tests/integration/test_pilot_readiness_flow.py
  git commit -m "feat: automate pilot readiness evidence"
  ```

**Acceptance Criteria:**

- A fresh database run produces one evidence directory containing JSON, Markdown, threshold reports, and secret state file.
- Evidence reports do not expose API keys or raw query values.
- The pilot runbook can be validated end-to-end through a single readiness command after the API is running.

## Task 5: Dify HTTP Request Node Template And Branch Playbook

**Files:**
- Create: `docs/integrations/dify-http-request-node-template.json`
- Create: `docs/integrations/dify-branching-playbook.md`
- Modify: `docs/integrations/dify-http-request-node.md`
- Modify: `docs/api/openapi-runtime-examples.md`
- Modify: `scripts/smoke_runtime_dify.py`
- Test: `tests/unit/test_dify_template_contract.py`
- Test: `tests/unit/test_dify_smoke.py`
- Test: `tests/unit/test_operator_docs_contract.py`

- [ ] **Step 1: Write Dify template contract tests**

  Add tests that parse `docs/integrations/dify-http-request-node-template.json` and assert:

  - Method is `POST`.
  - URL uses `http://intent-routing.internal/v1/intent-route`.
  - Headers include `Authorization`, `X-Key-Id`, `X-App-Id`, `X-Service-Id`, `X-Request-Id`, and `Content-Type`.
  - Body maps `query`, `channel`, and `user_context.workflow_run_id`.
  - Decision branches include `confident`, `clarify`, `fallback`, `off_topic`, `risk`, and `unauthorized`.
  - Error branches include `401`, `403`, `422`, `408`, `5xx`, and timeout.
  - Every branch carries `trace_id` and `request_id` into Dify logs or user-facing handoff context.

- [ ] **Step 2: Extend Dify smoke script**

  Update `scripts/smoke_runtime_dify.py` with optional flags:

  ```bash
  --request-id dify-smoke-local-001
  --timeout-seconds 8
  --expect-route-key it.api_timeout.manual_lookup
  --output var/evidence/${SERVICE_ID}/dify-smoke-confident.json
  ```

  Keep existing defaults compatible with Sprint 1.

- [ ] **Step 3: Create template JSON**

  The template JSON should be intentionally simple and stable:

  - `node_type`: `http_request`
  - `method`: `POST`
  - `url`: `http://intent-routing.internal/v1/intent-route`
  - `timeout_seconds`: `8`
  - `headers`: array of name/value pairs.
  - `body`: JSON object using Dify variables.
  - `branches`: array of branch names, conditions, and required downstream action.

- [ ] **Step 4: Write branch playbook**

  Create `docs/integrations/dify-branching-playbook.md` with concrete branch behavior:

  - `confident`: branch by `route_key`.
  - `clarify`: answer with `clarify_question`, preserve `trace_id`, and send candidate labels.
  - `fallback`: fixed message or human handoff.
  - `off_topic`: service-scope fixed message.
  - `risk`: block message and security trace handoff.
  - `unauthorized`: do not execute route; operator triage.
  - `401`, `403`, `422`: Dify configuration error.
  - `408`, `5xx`, timeout: client fallback or human handoff; no automatic retry loop.

- [ ] **Step 5: Update existing Dify docs and runtime examples**

  Update `docs/integrations/dify-http-request-node.md` to point to the template and playbook. Update `docs/api/openapi-runtime-examples.md` so `request_id` propagation is shown consistently in every example.

- [ ] **Step 6: Verify Dify task**

  Run:

  ```bash
  uv run pytest tests/unit/test_dify_template_contract.py tests/unit/test_dify_smoke.py tests/unit/test_operator_docs_contract.py -v
  ```

- [ ] **Step 7: Commit**

  ```bash
  git add docs/integrations docs/api/openapi-runtime-examples.md scripts/smoke_runtime_dify.py tests/unit/test_dify_template_contract.py tests/unit/test_dify_smoke.py tests/unit/test_operator_docs_contract.py
  git commit -m "docs: add Dify branch template"
  ```

**Acceptance Criteria:**

- Dify integration has a checked-in template, not only prose.
- Decision, HTTP error, and timeout branches are documented with trace propagation.
- Smoke script can produce per-branch evidence files without leaking secrets.

## Task 6: BGE-M3 Real-Model Readiness

**Files:**
- Create: `src/intent_routing/embedding/diagnostics.py`
- Create: `scripts/benchmark_bge_m3.py`
- Create: `docs/ops/bge-m3-closed-network.md`
- Modify: `.env.closed-network.example`
- Modify: `docs/pilot/README.md`
- Test: `tests/unit/test_bge_benchmark_script.py`
- Test: `tests/unit/test_embedding_provider.py`

- [ ] **Step 1: Write benchmark tests**

  Use a fake embedding provider in tests and assert:

  - Benchmark accepts a local model path.
  - It passes `max_tokens=256`.
  - It records `model_version`, `dimension`, `batch_size`, query count, p50 latency, p95 latency, elapsed time, and max RSS memory.
  - It writes JSON and Markdown reports.
  - It fails with a clear message when `BGE_M3_MODEL_PATH` does not exist.
  - It does not import `FlagEmbedding` during argument parsing.

- [ ] **Step 2: Add diagnostics helpers**

  Create `src/intent_routing/embedding/diagnostics.py` with:

  - `EmbeddingBenchmarkCase`.
  - `EmbeddingBenchmarkResult`.
  - `run_embedding_benchmark(provider, texts, max_tokens, repeats)`.
  - `render_benchmark_json(result)`.
  - `render_benchmark_markdown(result)`.

- [ ] **Step 3: Implement benchmark script**

  CLI contract:

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

  The script should:

  - Force offline provider behavior through existing provider code.
  - Use masked CSV queries.
  - Warm up once before measuring.
  - Validate dimension is 1024.
  - Write `bge-m3-benchmark.json` and `bge-m3-benchmark.md`.

- [ ] **Step 4: Write BGE-M3 operations runbook**

  Create `docs/ops/bge-m3-closed-network.md` with:

  - Model import package contents.
  - Local path and checksum contract.
  - CPU-only expectation.
  - Max length 256-token pilot setting.
  - Benchmark command and evidence interpretation.
  - Failure handling when model path or optional dependencies are missing.
  - Rule that production runtime must not download model files.

- [ ] **Step 5: Verify BGE task**

  Run:

  ```bash
  uv run pytest tests/unit/test_bge_benchmark_script.py tests/unit/test_embedding_provider.py -v
  ```

  Manual real-model command runs only when `/models/bge-m3` is mounted.

- [ ] **Step 6: Commit**

  ```bash
  git add src/intent_routing/embedding/diagnostics.py scripts/benchmark_bge_m3.py docs/ops/bge-m3-closed-network.md .env.closed-network.example docs/pilot/README.md tests/unit/test_bge_benchmark_script.py tests/unit/test_embedding_provider.py
  git commit -m "feat: add BGE-M3 readiness benchmark"
  ```

**Acceptance Criteria:**

- BGE-M3 transition has a repeatable local-model benchmark.
- Benchmark proves CPU-only offline operation and 1024-dimensional outputs.
- Max length 256 is verified in benchmark inputs and documented as the pilot default.

## Task 7: CSV Test Expansion And Threshold Report Detail

**Files:**
- Create: `docs/pilot/it-helpdesk-pilot-cases-30.csv`
- Create: `docs/pilot/it-helpdesk-pilot-cases-50.csv`
- Create: `docs/pilot/it-helpdesk-pilot-cases-100.csv`
- Modify: `docs/pilot/it-helpdesk-pilot-cases.csv`
- Modify: `docs/pilot/it-helpdesk-pilot-catalog.json`
- Modify: `docs/pilot/README.md`
- Modify: `src/intent_routing/testing/csv_runner.py`
- Modify: `src/intent_routing/ops/reports.py`
- Modify: `scripts/run_csv_gate.py`
- Test: `tests/unit/test_pilot_fixtures.py`
- Test: `tests/unit/test_csv_gate.py`
- Test: `tests/unit/test_ops_reports.py`
- Test: `tests/integration/test_pilot_seed_flow.py`
- Test: `tests/integration/test_dify_smoke_flow.py`

- [ ] **Step 1: Add explicit `clarify` case type**

  Extend `src/intent_routing/testing/csv_runner.py`:

  - Add `clarify -> clarify` to `EXPECTED_DECISIONS`.
  - Require `expected_intent` to be empty for `clarify`.
  - Keep the CSV header unchanged: `case_id,query,expected_intent,case_type,memo`.

  Add unit tests for valid and invalid clarify rows.

- [ ] **Step 2: Expand pilot CSV**

  Add tiered pilot CSV fixtures:

  - `docs/pilot/it-helpdesk-pilot-cases-30.csv`: exactly 30 rows for the minimum pilot gate.
  - `docs/pilot/it-helpdesk-pilot-cases-50.csv`: exactly 50 rows for the normal pilot dataset and default Sprint 2 recommendation.
  - `docs/pilot/it-helpdesk-pilot-cases-100.csv`: exactly 100 rows for higher-confidence regression coverage.
  - `docs/pilot/it-helpdesk-pilot-cases.csv`: keep as the default alias and make its contents match the 50-row standard dataset.

  Required coverage for every built-in tier:

  - At least 40% `positive` cases across `it_api_timeout`, `it_password_reset`, and `it_vpn_access`.
  - At least 10% `clarify` cases.
  - At least 7 `risk` cases, one memo for each global risk type: `abuse`, `dangerous_command`, `sensitive_data`, `credential_secret`, `unauthorized_access`, `prompt_injection`, `fraud_or_illegal`.
  - At least 10% `off_topic` cases.
  - At least 10% `fallback` cases.
  - No phone numbers, account numbers, raw secrets, or real personal data in fixture text.

  Custom dataset behavior:

  - Operators may pass any CSV path with `--csv-tier custom --csv <path>`.
  - Custom CSVs must keep the exact header `case_id,query,expected_intent,case_type,memo`.
  - Custom CSVs must satisfy the same parser, PII, risk coverage, and balanced gate rules before they are accepted as pilot evidence.

- [ ] **Step 3: Adjust pilot catalog if needed**

  Add only the minimum positive/negative examples or include/exclude keywords required for the expanded dataset to keep balanced pass rate above 70%. Keep the catalog small enough for operators to understand.

- [ ] **Step 4: Improve threshold reports**

  Extend `src/intent_routing/ops/reports.py` so `render_threshold_report` can include:

  - Summary table by preset.
  - Case result counts by `case_type`.
  - Failed cases table with `case_id`, expected decision, actual decision, expected intent, actual intent, confidence, and reason.
  - Review cases table for clarify/fallback-heavy outcomes.

  Update `scripts/run_csv_gate.py` to call `/admin/v1/services/{service_id}/test-runs/{test_run_id}/results` for each preset and pass those results to the report renderer.

- [ ] **Step 5: Strengthen fixture tests**

  Update `tests/unit/test_pilot_fixtures.py` to assert:

  - Built-in CSV files exist for 30, 50, and 100 rows.
  - `docs/pilot/it-helpdesk-pilot-cases.csv` is byte-for-byte identical to `docs/pilot/it-helpdesk-pilot-cases-50.csv`.
  - Each built-in tier has the exact expected row count.
  - All required case types are present in every built-in tier.
  - Clarify cases exist in every built-in tier.
  - All seven risk types are represented in memos for every built-in tier.
  - No fixture query contains obvious PII or secret-like strings.

- [ ] **Step 6: Verify CSV task**

  Run:

  ```bash
  uv run pytest tests/unit/test_pilot_fixtures.py tests/unit/test_csv_gate.py tests/unit/test_ops_reports.py tests/integration/test_pilot_seed_flow.py tests/integration/test_dify_smoke_flow.py -v
  ```

- [ ] **Step 7: Commit**

  ```bash
  git add docs/pilot src/intent_routing/testing/csv_runner.py src/intent_routing/ops/reports.py scripts/run_csv_gate.py tests/unit/test_pilot_fixtures.py tests/unit/test_csv_gate.py tests/unit/test_ops_reports.py tests/integration/test_pilot_seed_flow.py tests/integration/test_dify_smoke_flow.py
  git commit -m "test: expand pilot CSV readiness coverage"
  ```

**Acceptance Criteria:**

- Pilot CSV fixtures exist for 30, 50, and 100 rows, with 50 rows as the default alias.
- Custom CSV paths are supported by readiness automation and must pass the same parser and gate rules.
- Every built-in CSV tier covers risk, off_topic, clarify, fallback, and positive routing.
- Balanced CSV gate remains at least 70%.
- Risk pass rate remains 100%.
- Threshold reports show which cases changed by preset.

## Final Verification

Run these after all tasks:

```bash
uv run ruff check .
uv run mypy src tests
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing uv run pytest -v
docker compose config
```

Closed-network packaging smoke:

```bash
docker compose --profile runtime build
docker compose --profile runtime up -d postgres migrate api
curl -s http://127.0.0.1:8000/healthz
curl -s http://127.0.0.1:8000/readyz
```

Fresh-DB pilot evidence smoke:

```bash
export DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing
export INTENT_ROUTING_ENVIRONMENT=dev
export ADMIN_BOOTSTRAP_TOKEN=local-admin-token
export RAW_TEXT_KEK_ID=local-kek-001
export RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
export EMBEDDING_PROVIDER=fake
export SERVICE_ID=it-helpdesk-pilot-$(date +%Y%m%d%H%M%S)
export STATE_PATH="var/pilot/${SERVICE_ID}.state.secret.json"

docker compose down -v
docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000
uv run python scripts/run_pilot_readiness.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --environment ${INTENT_ROUTING_ENVIRONMENT} \
  --state-path ${STATE_PATH} \
  --csv-tier standard \
  --out-dir var/evidence/${SERVICE_ID}
```

Secret leak check:

```bash
rg "irt_|RAW_TEXT_KEK_BASE64|Authorization: Bearer|super-secret|query_raw" var/evidence var/reports
```

Expected: no raw API keys, KEK values, bearer tokens, or raw decrypted query values in non-secret reports. The `.secret.json` state file is allowed to contain the active API key and must remain under `var/pilot` with mode `0600`.

## Manual Pilot Acceptance Procedure

1. Confirm the repo is clean before starting implementation:

   ```bash
   git status --short --branch
   ```

2. Build and render Compose config:

   ```bash
   docker compose --profile runtime build
   docker compose --profile runtime config
   ```

3. Start from a fresh local database:

   ```bash
   docker compose down -v
   docker compose up -d postgres
   uv run alembic upgrade head
   ```

4. Start the API and verify liveness/readiness:

   ```bash
   uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000
   curl -s http://127.0.0.1:8000/healthz
   curl -s http://127.0.0.1:8000/readyz
   ```

5. Run pilot readiness evidence automation and confirm all checklist items are PASS.

6. Run API key rotation with `--revoke-old`, then verify:

   - New state file works with `scripts/smoke_runtime_dify.py`.
   - Old state file fails with HTTP 401.
   - Rotation report contains no raw secret.
   - Audit logs contain `api_key.revoked`.

7. Run raw query audit drill with approval ID and confirm:

   - CLI output does not print raw query.
   - Admin API writes `raw_query.viewed` audit log.
   - Evidence report records only trace ID, actor, approval ID, and timestamp.

8. Review Dify template with the Dify operator:

   - Headers match secret variables.
   - `X-Request-Id` uses Dify workflow run ID.
   - Each decision branch has a downstream node.
   - Timeout and 5xx path does not retry in a loop.

9. If BGE-M3 model is available locally, run:

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

10. Attach `var/evidence/${SERVICE_ID}/readiness-report.md`, threshold comparison report, rotation report, Dify smoke output, and BGE-M3 benchmark report to the pilot handoff package.

## Sprint 2 Completion Criteria

- All final verification commands pass.
- Closed-network deployment runbook can be followed without reading source code.
- Fresh-DB readiness evidence can be generated in one operator command after the API is running.
- Dify integration has a checked template and branch playbook.
- API key rotation is tested, documented, and audited.
- KEK and raw query decrypt operations have explicit approval and audit procedures.
- BGE-M3 real-model benchmark is available and optional dependency failures are clear.
- Tiered CSV fixtures support 30, 50, 100, and custom datasets; the default 50-row fixture keeps balanced pass rate at least 70% and risk pass rate 100%.
