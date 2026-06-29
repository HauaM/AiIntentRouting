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
docker compose up -d postgres
DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing uv run alembic upgrade head
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing uv run pytest -q
uv run ruff check .
uv run mypy src tests
docker compose --profile runtime config
```

## Branch Protection

After Sprint 4, require the `CI / verify` check before merging into `main`.

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
