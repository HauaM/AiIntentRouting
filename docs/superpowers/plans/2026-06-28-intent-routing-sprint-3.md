# Sprint 3: Security Lifecycle And Operations Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the closed-network pilot from Sprint 2 readiness into production-approval hardening by adding safe raw-text KEK rotation, runtime raw-query retention, auditable security/metrics APIs, and a repeatable operations evidence package.

**Architecture:** Keep the Sprint 0-2 FastAPI service and PostgreSQL schema as the system of record. Add narrowly scoped security lifecycle modules around existing envelope-encrypted raw text, runtime logs, audit logs, and operator scripts; routing behavior, Dify contracts, threshold presets, and exact pgvector search stay unchanged. The most important design constraint is that current encrypted envelopes bind `key_id` into AES-GCM associated data, so Sprint 3 must full-decrypt and re-encrypt records during KEK migration rather than mutating only encrypted DEKs.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL 16 + pgvector, cryptography AES-256-GCM, httpx, pytest, ruff, mypy, Docker Compose, Markdown/JSON evidence reports.

---

## Source Context Reviewed

Required documents checked before writing this plan:

- `docs/superpowers/plans/2026-06-25-intent-routing-sprint-0.md`
- `docs/superpowers/plans/2026-06-26-intent-routing-sprint-1.md`
- `docs/superpowers/plans/2026-06-28-intent-routing-sprint-2.md`
- `docs/ops/closed-network-deployment.md`
- `docs/ops/security-operations.md`
- `docs/ops/pilot-readiness-evidence.md`
- `docs/ops/bge-m3-closed-network.md`
- `docs/integrations/dify-branching-playbook.md`
- `docs/pilot/README.md`

Current implementation observations:

- Sprint 0 implemented the API-only vertical slice: admin API, `/v1/intent-route`, API keys, release activation, pgvector exact search, CSV gate, encrypted raw text, PII masking, runtime logs, and audit logs.
- Sprint 1 made the service pilotable through deterministic IT helpdesk fixtures, seed/smoke scripts, threshold comparison reports, Dify mapping, and trace/audit drills.
- Sprint 2 added closed-network packaging, `/healthz`, `/readyz`, runtime Compose profile, API key rotation, readiness evidence automation, Dify branch template/playbook, BGE-M3 CPU-only benchmark tooling, and 30/50/100 pilot CSV tiers.
- `docs/ops/security-operations.md` explicitly leaves safe KEK rewrap as a later sprint limitation.
- Existing encryption uses `EnvelopeEncryptor` with one active `RAW_TEXT_KEK_ID` plus `RAW_TEXT_KEK_BASE64`; decryption fails when `encrypted.key_id` differs from the active key.
- Raw query decrypt is audited, but audit logs are not yet queryable through a scoped admin API.
- Runtime logs have encrypted raw query fields and masked query fields, but no raw-query retention marker.
- Runtime logs have latency and decision fields, but no operator metrics endpoint or consolidated operations evidence export.

## Sprint 3 Recommendation

Recommended Sprint 3 scope: **security lifecycle and operations evidence**, not a routing algorithm rewrite.

This is the right next step because Sprint 2 made the service deployable for a closed-network pilot, while the clearest remaining blocker before production-style operation is lifecycle control over encrypted raw text and operational evidence. HNSW, sparse retrieval, multi-vector retrieval, LLM judge paths, Dify plugin packaging, management UI, production IAM, mTLS, and Kubernetes can remain outside this sprint because they either contradict locked MVP choices or need real pilot traffic evidence first.

## Sprint 3 Scope

Deliverables:

- Multi-KEK raw text keyring that preserves backward compatibility with `RAW_TEXT_KEK_ID` and `RAW_TEXT_KEK_BASE64`.
- Safe raw text KEK migration workflow for both `intent_examples.text_raw_*` and `runtime_logs.query_raw_*`.
- Dry-run-first rewrap CLI with approval ID, actor ID, batch limits, JSON/Markdown reports, and audit/run records.
- Runtime raw-query retention workflow that redacts encrypted raw query material while keeping masked runtime logs available.
- Scoped admin APIs for audit log lookup, raw-text key summary, and runtime metrics.
- Operations evidence export that combines readiness, metrics, audit, key summary, and retention state without secrets.
- Updated closed-network and security operations docs.

Non-goals:

- No changes to routing decision rules, threshold presets, CSV gate semantics, or Dify branch behavior.
- No new vector index type, sparse retrieval, multi-vector retrieval, or LLM judge runtime path.
- No management web UI.
- No production IAM, OIDC, Keycloak, HMAC signing, or mTLS implementation.
- No external KMS/HSM SDK integration. Sprint 3 keeps environment/secret-manager supplied KEK material and documents the handoff point.
- No automatic audit log deletion. Audit logs remain retained; this sprint only adds query/export support and runtime raw-query redaction.

## Planned File Structure

Create:

```text
alembic/versions/0004_security_lifecycle_ops.py
src/intent_routing/config.py
src/intent_routing/security/keyring.py
src/intent_routing/security/rewrap.py
src/intent_routing/ops/retention.py
src/intent_routing/ops/metrics.py
src/intent_routing/ops/evidence.py
scripts/rewrap_raw_text.py
scripts/apply_log_retention.py
scripts/export_ops_evidence.py
docs/ops/security-lifecycle.md
tests/unit/test_security_keyring.py
tests/unit/test_raw_text_rewrap.py
tests/unit/test_log_retention.py
tests/unit/test_ops_metrics.py
tests/unit/test_ops_evidence.py
tests/unit/test_security_lifecycle_docs_contract.py
tests/integration/test_raw_text_rewrap_flow.py
tests/integration/test_log_retention_flow.py
tests/integration/test_ops_metrics_api.py
tests/integration/test_ops_evidence_export.py
```

Modify:

```text
.env.example
.env.closed-network.example
README.md
docs/ops/closed-network-deployment.md
docs/ops/security-operations.md
docs/ops/pilot-readiness-evidence.md
src/intent_routing/api/admin.py
src/intent_routing/db/models.py
src/intent_routing/db/repositories.py
src/intent_routing/domain/enums.py
src/intent_routing/logging/audit.py
src/intent_routing/logging/trace.py
tests/unit/test_env_contract.py
tests/unit/test_security_ops_docs_contract.py
tests/unit/test_operator_docs_contract.py
```

Responsibilities:

- `src/intent_routing/config.py`: typed environment parsing for raw-text keyring and ops retention defaults.
- `src/intent_routing/security/keyring.py`: active plus legacy KEK lookup, encrypt with active key, decrypt by stored key ID.
- `src/intent_routing/security/rewrap.py`: full raw-text re-encryption helpers and table adapters for examples/logs.
- `src/intent_routing/ops/retention.py`: runtime raw-query redaction planning and application logic.
- `src/intent_routing/ops/metrics.py`: sanitized runtime metrics aggregation.
- `src/intent_routing/ops/evidence.py`: deterministic JSON/Markdown rendering for Sprint 3 ops evidence.
- `scripts/rewrap_raw_text.py`: operator CLI for dry-run and execute KEK migration.
- `scripts/apply_log_retention.py`: operator CLI for runtime raw-query redaction.
- `scripts/export_ops_evidence.py`: operator CLI for non-secret security/ops evidence package.
- `docs/ops/security-lifecycle.md`: end-to-end closed-network procedures for KEK migration, retention, metrics, and evidence export.

## Core Contracts

### Raw Text Keyring Environment

Existing variables remain valid:

```dotenv
RAW_TEXT_KEK_ID=pilot-kek-20260628-001
RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
```

Sprint 3 adds optional legacy keys as JSON:

```dotenv
RAW_TEXT_LEGACY_KEKS_JSON={"pilot-kek-20260627-001":"MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE="}
```

Rules:

- New encryption always uses `RAW_TEXT_KEK_ID` and `RAW_TEXT_KEK_BASE64`.
- Decryption uses the stored envelope `key_id` to choose active or legacy KEK material.
- The active key ID must not also appear in `RAW_TEXT_LEGACY_KEKS_JSON`.
- Reports, audit logs, CLI stdout, and Markdown must show key IDs and counts only, never base64 key material or raw plaintext.

### Rewrap Semantics

Current `EnvelopeEncryptor` uses associated data formatted as:

```text
key_id=pilot-kek-20260628-001;algorithm=AES-256-GCM
```

Because the text ciphertext auth tag is bound to `key_id`, Sprint 3 must rewrap raw text by:

1. decrypting the current envelope with the keyring,
2. encrypting plaintext again with the active KEK ID,
3. updating all envelope columns atomically in the same transaction,
4. recording run/audit evidence without plaintext.

Do not implement a DEK-only update that changes `encrypted_dek` and `key_id` while leaving `ciphertext`, `iv`, and `auth_tag` from the old envelope.

### Runtime Raw-Query Retention

Retention redacts encrypted raw-query material from `runtime_logs` only:

- Set all `query_raw_*` envelope columns to `NULL`.
- Preserve `trace_id`, `request_id`, `service_id`, release fields, decision fields, error fields, latency, `decision_state`, `query_masked`, and `created_at`.
- Set `raw_query_deleted_at`, `raw_query_deleted_by`, and `raw_query_delete_reason`.
- After redaction, raw decrypt returns HTTP 410 with `RAW_QUERY_UNAVAILABLE` and no `query_raw`.

Intent example raw text is not retention-redacted in Sprint 3 because approved examples are part of catalog/release evidence. Intent examples are included only in KEK rewrap.

### Admin API Additions

Add these scoped read APIs:

```http
GET /admin/v1/services/{service_id}/audit-logs?limit=50&event_type=raw_query.viewed
GET /admin/v1/services/{service_id}/security/raw-text-key-summary
GET /admin/v1/services/{service_id}/runtime-metrics?window_hours=24
```

Access rules:

- `system_admin`: all endpoints, all services.
- scoped `auditor`: audit logs and raw-text key summary for assigned services.
- scoped `service_operator`: runtime metrics for assigned services.
- `service_developer`: no new security lifecycle read access unless already scoped through existing catalog operations.

## Tasks

### Task 1: Typed Config And Raw Text Keyring

**Files:**

- Create: `src/intent_routing/config.py`
- Create: `src/intent_routing/security/keyring.py`
- Create: `tests/unit/test_security_keyring.py`
- Modify: `src/intent_routing/api/admin.py`
- Modify: `src/intent_routing/logging/audit.py`
- Modify: `src/intent_routing/logging/trace.py`
- Modify: `.env.example`
- Modify: `.env.closed-network.example`
- Modify: `tests/unit/test_env_contract.py`

- [ ] **Step 1: Write failing keyring tests**

Add tests covering active encryption, legacy decryption, missing key IDs, invalid base64, duplicate active/legacy IDs, and secret-safe representation.

```python
def test_keyring_encrypts_with_active_key_and_decrypts_legacy_key() -> None:
    legacy = EnvelopeEncryptor(kek_id="old-kek", kek_base64=_kek(b"1"))
    encrypted = legacy.encrypt_text("보험금 청구 010-1234-5678")

    keyring = RawTextKeyring.from_values(
        active_key_id="new-kek",
        active_kek_base64=_kek(b"2"),
        legacy_keks={"old-kek": _kek(b"1")},
    )

    assert keyring.decrypt_text(encrypted) == "보험금 청구 010-1234-5678"
    assert keyring.encrypt_text("new text").key_id == "new-kek"
```

Run:

```bash
uv run pytest tests/unit/test_security_keyring.py -v
```

Expected: fail because `RawTextKeyring` does not exist.

- [ ] **Step 2: Implement environment parsing and keyring**

Implement these public interfaces:

```text
RawTextKeyringConfig
- active_key_id: str
- active_kek_base64: str
- legacy_keks: dict[str, str]

load_raw_text_keyring_config(environ: Mapping[str, str] | None = None) -> RawTextKeyringConfig

RawTextKeyring.from_values(
    active_key_id: str,
    active_kek_base64: str,
    legacy_keks: Mapping[str, str],
) -> RawTextKeyring

RawTextKeyring.encrypt_text(plaintext: str) -> EncryptedText
RawTextKeyring.decrypt_text(encrypted: EncryptedText) -> str
RawTextKeyring.key_ids() -> Sequence[str]
RawTextKeyring.active_key_id -> str
```

Validation rules:

- `RAW_TEXT_KEK_BASE64` is required.
- `RAW_TEXT_KEK_ID` defaults to `local-kek-001` for local compatibility.
- `RAW_TEXT_LEGACY_KEKS_JSON` defaults to `{}`.
- legacy JSON must be an object from key ID string to base64 string.
- active key ID must not appear in legacy JSON.

- [ ] **Step 3: Replace direct encryptor construction**

Update admin raw-text encryption/decryption and runtime trace logging to call a single keyring factory. Keep the existing failure behavior for invalid active KEK configuration during runtime error fallback.

Run:

```bash
uv run pytest tests/unit/test_security_keyring.py tests/unit/test_encryption.py -v
uv run pytest tests/integration/test_admin_catalog_api.py::test_create_example_encrypts_raw_text_masks_text_and_defaults_unapproved -v
uv run pytest tests/integration/test_trace_audit_logs.py::test_raw_decrypt_returns_plaintext_to_auditor_or_system_admin_and_writes_audit_log -v
```

Expected: pass.

- [ ] **Step 4: Update env examples and env contract tests**

Add `RAW_TEXT_LEGACY_KEKS_JSON={}` to both environment samples. Update tests so closed-network examples keep real secret placeholders but no live key material.

Run:

```bash
uv run pytest tests/unit/test_env_contract.py tests/unit/test_closed_network_packaging_contract.py -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/intent_routing/config.py src/intent_routing/security/keyring.py src/intent_routing/api/admin.py src/intent_routing/logging/audit.py src/intent_routing/logging/trace.py .env.example .env.closed-network.example tests/unit/test_security_keyring.py tests/unit/test_env_contract.py
git commit -m "feat: add raw text keyring"
```

### Task 2: Raw Text Re-Encryption Primitives

**Files:**

- Create: `src/intent_routing/security/rewrap.py`
- Create: `tests/unit/test_raw_text_rewrap.py`
- Modify: `src/intent_routing/logging/audit.py`

- [ ] **Step 1: Write failing tests for full re-encryption**

The tests must prove the migration changes the key ID and ciphertext while preserving plaintext.

```python
def test_reencrypt_envelope_uses_active_key_and_preserves_plaintext() -> None:
    old_encryptor = EnvelopeEncryptor(kek_id="old-kek", kek_base64=_kek(b"1"))
    encrypted = old_encryptor.encrypt_text("raw query text")
    keyring = RawTextKeyring.from_values(
        active_key_id="new-kek",
        active_kek_base64=_kek(b"2"),
        legacy_keks={"old-kek": _kek(b"1")},
    )

    migrated = reencrypt_envelope(encrypted, keyring)

    assert migrated.key_id == "new-kek"
    assert migrated.ciphertext != encrypted.ciphertext
    assert keyring.decrypt_text(migrated) == "raw query text"
```

Run:

```bash
uv run pytest tests/unit/test_raw_text_rewrap.py -v
```

Expected: fail because `rewrap.py` does not exist.

- [ ] **Step 2: Implement envelope re-encryption helpers**

Implement:

```python
def reencrypt_envelope(encrypted: EncryptedText, keyring: RawTextKeyring) -> EncryptedText:
    if encrypted.key_id == keyring.active_key_id:
        return encrypted
    plaintext = keyring.decrypt_text(encrypted)
    return keyring.encrypt_text(plaintext)
```

Expose table adapters:

```text
intent_example_encrypted_text(example: IntentExample) -> EncryptedText
apply_intent_example_encrypted_text(example: IntentExample, encrypted: EncryptedText) -> None
runtime_log_encrypted_query(runtime_log: RuntimeLog) -> EncryptedText | None
apply_runtime_log_encrypted_query(runtime_log: RuntimeLog, encrypted: EncryptedText) -> None
```

Adapter rules:

- Runtime logs without a complete encrypted raw query envelope return `None`.
- Applying an envelope updates every matching ciphertext, DEK, IV, auth tag, algorithm, and key ID field together.
- No helper returns plaintext to callers except through local variables inside `reencrypt_envelope`.

- [ ] **Step 3: Run focused tests**

```bash
uv run pytest tests/unit/test_raw_text_rewrap.py tests/unit/test_encrypted_storage_schema.py -v
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add src/intent_routing/security/rewrap.py src/intent_routing/logging/audit.py tests/unit/test_raw_text_rewrap.py
git commit -m "feat: add raw text rewrap primitives"
```

### Task 3: Security Lifecycle Schema And Repository Methods

**Files:**

- Create: `alembic/versions/0004_security_lifecycle_ops.py`
- Modify: `src/intent_routing/db/models.py`
- Modify: `src/intent_routing/db/repositories.py`
- Modify: `tests/integration/test_release_flow.py`
- Create: `tests/unit/test_log_retention.py`

- [ ] **Step 1: Write failing schema tests**

Add assertions for:

- table `raw_text_rewrap_runs`,
- runtime log columns `raw_query_deleted_at`, `raw_query_deleted_by`, `raw_query_delete_reason`,
- indexes for rewrap run service/time and audit log service/time.

Run:

```bash
uv run pytest tests/integration/test_release_flow.py::test_initial_schema_contains_required_tables_and_columns -v
```

Expected: fail because the schema has no Sprint 3 lifecycle additions.

- [ ] **Step 2: Add migration**

Migration contract:

```python
def upgrade() -> None:
    op.create_table(
        "raw_text_rewrap_runs",
        sa.Column("rewrap_run_id", sa.Text(), primary_key=True),
        sa.Column("service_id", sa.Text(), nullable=True),
        sa.Column("target_key_id", sa.Text(), nullable=False),
        sa.Column("source_key_ids", postgresql.JSONB(), nullable=False),
        sa.Column("included_tables", postgresql.JSONB(), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("approval_id", sa.Text(), nullable=True),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("scanned_count", sa.Integer(), nullable=False),
        sa.Column("rewrapped_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("report", postgresql.JSONB(), nullable=False),
        sa.Column("started_at", TIMESTAMPTZ, nullable=False),
        sa.Column("completed_at", TIMESTAMPTZ, nullable=True),
    )
    op.add_column("runtime_logs", sa.Column("raw_query_deleted_at", TIMESTAMPTZ, nullable=True))
    op.add_column("runtime_logs", sa.Column("raw_query_deleted_by", sa.Text(), nullable=True))
    op.add_column("runtime_logs", sa.Column("raw_query_delete_reason", sa.Text(), nullable=True))
    op.create_index("ix_raw_text_rewrap_runs_service_started", "raw_text_rewrap_runs", ["service_id", sa.text("started_at DESC")])
    op.create_index("ix_audit_logs_service_created_at", "audit_logs", ["service_id", sa.text("created_at DESC")])
```

Use the same revision style as `0002_runtime_log_state.py` and `0003_runtime_logs_service_created_at_index.py`.

- [ ] **Step 3: Update models**

Add model:

```python
class RawTextRewrapRun(Base):
    __tablename__ = "raw_text_rewrap_runs"
    rewrap_run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    service_id: Mapped[str | None] = mapped_column(Text)
    target_key_id: Mapped[str] = mapped_column(Text)
    source_key_ids: Mapped[list[str]] = mapped_column(JSONB)
    included_tables: Mapped[list[str]] = mapped_column(JSONB)
    dry_run: Mapped[bool]
    approval_id: Mapped[str | None] = mapped_column(Text)
    actor_id: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    scanned_count: Mapped[int]
    rewrapped_count: Mapped[int]
    skipped_count: Mapped[int]
    failed_count: Mapped[int]
    report: Mapped[dict[str, Any]] = mapped_column(JSONB)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

Add the three runtime log retention columns to `RuntimeLog`.

- [ ] **Step 4: Add repository methods**

Add methods for:

- creating/updating raw text rewrap runs,
- listing intent examples by service and key ID,
- listing runtime logs by service and key ID,
- counting raw text key IDs across examples and runtime logs,
- listing audit logs with filters,
- redacting runtime raw query envelope fields.

Method names to use consistently:

```text
create_raw_text_rewrap_run
complete_raw_text_rewrap_run
list_intent_examples_for_rewrap
list_runtime_logs_for_rewrap
count_raw_text_key_ids
list_audit_logs
redact_runtime_raw_queries
```

- [ ] **Step 5: Run migration/schema tests**

```bash
uv run pytest tests/integration/test_release_flow.py::test_initial_schema_contains_required_tables_and_columns tests/unit/test_log_retention.py -v
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add alembic/versions/0004_security_lifecycle_ops.py src/intent_routing/db/models.py src/intent_routing/db/repositories.py tests/integration/test_release_flow.py tests/unit/test_log_retention.py
git commit -m "feat: add security lifecycle schema"
```

### Task 4: Dry-Run-First Raw Text Rewrap CLI

**Files:**

- Create: `scripts/rewrap_raw_text.py`
- Create: `tests/integration/test_raw_text_rewrap_flow.py`
- Modify: `src/intent_routing/security/rewrap.py`

- [ ] **Step 1: Write failing integration tests**

Cover:

- dry-run reports legacy key counts and writes no data changes,
- execute requires `--approval-id` and `--confirm-active-key-id`,
- execute re-encrypts legacy intent examples and runtime logs to active key,
- report and audit/run records contain no raw plaintext, API keys, or KEK material,
- records already on the active key are skipped.

Run:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:55432/intent_routing_task4_schema uv run pytest tests/integration/test_raw_text_rewrap_flow.py -v
```

Expected: fail because the CLI does not exist.

- [ ] **Step 2: Implement CLI arguments**

Required arguments:

```text
--service-id it-helpdesk-pilot
--actor-id security-operator
--report-dir var/security
```

Mode arguments:

```text
--dry-run
--execute
--approval-id SEC-20260628-REWRAP-001
--confirm-active-key-id pilot-kek-20260628-002
```

Scope/limit arguments:

```text
--include intent-examples
--include runtime-logs
--batch-size 100
--limit 1000
```

Behavior:

- default mode is dry-run when neither `--dry-run` nor `--execute` is present,
- `--execute` requires `--approval-id`,
- `--execute` requires `--confirm-active-key-id` equal to the active keyring key ID,
- at least one `--include` is required; allow both values by passing `--include both`,
- every run writes JSON and Markdown files named from the run ID, for example `raw-text-rewrap-rtr-20260628-001.json` and `raw-text-rewrap-rtr-20260628-001.md`,
- every run inserts `raw_text_rewrap_runs`,
- execute inserts one `audit_logs` event `raw_text.rewrap.executed` with counts and approval ID.

- [ ] **Step 3: Implement report shape**

JSON report:

```json
{
  "rewrap_run_id": "rtr-20260628-001",
  "service_id": "it-helpdesk-pilot",
  "dry_run": true,
  "target_key_id": "pilot-kek-20260628-002",
  "source_key_ids": ["pilot-kek-20260628-001"],
  "included_tables": ["intent_examples", "runtime_logs"],
  "scanned_count": 42,
  "rewrapped_count": 0,
  "skipped_count": 10,
  "failed_count": 0,
  "plaintext_exported": false
}
```

Markdown report must include a summary table and the same counts. It must not include `query_raw`, `text_raw`, `RAW_TEXT_KEK_BASE64`, bearer tokens, or API key secrets.

- [ ] **Step 4: Run focused tests**

```bash
uv run pytest tests/unit/test_raw_text_rewrap.py -v
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:55432/intent_routing_task4_schema uv run pytest tests/integration/test_raw_text_rewrap_flow.py -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/rewrap_raw_text.py src/intent_routing/security/rewrap.py tests/integration/test_raw_text_rewrap_flow.py
git commit -m "feat: add raw text rewrap workflow"
```

### Task 5: Runtime Raw-Query Retention Redaction

**Files:**

- Create: `src/intent_routing/ops/retention.py`
- Create: `scripts/apply_log_retention.py`
- Create: `tests/integration/test_log_retention_flow.py`
- Modify: `src/intent_routing/api/admin.py`
- Modify: `src/intent_routing/domain/enums.py`
- Modify: `tests/integration/test_trace_audit_logs.py`

- [ ] **Step 1: Write failing retention tests**

Cover:

- dry-run lists eligible runtime logs without modifying rows,
- execute nulls all encrypted raw query columns and sets deletion metadata,
- masked log list still returns the row and `query_masked`,
- raw decrypt returns HTTP 410 with `RAW_QUERY_UNAVAILABLE`,
- execution inserts audit event `runtime_log.raw_query_redacted`.

Run:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:55432/intent_routing_task5_retention uv run pytest tests/integration/test_log_retention_flow.py -v
```

Expected: fail because retention logic does not exist.

- [ ] **Step 2: Add error code and admin decrypt behavior**

Add:

```python
class ErrorCode(StrEnum):
    RAW_QUERY_UNAVAILABLE = "RAW_QUERY_UNAVAILABLE"
```

Admin raw decrypt behavior:

- if the runtime log exists but encrypted raw query fields are absent or `raw_query_deleted_at` is set, return HTTP 410,
- envelope has no `decision`,
- `query_raw` is never included in the response body,
- do not create `raw_query.viewed` audit logs for unavailable raw query data.

- [ ] **Step 3: Implement retention planner and executor**

Public interface contract:

```text
RuntimeRawQueryRetentionPlan
- service_id: str
- older_than_days: int
- eligible_trace_ids: Sequence[str]
- already_redacted_count: int

plan_runtime_raw_query_redaction(
    repository: IntentRoutingRepository,
    service_id: str,
    older_than_days: int,
    limit: int,
) -> RuntimeRawQueryRetentionPlan

apply_runtime_raw_query_redaction(
    repository: IntentRoutingRepository,
    service_id: str,
    trace_ids: Sequence[str],
    actor_id: str,
    reason: str,
) -> int
```

Redaction updates:

```text
query_raw_ciphertext = NULL
query_raw_encrypted_dek = NULL
query_raw_encrypted_dek_iv = NULL
query_raw_encrypted_dek_auth_tag = NULL
query_raw_key_id = NULL
query_raw_iv = NULL
query_raw_auth_tag = NULL
query_raw_algorithm = NULL
raw_query_deleted_at = now()
raw_query_deleted_by = actor_id
raw_query_delete_reason = reason
```

- [ ] **Step 4: Implement retention CLI**

Arguments:

```text
--service-id it-helpdesk-pilot
--older-than-days 30
--limit 500
--actor-id security-operator
--reason "raw query retention policy 30 days"
--report-dir var/security
--dry-run
--execute
--approval-id SEC-20260628-RETENTION-001
```

Rules:

- default mode is dry-run,
- execute requires `--approval-id`,
- output JSON/Markdown report contains trace IDs, timestamps, counts, actor ID, approval ID, and no raw query text.

- [ ] **Step 5: Run focused tests**

```bash
uv run pytest tests/unit/test_log_retention.py -v
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:55432/intent_routing_task5_retention uv run pytest tests/integration/test_log_retention_flow.py tests/integration/test_trace_audit_logs.py -v
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/intent_routing/ops/retention.py scripts/apply_log_retention.py src/intent_routing/api/admin.py src/intent_routing/domain/enums.py tests/integration/test_log_retention_flow.py tests/integration/test_trace_audit_logs.py
git commit -m "feat: add runtime raw query retention"
```

### Task 6: Scoped Audit, Key Summary, And Runtime Metrics APIs

**Files:**

- Create: `src/intent_routing/ops/metrics.py`
- Create: `tests/unit/test_ops_metrics.py`
- Create: `tests/integration/test_ops_metrics_api.py`
- Modify: `src/intent_routing/api/admin.py`
- Modify: `src/intent_routing/db/repositories.py`

- [ ] **Step 1: Write failing API tests**

Cover access rules:

- scoped `auditor` can list audit logs and raw-text key summary for its service,
- scoped `auditor` cannot read another service,
- scoped `service_operator` can read runtime metrics,
- `service_developer` cannot read key summary or audit logs,
- responses do not include ciphertext, encrypted DEKs, raw query, raw example text, bearer tokens, or KEK base64.

Run:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:55432/intent_routing_task6_metrics uv run pytest tests/integration/test_ops_metrics_api.py -v
```

Expected: fail because endpoints do not exist.

- [ ] **Step 2: Implement runtime metrics aggregation**

Metric response shape:

```json
{
  "service_id": "it-helpdesk-pilot",
  "window_hours": 24,
  "request_count": 120,
  "decision_counts": {
    "confident": 80,
    "clarify": 12,
    "fallback": 10,
    "off_topic": 8,
    "risk": 5,
    "unauthorized": 5
  },
  "error_counts": {
    "AUTHENTICATION_FAILED": 2
  },
  "latency_ms": {
    "p50": 24,
    "p95": 80,
    "max": 141
  },
  "top_route_keys": [
    {"route_key": "it.api_timeout.manual_lookup", "count": 44}
  ],
  "raw_query_retention": {
    "encrypted_count": 100,
    "redacted_count": 20
  }
}
```

Implementation notes:

- use PostgreSQL aggregate SQL for counts and percentiles,
- return zero counts and `null` latency percentiles when there are no rows,
- filter by `service_id` and `created_at >= now() - window_hours`.

- [ ] **Step 3: Implement audit log listing**

Endpoint:

```http
GET /admin/v1/services/{service_id}/audit-logs?limit=50&event_type=raw_query.viewed&trace_id=irt-abc
```

Response item:

```json
{
  "audit_id": "uuid",
  "event_type": "raw_query.viewed",
  "actor_id": "auditor-user",
  "service_id": "it-helpdesk-pilot",
  "trace_id": "irt-abc",
  "target_type": "runtime_log",
  "target_id": "irt-abc",
  "view_reason": "approval=SEC-20260628-001; reason=장애 분석 ticket INC-20260628-001",
  "source_ip": "127.0.0.1",
  "created_at": "2026-06-28T00:00:00Z"
}
```

Do not return `before_state` or `after_state` from this endpoint in Sprint 3.

- [ ] **Step 4: Implement raw-text key summary**

Endpoint:

```http
GET /admin/v1/services/{service_id}/security/raw-text-key-summary
```

Response:

```json
{
  "service_id": "it-helpdesk-pilot",
  "active_key_id": "pilot-kek-20260628-002",
  "intent_examples": [
    {"key_id": "pilot-kek-20260628-002", "count": 30}
  ],
  "runtime_logs": [
    {"key_id": "pilot-kek-20260628-002", "count": 20},
    {"key_id": null, "count": 5, "state": "raw_query_redacted"}
  ]
}
```

The endpoint must not validate legacy key material or decrypt records. It only counts stored key IDs.

- [ ] **Step 5: Run focused tests**

```bash
uv run pytest tests/unit/test_ops_metrics.py -v
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:55432/intent_routing_task6_metrics uv run pytest tests/integration/test_ops_metrics_api.py -v
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/intent_routing/ops/metrics.py src/intent_routing/api/admin.py src/intent_routing/db/repositories.py tests/unit/test_ops_metrics.py tests/integration/test_ops_metrics_api.py
git commit -m "feat: add operations security APIs"
```

### Task 7: Operations Evidence Export And Security Lifecycle Docs

**Files:**

- Create: `src/intent_routing/ops/evidence.py`
- Create: `scripts/export_ops_evidence.py`
- Create: `docs/ops/security-lifecycle.md`
- Create: `tests/unit/test_ops_evidence.py`
- Create: `tests/unit/test_security_lifecycle_docs_contract.py`
- Create: `tests/integration/test_ops_evidence_export.py`
- Modify: `docs/ops/security-operations.md`
- Modify: `docs/ops/closed-network-deployment.md`
- Modify: `docs/ops/pilot-readiness-evidence.md`
- Modify: `README.md`
- Modify: `tests/unit/test_security_ops_docs_contract.py`
- Modify: `tests/unit/test_operator_docs_contract.py`

- [ ] **Step 1: Write failing evidence renderer tests**

Test that JSON and Markdown evidence:

- include service ID, active release, readyz status, runtime metrics, audit count, raw-text key summary, latest rewrap run IDs, retention redaction count,
- redact secret-looking fields recursively,
- omit `query_raw`, `text_raw`, `Authorization`, `RAW_TEXT_KEK_BASE64`, `irt_secret`, and legacy KEK base64 values.

Run:

```bash
uv run pytest tests/unit/test_ops_evidence.py tests/unit/test_security_lifecycle_docs_contract.py -v
```

Expected: fail because evidence and docs do not exist.

- [ ] **Step 2: Implement evidence rendering**

Public functions:

```text
render_ops_evidence_json(payload: Mapping[str, Any]) -> str
render_ops_evidence_markdown(payload: Mapping[str, Any]) -> str
```

Markdown sections:

```text
# Intent Routing Operations Evidence
## Service
## Readiness
## Runtime Metrics
## Raw Text Key Summary
## KEK Rewrap Runs
## Runtime Raw-Query Retention
## Audit Evidence
## Secret Redaction Statement
```

- [ ] **Step 3: Implement export CLI**

Arguments:

```text
--base-url http://127.0.0.1:8000
--admin-token ${ADMIN_BOOTSTRAP_TOKEN}
--service-id ${SERVICE_ID}
--out-dir var/evidence/${SERVICE_ID}/ops
--window-hours 24
--actor-id ops-evidence
```

Behavior:

- calls `/readyz`,
- calls active release endpoint,
- calls runtime metrics endpoint,
- calls raw-text key summary endpoint,
- calls audit log endpoint for security lifecycle events,
- reads latest rewrap run summaries from the admin API if a rewrap run listing endpoint was added; otherwise reads the `raw_text_rewrap_runs` table through repository using `DATABASE_URL`,
- writes `ops-evidence.json` and `ops-evidence.md`.

- [ ] **Step 4: Update docs**

`docs/ops/security-lifecycle.md` must include:

- KEK rotation prerequisites,
- how to set active and legacy KEK env values,
- dry-run command,
- execute command,
- post-rewrap validation using raw-text key summary,
- raw-query retention dry-run and execute commands,
- metrics/evidence export commands,
- rollback procedure before and after rewrap,
- secret leak checks.

Update `docs/ops/security-operations.md` by replacing the Sprint 2 limitation text with a pointer to the Sprint 3 KEK rewrap workflow. Keep explicit warnings that base64 KEKs must only live in the approved secret manager or deployment secret channel.

- [ ] **Step 5: Run focused tests**

```bash
uv run pytest tests/unit/test_ops_evidence.py tests/unit/test_security_lifecycle_docs_contract.py tests/unit/test_security_ops_docs_contract.py tests/unit/test_operator_docs_contract.py -v
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:55432/intent_routing_task7_evidence uv run pytest tests/integration/test_ops_evidence_export.py -v
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/intent_routing/ops/evidence.py scripts/export_ops_evidence.py docs/ops/security-lifecycle.md docs/ops/security-operations.md docs/ops/closed-network-deployment.md docs/ops/pilot-readiness-evidence.md README.md tests/unit/test_ops_evidence.py tests/unit/test_security_lifecycle_docs_contract.py tests/unit/test_security_ops_docs_contract.py tests/unit/test_operator_docs_contract.py tests/integration/test_ops_evidence_export.py
git commit -m "docs: add operations evidence workflow"
```

### Task 8: Final Verification And Manual Pilot Acceptance

**Files:**

- Modify: `docs/superpowers/plans/2026-06-28-intent-routing-sprint-3.md` only if implementation discovers a plan correction that needs to be recorded.

- [ ] **Step 1: Run static checks**

```bash
uv run ruff check .
uv run mypy src tests
docker compose --profile runtime config
```

Expected: all pass.

- [ ] **Step 2: Run focused Sprint 3 tests**

```bash
uv run pytest tests/unit/test_security_keyring.py tests/unit/test_raw_text_rewrap.py tests/unit/test_log_retention.py tests/unit/test_ops_metrics.py tests/unit/test_ops_evidence.py tests/unit/test_security_lifecycle_docs_contract.py -v
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:55432/intent_routing_sprint3 uv run pytest tests/integration/test_raw_text_rewrap_flow.py tests/integration/test_log_retention_flow.py tests/integration/test_ops_metrics_api.py tests/integration/test_ops_evidence_export.py -v
```

Expected: all pass.

- [ ] **Step 3: Run full regression**

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:55432/intent_routing_sprint3 uv run pytest -v
```

Expected: all tests pass. Existing Starlette/httpx and Alembic path separator deprecation warnings may remain unless separately fixed.

- [ ] **Step 4: Run manual closed-network-style smoke**

Use a fresh service ID and local fake embeddings:

```bash
export DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:5432/intent_routing
export INTENT_ROUTING_ENVIRONMENT=dev
export ADMIN_BOOTSTRAP_TOKEN=local-admin-token
export RAW_TEXT_KEK_ID=pilot-kek-20260628-001
export RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
export RAW_TEXT_LEGACY_KEKS_JSON={}
export EMBEDDING_PROVIDER=fake
export SERVICE_ID=it-helpdesk-pilot-$(date +%Y%m%d%H%M%S)
export STATE_PATH="var/pilot/${SERVICE_ID}.state.secret.json"
```

Start stack:

```bash
docker compose down -v
docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000
```

Seed and generate evidence baseline:

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

- [ ] **Step 5: Manually verify KEK rewrap**

Simulate rotation by moving the old active key into legacy JSON and setting a new active key:

```bash
export RAW_TEXT_LEGACY_KEKS_JSON='{"pilot-kek-20260628-001":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="}'
export RAW_TEXT_KEK_ID=pilot-kek-20260628-002
export RAW_TEXT_KEK_BASE64=MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE=
```

Dry-run:

```bash
uv run python scripts/rewrap_raw_text.py \
  --service-id ${SERVICE_ID} \
  --actor-id security-operator \
  --include both \
  --report-dir var/evidence/${SERVICE_ID}/security \
  --dry-run
```

Execute:

```bash
uv run python scripts/rewrap_raw_text.py \
  --service-id ${SERVICE_ID} \
  --actor-id security-operator \
  --include both \
  --report-dir var/evidence/${SERVICE_ID}/security \
  --execute \
  --approval-id SEC-20260628-REWRAP-001 \
  --confirm-active-key-id pilot-kek-20260628-002
```

Verify key summary:

```bash
curl -s \
  -H "X-Admin-Token: ${ADMIN_BOOTSTRAP_TOKEN}" \
  -H "X-Actor-Id: auditor-user" \
  -H "X-Actor-Roles: auditor" \
  -H "X-Service-Scope: ${SERVICE_ID}" \
  "http://127.0.0.1:8000/admin/v1/services/${SERVICE_ID}/security/raw-text-key-summary"
```

Expected: non-redacted encrypted records use `pilot-kek-20260628-002`.

- [ ] **Step 6: Manually verify retention**

Dry-run:

```bash
uv run python scripts/apply_log_retention.py \
  --service-id ${SERVICE_ID} \
  --older-than-days 0 \
  --limit 50 \
  --actor-id security-operator \
  --reason "raw query retention policy 0 days for Sprint 3 acceptance" \
  --report-dir var/evidence/${SERVICE_ID}/security \
  --dry-run
```

Execute:

```bash
uv run python scripts/apply_log_retention.py \
  --service-id ${SERVICE_ID} \
  --older-than-days 0 \
  --limit 50 \
  --actor-id security-operator \
  --reason "raw query retention policy 0 days for Sprint 3 acceptance" \
  --report-dir var/evidence/${SERVICE_ID}/security \
  --execute \
  --approval-id SEC-20260628-RETENTION-001
```

Expected:

- masked runtime logs remain listed,
- raw query decrypt returns HTTP 410 `RAW_QUERY_UNAVAILABLE`,
- audit logs contain `runtime_log.raw_query_redacted`,
- retention reports contain no raw query text.

- [ ] **Step 7: Export operations evidence and run secret leak check**

```bash
uv run python scripts/export_ops_evidence.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --out-dir var/evidence/${SERVICE_ID}/ops \
  --window-hours 24 \
  --actor-id ops-evidence
```

Secret leak check:

```bash
rg "RAW_TEXT_KEK_BASE64|AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=|MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE=|Authorization: Bearer|irt_secret|query_raw|text_raw" var/evidence/${SERVICE_ID}
```

Expected: no matches in non-secret evidence files. The `.secret.json` state file under `var/pilot` is allowed to contain the runtime API key and must remain outside evidence reports.

- [ ] **Step 8: Commit final verification/docs touch-ups**

```bash
git status --short
git add docs/superpowers/plans/2026-06-28-intent-routing-sprint-3.md
git commit -m "docs: add sprint 3 security lifecycle plan"
```

Skip this commit if the plan was already committed before implementation execution.

## Test Strategy

Unit tests:

- Keyring env parsing and validation.
- Active encrypt plus legacy decrypt behavior.
- Re-encryption changes key ID and ciphertext while preserving plaintext.
- Re-encryption does not perform DEK-only mutation.
- Runtime raw-query retention plan and redaction payloads.
- Metrics aggregation formatting with empty and populated rows.
- Evidence rendering and recursive secret redaction.
- Docs contracts for security lifecycle, environment samples, and operator runbooks.

Integration tests:

- Legacy-encrypted examples and runtime logs rewrap to the active key.
- Rewrap dry-run writes no encrypted field changes.
- Rewrap execute requires approval ID and active key confirmation.
- Raw query redaction preserves masked runtime logs and blocks raw decrypt.
- Audit log listing respects scoped admin roles.
- Runtime metrics endpoint respects scoped admin roles and returns sanitized aggregates.
- Ops evidence export writes JSON/Markdown without secrets.
- Existing admin/runtime/release/pilot readiness flows still pass.

Manual smoke:

- Fresh DB pilot readiness still succeeds.
- API key rotation from Sprint 2 still succeeds after keyring changes.
- Raw query decrypt still succeeds before retention redaction and returns 410 after redaction.
- Rewrap reports and evidence reports pass secret leak checks.

## Acceptance Criteria

- Existing `RAW_TEXT_KEK_ID` and `RAW_TEXT_KEK_BASE64` deployments keep working without legacy JSON.
- Operators can configure legacy KEKs with `RAW_TEXT_LEGACY_KEKS_JSON` and decrypt old records during migration.
- `scripts/rewrap_raw_text.py` defaults to dry-run and requires approval ID plus active key confirmation for execute.
- Rewrap migrates both approved intent examples and runtime logs from old key IDs to the active key ID.
- Rewrap never writes raw plaintext to reports, audit logs, stdout, or runtime logs.
- Runtime raw-query retention redacts encrypted raw query fields while preserving masked operational logs.
- Raw query decrypt after retention returns standard error envelope with HTTP 410 and no `decision`.
- Audit log, key summary, and runtime metrics APIs enforce scoped admin roles.
- Operations evidence export produces non-secret JSON and Markdown artifacts.
- Updated docs explain KEK migration, retention, metrics, rollback, and secret leak checks without requiring source-code reading.
- `uv run ruff check .`, `uv run mypy src tests`, `docker compose --profile runtime config`, and full PostgreSQL-backed `pytest -v` pass.

## Implementation Order

Execute tasks in order:

1. Keyring first, because every later encryption/decryption path depends on it.
2. Rewrap primitives before schema and CLI, so table-specific update behavior is testable in isolation.
3. Schema/repository before operator workflows.
4. Rewrap CLI before retention, because retention may remove raw query material that can no longer be rewrapped.
5. Retention before metrics/evidence, because evidence should reflect redacted state.
6. Admin metrics/audit/key summary before evidence export.
7. Docs and final verification last.

Recommended checkpoints:

```text
Checkpoint A after Task 1: existing encryption/decryption tests still pass with keyring.
Checkpoint B after Task 4: KEK rewrap dry-run and execute work on fresh PostgreSQL.
Checkpoint C after Task 5: retained logs keep masked data and block raw decrypt.
Checkpoint D after Task 7: evidence package is secret-safe.
Checkpoint E after Task 8: full Sprint 0-3 regression is green.
```

## Manual Review Checklist

- [ ] Confirm Sprint 3 did not change routing decisions or threshold preset values.
- [ ] Confirm no report contains raw query text, raw example text, API keys, bearer headers, or KEK material.
- [ ] Confirm rewrap reports include key IDs and counts only.
- [ ] Confirm `raw_query.viewed` is only written when raw query is actually returned.
- [ ] Confirm `runtime_log.raw_query_redacted` is written when retention redacts encrypted raw query fields.
- [ ] Confirm Dify branch playbook remains compatible with runtime response envelopes.
- [ ] Confirm closed-network docs still state that model downloads must not occur during image build, startup, benchmark, or runtime.

## Self-Review Notes

- Sprint 0/1/2 decisions remain intact: independent service, API-only MVP, Dify HTTP Request node, exact pgvector search, BGE-M3 CPU-only, threshold presets, CSV gate, service-specific off-topic, seven global risk types, API key auth, release-version operations, and error-envelope separation.
- The plan directly addresses the Sprint 2 documented KEK limitation.
- Runtime raw-query retention is scoped to runtime logs only to avoid weakening catalog/release reproducibility.
- Audit logs are queryable/exportable but not automatically deleted.
- The plan avoids broad IAM, UI, retrieval, and deployment platform expansion.
