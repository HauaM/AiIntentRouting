# Encrypted API Key Secret Reveal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an authorized `system_admin` or selected-Service `service_owner` copy the actual runtime API secret from API Keys after initial issuance, while storing only encrypted secret material in the database and preserving auditability.

**Architecture:** Keep `api_keys.key_hash` and `api_keys.key_fingerprint` as the runtime authentication source. Add nullable AES-256-GCM envelope-encrypted secret columns to `api_keys`; new keys persist encrypted secret material, legacy keys without encrypted material cannot be revealed and must be rotated. Add a service-scoped reveal endpoint that decrypts only on explicit user action, returns the secret in that single response, and writes an audit event with no raw secret.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic v2, existing `intent_routing.security.encryption.EncryptedText`, Umi `request`, React, Ant Design, Vitest, pytest.

## Global Constraints

- Do not store raw API key secrets in plaintext in DB, logs, audit state, docs, screenshots, or committed files.
- Use AES-256-GCM envelope encryption via the existing encryption primitives.
- Keep runtime authentication based on hash verification; runtime must not decrypt API key secrets.
- Normal Admin UI browser requests use `irt_admin_session` and Umi `request`; do not send trusted actor headers or browser Bearer auth from Admin UI.
- Reveal is available only to `system_admin` or selected-Service `service_owner` with API key management access.
- `service_developer`, `service_operator`, and `auditor` cannot reveal API secrets.
- Inventory, revoke, runtime setup guidance, audit logs, runtime logs, and exports must not include raw `api_key`.
- Existing keys created before this migration have no recoverable raw secret; reveal returns a clear unavailable response and operators must rotate/reissue.
- Supported runtime environments remain `dev`, `qa`, and `prod`.
- Current worktree note: there is UI-only WIP around `oneTimeApiSecretForSelectedKey`; replace it with reveal API behavior instead of preserving page-scoped secret copy.

---

## File Structure

- Create `docs/adr/2026-07-21-encrypted-api-key-secret-reveal.md`: accepted ADR that supersedes the C-3 one-time-secret-only rule.
- Modify `docs/adr/2026-07-09-admin-ui-c3-runtime-integration-and-api-key-scope.md`: reference the new ADR and remove absolute “never returned after create” wording where it conflicts.
- Modify `docs/api/admin-runtime-setup-contracts.md`: add `POST /admin/v1/services/{service_id}/api-keys/{key_id}:reveal`.
- Modify `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`, `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`, and `docs/AdminUI_Handbook/v04/E2E_DX_QA_CHECKLIST.md`: document reveal as explicit audited API key management action.
- Modify `docs/THEME_AND_UX_GUIDE_v1.md`: replace the stale absolute raw-secret redisplay ban with the new encrypted reveal rule.
- Modify `.env.example`, `.env.closed-network.example`, `tests/unit/test_env_contract.py`: add API-key secret KEK configuration.
- Modify `src/intent_routing/config.py`: add API-key secret keyring config loader.
- Create `src/intent_routing/security/api_key_secrets.py`: translate `ApiKey` encrypted columns to/from `EncryptedText` and load the keyring.
- Modify `src/intent_routing/db/models.py`: add nullable encrypted secret columns to `ApiKey`.
- Create `alembic/versions/0013_api_key_encrypted_secret.py`: schema migration.
- Modify `src/intent_routing/api/admin.py`: encrypt at create time, add reveal response model and endpoint, audit reveals.
- Modify `frontend/intent-routing-console/src/services/adminServices.ts`: add reveal API client.
- Modify `frontend/intent-routing-console/src/types/api.d.ts`: add reveal response type.
- Modify `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`: replace static Authorization copy with reveal-and-copy action.
- Modify `frontend/intent-routing-console/src/pages/ApiKeys/runtimeSetup.ts`: remove page-scoped one-time copy override once reveal API is wired.
- Modify/add tests listed in each task.

---

### Task 1: ADR And Contract Update

**Files:**
- Create: `docs/adr/2026-07-21-encrypted-api-key-secret-reveal.md`
- Modify: `docs/adr/2026-07-09-admin-ui-c3-runtime-integration-and-api-key-scope.md`
- Modify: `docs/api/admin-runtime-setup-contracts.md`
- Modify: `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`
- Modify: `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`
- Modify: `docs/AdminUI_Handbook/v04/E2E_DX_QA_CHECKLIST.md`
- Modify: `docs/THEME_AND_UX_GUIDE_v1.md`
- Test: `tests/unit/test_admin_runtime_setup_contract_docs.py`
- Test: `tests/unit/test_admin_ui_handbook_docs_contract.py`

**Interfaces:**
- Produces: accepted contract for `POST /admin/v1/services/{service_id}/api-keys/{key_id}:reveal`.
- Produces response shape:

```json
{
  "key_id": "key_live_012345",
  "service_id": "it-helpdesk",
  "environment": "prod",
  "app_id": "dify-platform",
  "api_key": "irt_<decrypted-secret>",
  "authorization_header": "Bearer irt_<decrypted-secret>",
  "api_key_revealed": true
}
```

- Produces audit event name: `api_key.secret_revealed`.

- [ ] **Step 1: Write failing docs contract tests**

Add assertions to `tests/unit/test_admin_runtime_setup_contract_docs.py`:

```python
def test_api_key_secret_reveal_contract_is_documented() -> None:
    text = _read(CONTRACT)

    for phrase in (
        "POST /admin/v1/services/{service_id}/api-keys/{key_id}:reveal",
        "encrypted secret material",
        "api_key.secret_revealed",
        "api_key_revealed",
        "authorization_header",
        "Legacy keys without encrypted secret material cannot be revealed",
        "Inventory, revoke, runtime setup guidance, audit logs, runtime logs, and exports never include raw `api_key`.",
    ):
        assert phrase in text
```

Add assertions to `tests/unit/test_admin_ui_handbook_docs_contract.py`:

```python
def test_admin_ui_v04_records_audited_api_key_secret_reveal() -> None:
    pattern_kit = _read(V04 / "PATTERN_KIT.md")
    onboarding = _read(V04 / "ONBOARDING_FLOW.md")
    checklist = _read(V04 / "E2E_DX_QA_CHECKLIST.md")
    theme = _read(ROOT / "docs/THEME_AND_UX_GUIDE_v1.md")
    text = f"{pattern_kit}\n{onboarding}\n{checklist}\n{theme}"

    for phrase in (
        "Secret 보기/복사",
        "POST /admin/v1/services/{service_id}/api-keys/{key_id}:reveal",
        "api_key.secret_revealed",
        "encrypted secret material",
        "raw secret is copied only through the audited reveal endpoint",
    ):
        assert phrase in text
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run pytest tests/unit/test_admin_runtime_setup_contract_docs.py tests/unit/test_admin_ui_handbook_docs_contract.py -q
```

Expected: fail because the reveal endpoint and docs are not documented yet.

- [ ] **Step 3: Create the ADR**

Create `docs/adr/2026-07-21-encrypted-api-key-secret-reveal.md` with:

```markdown
# ADR: Encrypted API Key Secret Reveal

## Status

Accepted

## Context

The API Keys page must allow an authorized Service owner to copy the actual runtime API secret after initial issuance. The previous C-3 baseline showed raw API secrets only once and stored only hash/fingerprint metadata, which prevented later copying from Runtime setup guidance.

## Decision

Persist API key secrets as AES-256-GCM envelope-encrypted secret material in `api_keys` while retaining hash/fingerprint fields for runtime authentication. Add an explicit audited service-scoped reveal endpoint for `system_admin` and selected-Service `service_owner`. Runtime setup guidance remains metadata/template-only and does not embed the raw secret.

## Alternatives Considered

### Option 1: Keep One-Time Secret Only

* Pros: lowest secret exposure.
* Cons: does not satisfy service_owner copy workflow after issuance.

### Option 2: Store Plaintext Secret

* Pros: simplest reveal implementation.
* Cons: unacceptable database compromise impact and conflicts with project security posture.

### Option 3: Store Encrypted Secret And Reveal On Explicit Action

* Pros: supports the workflow, avoids plaintext persistence, keeps audit evidence.
* Cons: requires KEK management, migration, reveal authorization, and rewrap planning.

## Consequences

New API keys can be revealed by authorized owners. Legacy keys without encrypted secret columns cannot be recovered. Reveal events become sensitive audit events. Runtime auth remains hash-based and does not decrypt secrets.

## Implementation Notes

Use nullable encrypted secret columns on `api_keys` with the same envelope shape as raw text fields. Add API-key-specific KEK configuration. The reveal endpoint returns the raw secret only in the response body and writes audit state with `api_key` redacted.

## Verification

Verify with docs contract tests, migration/model tests, backend integration tests for create/reveal/revoke, frontend service tests, API Keys page contract tests, mypy, ruff, TypeScript, and targeted Vitest.

## Rollback or Revisit Conditions

Revisit if security review disallows decryptable API secrets, KEK rotation cannot be operated safely, or audit evidence is insufficient.
```

- [ ] **Step 4: Update existing docs**

In `docs/adr/2026-07-09-admin-ui-c3-runtime-integration-and-api-key-scope.md`, replace the absolute one-time-only sentence with a pointer to the new ADR:

```markdown
The raw API key secret is displayed on create. After
`docs/adr/2026-07-21-encrypted-api-key-secret-reveal.md`, authorized
`system_admin` and selected-Service `service_owner` users may explicitly
reveal/copy the encrypted secret through an audited service-scoped endpoint.
Inventory, revoke, runtime setup guidance, audit logs, runtime logs, and
exports still never embed raw `api_key`.
```

In `docs/api/admin-runtime-setup-contracts.md`, add a section after revoke:

```markdown
### POST /admin/v1/services/{service_id}/api-keys/{key_id}:reveal

Decrypts the stored encrypted API key secret for explicit copy by an authorized
`system_admin` or selected-Service `service_owner`.

Response:

```json
{
  "key_id": "key_live_012345",
  "service_id": "it-helpdesk",
  "environment": "prod",
  "app_id": "dify-platform",
  "api_key": "irt_<decrypted-secret>",
  "authorization_header": "Bearer irt_<decrypted-secret>",
  "api_key_revealed": true
}
```

Rules:

- The endpoint requires API key management access for `{service_id}`.
- The key must belong to `{service_id}`.
- Revoked or expired keys cannot be revealed.
- Legacy keys without encrypted secret material cannot be revealed.
- The response is the only place where the reveal API returns raw `api_key`.
- Inventory, revoke, runtime setup guidance, audit logs, runtime logs, and exports never include raw `api_key`.
- Each successful reveal writes `api_key.secret_revealed` with redacted audit state.
```

In `docs/THEME_AND_UX_GUIDE_v1.md`, replace the stale API Keys rule with:

```markdown
- **API Keys** — secret is shown in the creation-success modal and may later be copied only through the explicit audited `Secret 보기/복사` reveal action. Inventory, revoke, runtime setup guidance, Audit Logs, Runtime Logs, and exports always show metadata or masked suffixes only, never raw `api_key`.
```

In `docs/AdminUI_Handbook/v04/E2E_DX_QA_CHECKLIST.md`, add an API Keys QA assertion near the existing key lifecycle checks:

```markdown
- [ ] Authorization의 `Secret 보기/복사`는 `POST /admin/v1/services/{service_id}/api-keys/{key_id}:reveal`을 호출하고 `Bearer irt_<decrypted-secret>`만 클립보드에 복사한다.
- [ ] Audit Logs에 `api_key.secret_revealed` event가 남고 audit state에는 raw `api_key`가 포함되지 않는다.
```

- [ ] **Step 5: Run docs tests and verify they pass**

Run:

```bash
uv run pytest tests/unit/test_admin_runtime_setup_contract_docs.py tests/unit/test_admin_ui_handbook_docs_contract.py -q
```

Expected: pass.

- [ ] **Step 6: Commit Task 1**

Create `/private/tmp/task1-api-key-secret-reveal-docs-commit.txt`:

```text
docs: record encrypted api key secret reveal contract

API key secret 재조회 요구사항을 ADR, Admin API 계약, Admin UI 핸드북, UX 가이드에 반영한다.
문서 계약 테스트를 추가하고 통과를 확인한다.
```

Run:

```bash
git add docs/adr/2026-07-21-encrypted-api-key-secret-reveal.md docs/adr/2026-07-09-admin-ui-c3-runtime-integration-and-api-key-scope.md docs/api/admin-runtime-setup-contracts.md docs/AdminUI_Handbook/v04/PATTERN_KIT.md docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md docs/AdminUI_Handbook/v04/E2E_DX_QA_CHECKLIST.md docs/THEME_AND_UX_GUIDE_v1.md tests/unit/test_admin_runtime_setup_contract_docs.py tests/unit/test_admin_ui_handbook_docs_contract.py
git commit -F /private/tmp/task1-api-key-secret-reveal-docs-commit.txt
git log -1 --pretty=format:%B
```

Expected: commit title is `docs: record encrypted api key secret reveal contract`.

---

### Task 2: API Key Secret KEK Configuration

**Files:**
- Modify: `src/intent_routing/config.py`
- Modify: `.env.example`
- Modify: `.env.closed-network.example`
- Test: `tests/unit/test_env_contract.py`

**Interfaces:**
- Produces: `ApiKeySecretKeyringConfig`
- Produces: `load_api_key_secret_keyring_config(environ: Mapping[str, str] | None = None) -> ApiKeySecretKeyringConfig`
- Environment keys:
  - `API_KEY_SECRET_KEK_ID`
  - `API_KEY_SECRET_KEK_BASE64`
  - `API_KEY_SECRET_LEGACY_KEKS_JSON`

- [ ] **Step 1: Write failing config tests**

Update `EXPECTED_LOCAL_ENV` in `tests/unit/test_env_contract.py`:

```python
EXPECTED_LOCAL_ENV["API_KEY_SECRET_KEK_ID"] = "local-api-key-secret-kek-001"
EXPECTED_LOCAL_ENV["API_KEY_SECRET_KEK_BASE64"] = (
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
)
EXPECTED_LOCAL_ENV["API_KEY_SECRET_LEGACY_KEKS_JSON"] = "{}"
```

Add:

```python
def test_api_key_secret_keyring_config_requires_kek(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("API_KEY_SECRET_KEK_BASE64", raising=False)

    from intent_routing.config import MissingApiKeySecretKekError, load_api_key_secret_keyring_config

    with pytest.raises(MissingApiKeySecretKekError):
        load_api_key_secret_keyring_config({})
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run pytest tests/unit/test_env_contract.py -q
```

Expected: fail because env keys and config loader do not exist.

- [ ] **Step 3: Implement config loader**

In `src/intent_routing/config.py`, add:

```python
DEFAULT_API_KEY_SECRET_KEK_ID = "local-api-key-secret-kek-001"


class ApiKeySecretKeyringConfigError(ValueError):
    pass


class MissingApiKeySecretKekError(ApiKeySecretKeyringConfigError):
    pass


@dataclass(frozen=True, slots=True)
class ApiKeySecretKeyringConfig:
    active_key_id: str
    active_kek_base64: str = field(repr=False)
    legacy_keks: dict[str, str] = field(default_factory=dict, repr=False)


def load_api_key_secret_keyring_config(
    environ: Mapping[str, str] | None = None,
) -> ApiKeySecretKeyringConfig:
    env = process_environ if environ is None else environ
    active_key_id = env.get(
        "API_KEY_SECRET_KEK_ID",
        DEFAULT_API_KEY_SECRET_KEK_ID,
    ).strip()
    if not active_key_id:
        raise ValueError("API_KEY_SECRET_KEK_ID must not be blank")
    active_kek_base64 = env.get("API_KEY_SECRET_KEK_BASE64")
    if active_kek_base64 is None or not active_kek_base64.strip():
        raise MissingApiKeySecretKekError("API_KEY_SECRET_KEK_BASE64 is required")
    legacy_keks = _parse_legacy_keks(env.get("API_KEY_SECRET_LEGACY_KEKS_JSON", "{}"))
    if active_key_id in legacy_keks:
        raise ValueError("active key_id must not appear in API_KEY_SECRET_LEGACY_KEKS_JSON")
    return ApiKeySecretKeyringConfig(
        active_key_id=active_key_id,
        active_kek_base64=active_kek_base64,
        legacy_keks=legacy_keks,
    )
```

- [ ] **Step 4: Update env examples**

Add to `.env.example`:

```dotenv
API_KEY_SECRET_KEK_ID=local-api-key-secret-kek-001
API_KEY_SECRET_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
API_KEY_SECRET_LEGACY_KEKS_JSON={}
```

Add to `.env.closed-network.example`:

```dotenv
API_KEY_SECRET_KEK_ID=replace-with-approved-api-key-secret-kek-id
API_KEY_SECRET_KEK_BASE64=replace-with-32-byte-base64-kek-from-approved-secret-store
API_KEY_SECRET_LEGACY_KEKS_JSON={}
```

- [ ] **Step 5: Run config tests**

Run:

```bash
uv run pytest tests/unit/test_env_contract.py -q
```

Expected: pass.

- [ ] **Step 6: Commit Task 2**

Create `/private/tmp/task2-api-key-secret-kek-config-commit.txt`:

```text
feat: add api key secret kek configuration

API key secret 암호화를 위한 KEK 설정과 환경 예시를 추가한다.
환경 계약 테스트로 로컬 및 폐쇄망 예시 값이 기대값과 일치하는지 검증한다.
```

Run:

```bash
git add src/intent_routing/config.py .env.example .env.closed-network.example tests/unit/test_env_contract.py
git commit -F /private/tmp/task2-api-key-secret-kek-config-commit.txt
git log -1 --pretty=format:%B
```

Expected: commit title is `feat: add api key secret kek configuration`.

---

### Task 3: Encrypted Secret Columns And Helpers

**Files:**
- Modify: `src/intent_routing/db/models.py`
- Create: `alembic/versions/0013_api_key_encrypted_secret.py`
- Create: `src/intent_routing/security/api_key_secrets.py`
- Test: `tests/unit/test_api_key_secret_encryption.py`
- Test: `tests/integration/test_release_flow.py`

**Interfaces:**
- Produces: nullable `ApiKey` fields:
  - `secret_ciphertext: bytes | None`
  - `secret_encrypted_dek: bytes | None`
  - `secret_encrypted_dek_iv: bytes | None`
  - `secret_encrypted_dek_auth_tag: bytes | None`
  - `secret_key_id: str | None`
  - `secret_iv: bytes | None`
  - `secret_auth_tag: bytes | None`
  - `secret_algorithm: str | None`
- Produces helpers:
  - `encrypted_api_key_secret(api_key: ApiKey) -> EncryptedText | None`
  - `apply_encrypted_api_key_secret(api_key: ApiKey, encrypted: EncryptedText) -> None`
  - `load_api_key_secret_keyring(environ: Mapping[str, str] | None = None) -> RawTextKeyring`

- [ ] **Step 1: Write failing helper test**

Create `tests/unit/test_api_key_secret_encryption.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from intent_routing.db import models
from intent_routing.security.api_key_secrets import (
    apply_encrypted_api_key_secret,
    encrypted_api_key_secret,
    load_api_key_secret_keyring,
)


def _api_key() -> models.ApiKey:
    now = datetime.now(UTC)
    return models.ApiKey(
        key_id="key_live_test",
        key_hash="hash",
        key_fingerprint="sha256:test:once",
        environment="dev",
        app_id="checkout-web",
        service_id="svc-a",
        allowed_intents=[],
        allowed_route_keys=[],
        status="active",
        expires_at=now + timedelta(days=1),
        revoked_at=None,
        created_by="admin-user",
        created_at=now,
    )


def test_api_key_secret_round_trips_through_envelope_columns() -> None:
    keyring = load_api_key_secret_keyring(
        {
            "API_KEY_SECRET_KEK_ID": "local-api-key-secret-kek-001",
            "API_KEY_SECRET_KEK_BASE64": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "API_KEY_SECRET_LEGACY_KEKS_JSON": "{}",
        }
    )
    api_key = _api_key()

    encrypted = keyring.encrypt_text("irt_secret_once")
    apply_encrypted_api_key_secret(api_key, encrypted)

    stored = encrypted_api_key_secret(api_key)
    assert stored is not None
    assert keyring.decrypt_text(stored) == "irt_secret_once"
    assert b"irt_secret_once" not in api_key.secret_ciphertext
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
uv run pytest tests/unit/test_api_key_secret_encryption.py -q
```

Expected: fail because fields/helpers do not exist.

- [ ] **Step 3: Add model columns**

Add fields to `ApiKey` in `src/intent_routing/db/models.py`:

```python
    secret_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    secret_encrypted_dek: Mapped[bytes | None] = mapped_column(LargeBinary)
    secret_encrypted_dek_iv: Mapped[bytes | None] = mapped_column(LargeBinary)
    secret_encrypted_dek_auth_tag: Mapped[bytes | None] = mapped_column(LargeBinary)
    secret_key_id: Mapped[str | None] = mapped_column(Text)
    secret_iv: Mapped[bytes | None] = mapped_column(LargeBinary)
    secret_auth_tag: Mapped[bytes | None] = mapped_column(LargeBinary)
    secret_algorithm: Mapped[str | None] = mapped_column(Text)
```

- [ ] **Step 4: Add migration**

Create `alembic/versions/0013_api_key_encrypted_secret.py`:

```python
"""store encrypted api key secrets

Revision ID: 0013_api_key_encrypted_secret
Revises: 0012_release_owned_environment
Create Date: 2026-07-21
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0013_api_key_encrypted_secret"
down_revision: str | None = "0012_release_owned_environment"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column("secret_ciphertext", sa.LargeBinary(), nullable=True))
    op.add_column("api_keys", sa.Column("secret_encrypted_dek", sa.LargeBinary(), nullable=True))
    op.add_column("api_keys", sa.Column("secret_encrypted_dek_iv", sa.LargeBinary(), nullable=True))
    op.add_column("api_keys", sa.Column("secret_encrypted_dek_auth_tag", sa.LargeBinary(), nullable=True))
    op.add_column("api_keys", sa.Column("secret_key_id", sa.Text(), nullable=True))
    op.add_column("api_keys", sa.Column("secret_iv", sa.LargeBinary(), nullable=True))
    op.add_column("api_keys", sa.Column("secret_auth_tag", sa.LargeBinary(), nullable=True))
    op.add_column("api_keys", sa.Column("secret_algorithm", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("api_keys", "secret_algorithm")
    op.drop_column("api_keys", "secret_auth_tag")
    op.drop_column("api_keys", "secret_iv")
    op.drop_column("api_keys", "secret_key_id")
    op.drop_column("api_keys", "secret_encrypted_dek_auth_tag")
    op.drop_column("api_keys", "secret_encrypted_dek_iv")
    op.drop_column("api_keys", "secret_encrypted_dek")
    op.drop_column("api_keys", "secret_ciphertext")
```

- [ ] **Step 5: Add helper module**

Create `src/intent_routing/security/api_key_secrets.py`:

```python
from __future__ import annotations

from collections.abc import Mapping

from intent_routing.config import load_api_key_secret_keyring_config
from intent_routing.db.models import ApiKey
from intent_routing.security.encryption import EncryptedText
from intent_routing.security.keyring import RawTextKeyring


def load_api_key_secret_keyring(
    environ: Mapping[str, str] | None = None,
) -> RawTextKeyring:
    config = load_api_key_secret_keyring_config(environ)
    return RawTextKeyring.from_values(
        active_key_id=config.active_key_id,
        active_kek_base64=config.active_kek_base64,
        legacy_keks=config.legacy_keks,
    )


def encrypted_api_key_secret(api_key: ApiKey) -> EncryptedText | None:
    if (
        api_key.secret_ciphertext is None
        or api_key.secret_encrypted_dek is None
        or api_key.secret_encrypted_dek_iv is None
        or api_key.secret_encrypted_dek_auth_tag is None
        or api_key.secret_key_id is None
        or api_key.secret_iv is None
        or api_key.secret_auth_tag is None
        or api_key.secret_algorithm is None
    ):
        return None
    return EncryptedText(
        ciphertext=api_key.secret_ciphertext,
        encrypted_dek=api_key.secret_encrypted_dek,
        encrypted_dek_iv=api_key.secret_encrypted_dek_iv,
        encrypted_dek_auth_tag=api_key.secret_encrypted_dek_auth_tag,
        key_id=api_key.secret_key_id,
        iv=api_key.secret_iv,
        auth_tag=api_key.secret_auth_tag,
        algorithm=api_key.secret_algorithm,
    )


def apply_encrypted_api_key_secret(api_key: ApiKey, encrypted: EncryptedText) -> None:
    api_key.secret_ciphertext = encrypted.ciphertext
    api_key.secret_encrypted_dek = encrypted.encrypted_dek
    api_key.secret_encrypted_dek_iv = encrypted.encrypted_dek_iv
    api_key.secret_encrypted_dek_auth_tag = encrypted.encrypted_dek_auth_tag
    api_key.secret_key_id = encrypted.key_id
    api_key.secret_iv = encrypted.iv
    api_key.secret_auth_tag = encrypted.auth_tag
    api_key.secret_algorithm = encrypted.algorithm
```

- [ ] **Step 6: Update schema contract test**

In `tests/integration/test_release_flow.py`, extend the encrypted column assertions for `api_keys`:

```python
expected_columns = {
    ("api_keys", "secret_ciphertext"): "bytea",
    ("api_keys", "secret_encrypted_dek"): "bytea",
    ("api_keys", "secret_encrypted_dek_iv"): "bytea",
    ("api_keys", "secret_encrypted_dek_auth_tag"): "bytea",
    ("api_keys", "secret_key_id"): "text",
    ("api_keys", "secret_iv"): "bytea",
    ("api_keys", "secret_auth_tag"): "bytea",
    ("api_keys", "secret_algorithm"): "text",
}
```

- [ ] **Step 7: Run tests**

Run:

```bash
uv run pytest tests/unit/test_api_key_secret_encryption.py tests/integration/test_release_flow.py::test_schema_contains_expected_tables_and_columns -q
```

Expected: pass.

- [ ] **Step 8: Commit Task 3**

Create `/private/tmp/task3-api-key-encrypted-secret-storage-commit.txt`:

```text
feat: store encrypted api key secrets

api_keys 테이블에 envelope 암호화 컬럼을 추가하고 모델, 마이그레이션, 변환 헬퍼를 구현한다.
단위 테스트와 스키마 계약 테스트로 암호화 round trip 및 DB 컬럼을 검증한다.
```

Run:

```bash
git add src/intent_routing/db/models.py alembic/versions/0013_api_key_encrypted_secret.py src/intent_routing/security/api_key_secrets.py tests/unit/test_api_key_secret_encryption.py tests/integration/test_release_flow.py
git commit -F /private/tmp/task3-api-key-encrypted-secret-storage-commit.txt
git log -1 --pretty=format:%B
```

Expected: commit title is `feat: store encrypted api key secrets`.

---

### Task 4: Backend Create And Reveal Endpoint

**Files:**
- Modify: `src/intent_routing/api/admin.py`
- Test: `tests/unit/test_admin_api_key_helpers.py`
- Test: `tests/integration/test_admin_runtime_setup_api.py`
- Test: `tests/integration/test_admin_api_key_inventory_flow.py`

**Interfaces:**
- Produces response model:

```python
class ApiKeyRevealResponse(BaseModel):
    key_id: str
    service_id: str
    environment: str
    app_id: str
    api_key: str
    authorization_header: str
    api_key_revealed: bool
```

- Produces endpoint:
  - `POST /admin/v1/services/{service_id}/api-keys/{key_id}:reveal`

- [ ] **Step 1: Write failing integration test for reveal success**

In `tests/integration/test_admin_runtime_setup_api.py`, add:

```python
def test_service_owner_can_reveal_encrypted_service_api_key_secret(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY_SECRET_KEK_ID", "local-api-key-secret-kek-001")
    monkeypatch.setenv("API_KEY_SECRET_KEK_BASE64", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
    monkeypatch.setenv("API_KEY_SECRET_LEGACY_KEKS_JSON", "{}")
    client, session_fixture = _system_admin_client(db_session)
    service_id = f"svc-runtime-reveal-{uuid4().hex}"
    try:
        _create_service(client, service_id)
        _seed_active_release(db_session, service_id)
        created = client.post(
            f"/admin/v1/services/{service_id}/api-keys",
            json=_api_key_payload(),
        )
        assert created.status_code == 201
        created_body = created.json()

        revealed = client.post(
            f"/admin/v1/services/{service_id}/api-keys/{created_body['key_id']}:reveal"
        )

        assert revealed.status_code == 200
        body = revealed.json()
        assert body["key_id"] == created_body["key_id"]
        assert body["service_id"] == service_id
        assert body["environment"] == "dev"
        assert body["app_id"] == "dify-helpdesk"
        assert body["api_key"] == created_body["api_key"]
        assert body["authorization_header"] == f"Bearer {created_body['api_key']}"
        assert body["api_key_revealed"] is True

        audit_log = db_session.scalar(
            select(models.AuditLog)
            .where(models.AuditLog.target_id == created_body["key_id"])
            .where(models.AuditLog.event_type == "api_key.secret_revealed")
        )
        assert audit_log is not None
        assert created_body["api_key"] not in json.dumps(
            {"before": audit_log.before_state, "after": audit_log.after_state},
            sort_keys=True,
        )
    finally:
        _purge_rows(db_session, service_ids=[service_id])
        _purge_session_fixture(db_session, session_fixture)
```

- [ ] **Step 2: Write failing tests for denied/unavailable reveal**

Add cases:

```python
def test_service_api_key_reveal_rejects_revoked_and_legacy_keys(db_session: Session) -> None:
    client, session_fixture = _system_admin_client(db_session)
    service_id = f"svc-runtime-reveal-denied-{uuid4().hex}"
    try:
        _create_service(client, service_id)
        legacy_key = IntentRoutingRepository(db_session).create_api_key(
            key_id=f"key_live_{uuid4().hex}",
            key_hash="legacy-hash",
            key_fingerprint="sha256:legacy:0000",
            environment="dev",
            app_id="legacy-app",
            service_id=service_id,
            allowed_intents=[],
            allowed_route_keys=[],
            status="active",
            expires_at=datetime.now(UTC) + timedelta(days=1),
            revoked_at=None,
            created_by="integration-test",
            created_at=datetime.now(UTC),
        )
        db_session.commit()

        unavailable = client.post(
            f"/admin/v1/services/{service_id}/api-keys/{legacy_key.key_id}:reveal"
        )
        assert unavailable.status_code == 409
        assert "encrypted secret" in unavailable.json()["error"]["message"].lower()

        legacy_key.status = "revoked"
        legacy_key.revoked_at = datetime.now(UTC)
        db_session.commit()
        revoked = client.post(
            f"/admin/v1/services/{service_id}/api-keys/{legacy_key.key_id}:reveal"
        )
        assert revoked.status_code == 400
        assert "revoked" in revoked.json()["error"]["message"].lower()
    finally:
        _purge_rows(db_session, service_ids=[service_id])
        _purge_session_fixture(db_session, session_fixture)
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```bash
uv run pytest tests/integration/test_admin_runtime_setup_api.py -q
```

Expected: fail because reveal endpoint and encrypted create storage do not exist.

- [ ] **Step 4: Encrypt secret at create time**

In `src/intent_routing/api/admin.py`, import helpers:

```python
from intent_routing.security.api_key_secrets import (
    apply_encrypted_api_key_secret,
    encrypted_api_key_secret,
    load_api_key_secret_keyring,
)
```

Update `_create_api_key_for_service`:

```python
def _create_api_key_for_service(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    environment: str,
    app_id: str,
    allowed_intents: list[str],
    allowed_route_keys: list[str],
    expires_in_days: int | None,
    actor_id: str,
    now: datetime,
) -> tuple[ApiKey, str]:
    api_key_secret = f"irt_{generate_api_key_secret()}"
    encrypted_secret = load_api_key_secret_keyring().encrypt_text(api_key_secret)
    api_key = repository.create_api_key(
        key_id=f"key_live_{uuid4().hex}",
        key_hash=hash_secret(api_key_secret),
        key_fingerprint=fingerprint_secret(api_key_secret),
        environment=environment,
        app_id=app_id,
        service_id=service_id,
        allowed_intents=allowed_intents,
        allowed_route_keys=allowed_route_keys,
        status=ApiKeyStatus.active.value,
        expires_at=(
            now + timedelta(days=expires_in_days)
            if expires_in_days is not None
            else None
        ),
        revoked_at=None,
        created_by=actor_id,
        created_at=now,
    )
    apply_encrypted_api_key_secret(api_key, encrypted_secret)
    repository.insert_audit_log(
        event_type="api_key.created",
        actor_id=actor_id,
        service_id=api_key.service_id,
        trace_id=None,
        target_type="api_key",
        target_id=api_key.key_id,
        view_reason=None,
        source_ip=None,
        before_state=None,
        after_state=_api_key_after_state(api_key),
        created_at=now,
    )
    return api_key, api_key_secret
```

Keep audit state redacted through `_api_key_after_state(api_key)`.

- [ ] **Step 5: Add reveal response and helper**

Add:

```python
class ApiKeyRevealResponse(BaseModel):
    key_id: str
    service_id: str
    environment: str
    app_id: str
    api_key: str
    authorization_header: str
    api_key_revealed: bool
```

Add helper:

```python
def _raise_if_api_key_not_revealable(api_key: ApiKey, now: datetime) -> None:
    if api_key.status == ApiKeyStatus.revoked.value or api_key.revoked_at is not None:
        _raise_bad_request("Revoked API key secrets cannot be revealed.")
    if api_key.expires_at is not None and api_key.expires_at <= now:
        _raise_bad_request("Expired API key secrets cannot be revealed.")
    if encrypted_api_key_secret(api_key) is None:
        _raise_conflict("API key secret is unavailable; rotate or reissue this legacy key.")
```

- [ ] **Step 6: Add reveal endpoint**

Add after `revoke_service_api_key`:

```python
@router.post(
    "/services/{service_id}/api-keys/{key_id}:reveal",
    response_model=ApiKeyRevealResponse,
)
def reveal_service_api_key(
    service_id: str,
    key_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
) -> ApiKeyRevealResponse:
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(session)
    service = repository.get_service(service_id)
    if service is None:
        _raise_not_found("Service does not exist.")
    _require_api_key_management_access(context, service_id)
    api_key = repository.get_api_key_by_id(key_id)
    if api_key is None:
        _raise_not_found("API key does not exist.")
    if api_key.service_id != service_id:
        raise_admin_forbidden("API key does not belong to the selected Service.")
    _raise_if_api_key_not_revealable(api_key, now)

    encrypted = encrypted_api_key_secret(api_key)
    if encrypted is None:
        _raise_conflict("API key secret is unavailable; rotate or reissue this legacy key.")
    api_key_secret = load_api_key_secret_keyring().decrypt_text(encrypted)
    repository.insert_audit_log(
        event_type="api_key.secret_revealed",
        actor_id=context.actor_id,
        service_id=service_id,
        trace_id=None,
        target_type="api_key",
        target_id=api_key.key_id,
        view_reason="runtime_setup_authorization_copy",
        source_ip=None,
        before_state=None,
        after_state=_api_key_reveal_audit_state(api_key),
        created_at=now,
    )
    session.commit()
    return ApiKeyRevealResponse(
        key_id=api_key.key_id,
        service_id=api_key.service_id,
        environment=api_key.environment,
        app_id=api_key.app_id,
        api_key=api_key_secret,
        authorization_header=f"Bearer {api_key_secret}",
        api_key_revealed=True,
    )
```

The reveal audit state must be metadata-only. Use a dedicated helper such as
`_api_key_reveal_audit_state(api_key)` and include only fields needed to explain
the event, for example `key_id`, `service_id`, `environment`, `app_id`, and
`status`. Do not include raw `api_key`, `authorization_header`, `key_hash`,
`key_fingerprint`, encrypted ciphertext, nonce, tag, or key version in the
secret-reveal audit payload.

- [ ] **Step 7: Run backend tests**

Run:

```bash
uv run pytest tests/unit/test_admin_api_key_helpers.py tests/unit/test_api_key_secret_encryption.py tests/integration/test_admin_runtime_setup_api.py tests/integration/test_admin_api_key_inventory_flow.py -q
```

Expected: pass.

- [ ] **Step 8: Commit Task 4**

Create `/private/tmp/task4-api-key-secret-reveal-endpoint-commit.txt`:

```text
feat: add audited api key secret reveal endpoint

API key 생성 시 secret을 암호화 저장하고 service-scoped reveal endpoint를 추가한다.
권한, revoked/expired/legacy key 처리, audit redaction을 통합 테스트로 검증한다.
```

Run:

```bash
git add src/intent_routing/api/admin.py tests/unit/test_admin_api_key_helpers.py tests/integration/test_admin_runtime_setup_api.py tests/integration/test_admin_api_key_inventory_flow.py
git commit -F /private/tmp/task4-api-key-secret-reveal-endpoint-commit.txt
git log -1 --pretty=format:%B
```

Expected: commit title is `feat: add audited api key secret reveal endpoint`.

---

### Task 5: Frontend Reveal Service And API Keys UI

**Files:**
- Modify: `frontend/intent-routing-console/src/services/adminServices.ts`
- Modify: `frontend/intent-routing-console/src/services/adminServices.test.ts`
- Modify: `frontend/intent-routing-console/src/types/api.d.ts`
- Modify: `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/ApiKeys/runtimeSetup.ts`
- Modify: `frontend/intent-routing-console/src/pages/ApiKeys/runtimeSetup.test.ts`

**Interfaces:**
- Produces: `revealServiceApiKey(serviceId: string, keyId: string): Promise<API.ApiKeyRevealResponse>`
- Produces UI behavior: Authorization row displays `Bearer {{intent_routing_api_key}}`, but its copy action calls reveal endpoint and copies `authorization_header`.

- [ ] **Step 1: Write failing frontend service test**

In `frontend/intent-routing-console/src/services/adminServices.test.ts`, import `revealServiceApiKey` and add to service-scoped lifecycle test:

```ts
await revealServiceApiKey('svc/admin', 'key/a');

expect(requestMock).toHaveBeenNthCalledWith(
  5,
  '/services/svc%2Fadmin/api-keys/key%2Fa:reveal',
  { method: 'POST' },
);
```

- [ ] **Step 2: Run service test and verify it fails**

Run:

```bash
cd frontend/intent-routing-console && ./node_modules/.bin/vitest run src/services/adminServices.test.ts
```

Expected: fail because `revealServiceApiKey` does not exist.

- [ ] **Step 3: Add type and service function**

In `frontend/intent-routing-console/src/types/api.d.ts`:

```ts
  type ApiKeyRevealResponse = {
    key_id: string;
    service_id: string;
    environment: string;
    app_id: string;
    api_key: string;
    authorization_header: string;
    api_key_revealed: boolean;
  };
```

In `frontend/intent-routing-console/src/services/adminServices.ts`:

```ts
export async function revealServiceApiKey(serviceId: string, keyId: string) {
  return request<API.ApiKeyRevealResponse>(
    servicePath(serviceId, `/api-keys/${encodeURIComponent(keyId)}:reveal`),
    { method: 'POST' },
  );
}
```

- [ ] **Step 4: Write failing API Keys page contract test**

In `frontend/intent-routing-console/src/pages/ApiKeys/runtimeSetup.test.ts`, replace the page-scoped one-time-secret assertions with reveal API assertions:

```ts
it('copies Authorization through the audited reveal endpoint instead of page-scoped secret replay', () => {
  const source = apiKeysPageSource();

  expect(source).toContain('revealServiceApiKey');
  expect(source).toContain('handleCopyHeader');
  expect(source).toContain("row.name.toLowerCase() === 'authorization'");
  expect(source).toContain('response.authorization_header');
  expect(source).toContain('navigator.clipboard.writeText');
  expect(source).toContain('Secret 보기/복사');
  expect(source).not.toContain('oneTimeApiSecretForSelectedKey');
});
```

- [ ] **Step 5: Run page test and verify it fails**

Run:

```bash
cd frontend/intent-routing-console && ./node_modules/.bin/vitest run src/pages/ApiKeys/runtimeSetup.test.ts
```

Expected: fail because UI still uses static copy/page-scoped WIP.

- [ ] **Step 6: Replace UI-only WIP with reveal action**

In `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`:

```ts
import { CopyOutlined } from '@ant-design/icons';
```

Use this services import block:

```ts
import {
  createServiceApiKey,
  fetchRuntimeSetupGuidance,
  listIntentRouteCandidates,
  listServiceApiKeys,
  revealServiceApiKey,
  revokeServiceApiKey,
} from '@/services/adminServices';
```

Remove:

```ts
oneTimeApiSecretForSelectedKey
createdKeyModalOpen
hideCreatedKeyModal
```

Keep `createdKey` for the create modal response, and clear it when the modal closes because reveal now works from DB.

Add:

```ts
const [revealingKeyId, setRevealingKeyId] = useState<string>();

const copyText = async (text: string) => {
  await navigator.clipboard.writeText(text);
};

const handleCopyHeader = async (row: RuntimeSetupHeaderRow) => {
  if (row.name.toLowerCase() !== 'authorization') {
    await copyText(row.value);
    message.success(`${row.name} 값이 복사되었습니다.`);
    return;
  }
  const keyId = runtimeSetup?.selected_key?.key_id;
  if (!keyId) {
    await copyText(row.value);
    message.info('선택된 key가 없어 템플릿 값을 복사했습니다.');
    return;
  }
  setRevealingKeyId(keyId);
  try {
    const response = await revealServiceApiKey(runtimeSetup.service_id, keyId);
    await copyText(response.authorization_header);
    message.success('Authorization header가 복사되었습니다.');
  } finally {
    setRevealingKeyId(undefined);
  }
};
```

Render header rows with explicit copy buttons instead of `Typography.Text copyable`:

```tsx
{runtimeSetupHeaderRows(runtimeSetup).map((row) => {
  const isAuthorization = row.name.toLowerCase() === 'authorization';
  return (
    <Descriptions.Item key={row.name} label={row.name}>
      <Space size={8} wrap>
        <Typography.Text code>{row.value}</Typography.Text>
        <Button
          size="small"
          icon={<CopyOutlined />}
          loading={isAuthorization && revealingKeyId === runtimeSetup.selected_key?.key_id}
          onClick={() => handleCopyHeader(row)}
        >
          {isAuthorization ? 'Secret 보기/복사' : '복사'}
        </Button>
      </Space>
    </Descriptions.Item>
  );
})}
```

- [ ] **Step 7: Run frontend tests**

Run:

```bash
cd frontend/intent-routing-console && ./node_modules/.bin/vitest run src/services/adminServices.test.ts src/pages/ApiKeys/runtimeSetup.test.ts src/pages/ApiKeys/apiKeyCreateFlow.test.ts src/components/intentRouteMultiSelectContract.test.ts
cd frontend/intent-routing-console && ./node_modules/.bin/tsc --noEmit
```

Expected: pass.

- [ ] **Step 8: Commit Task 5**

Create `/private/tmp/task5-api-key-secret-reveal-ui-commit.txt`:

```text
feat: copy api key authorization through reveal api

API Keys 화면에서 Authorization 복사를 audited reveal API 호출로 전환한다.
프론트엔드 서비스 테스트, API Keys 계약 테스트, TypeScript 검증을 수행한다.
```

Run:

```bash
git add frontend/intent-routing-console/src/services/adminServices.ts frontend/intent-routing-console/src/services/adminServices.test.ts frontend/intent-routing-console/src/types/api.d.ts frontend/intent-routing-console/src/pages/ApiKeys/index.tsx frontend/intent-routing-console/src/pages/ApiKeys/runtimeSetup.ts frontend/intent-routing-console/src/pages/ApiKeys/runtimeSetup.test.ts
git commit -F /private/tmp/task5-api-key-secret-reveal-ui-commit.txt
git log -1 --pretty=format:%B
```

Expected: commit title is `feat: copy api key authorization through reveal api`.

---

### Task 6: Verification And Guardrails

**Files:**
- No new production files unless previous tasks reveal an issue.
- Verify changed files only.

**Interfaces:**
- Produces: evidence that secret reveal works and no non-reveal response leaks `api_key`.

- [ ] **Step 1: Run backend checks**

Run:

```bash
uv run pytest tests/unit/test_env_contract.py tests/unit/test_admin_runtime_setup_contract_docs.py tests/unit/test_admin_ui_handbook_docs_contract.py tests/unit/test_api_key_secret_encryption.py tests/unit/test_admin_api_key_helpers.py tests/integration/test_admin_runtime_setup_api.py tests/integration/test_admin_api_key_inventory_flow.py -q
uv run mypy src tests
uv run ruff check .
```

Expected: pass. If DB integration skips locally because `TEST_DATABASE_URL` is unavailable, record the exact skip output and rely on CI for DB-backed proof.

- [ ] **Step 2: Run frontend checks**

Run:

```bash
cd frontend/intent-routing-console && ./node_modules/.bin/vitest run src/services/adminServices.test.ts src/pages/ApiKeys/runtimeSetup.test.ts src/pages/ApiKeys/apiKeyCreateFlow.test.ts src/components/intentRouteMultiSelectContract.test.ts
cd frontend/intent-routing-console && ./node_modules/.bin/tsc --noEmit
```

Expected: pass.

- [ ] **Step 3: Run secret and Admin UI guardrail searches**

Run:

```bash
rg -n "api_key.*audit|authorization_header|secret_revealed|revealServiceApiKey" src tests frontend/intent-routing-console/src docs
rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|server pagination|live polling" frontend/intent-routing-console/src/services/adminServices.ts frontend/intent-routing-console/src/pages/ApiKeys/index.tsx frontend/intent-routing-console/src/pages/ApiKeys/runtimeSetup.ts
rg -n "<Tag[^\\n]*\\bcolor=|darkAlgorithm|color-scheme:\\s*dark|background(-color)?\\s*:\\s*#0|background(-color)?\\s*:\\s*#1" frontend/intent-routing-console/src/pages/ApiKeys/index.tsx frontend/intent-routing-console/src/pages/ApiKeys/runtimeSetup.ts
git diff --check
```

Expected: no raw secret values, no forbidden Admin UI request patterns, no dark content surfaces, no whitespace errors.

- [ ] **Step 4: Manual QA scenario**

In a local DB-backed environment:

1. Start backend/admin UI with `API_KEY_SECRET_KEK_BASE64` configured.
2. Create or select a Service.
3. Activate a `dev` release.
4. Create an API key.
5. Close the create modal.
6. Go to `기존 키 관리`.
7. Select the key.
8. Click `Secret 보기/복사` next to Authorization.
9. Paste into a scratch buffer and confirm it starts with `Bearer irt_` and contains the decrypted secret value.
10. Query audit logs directly or through an authorized screen and confirm `api_key.secret_revealed` exists without the raw API secret value.
11. Revoke the key and confirm reveal returns a rejected response.

Expected: actual Authorization header can be copied only through the reveal action, and no non-reveal payload includes raw `api_key`.

- [ ] **Step 5: Close verification**

Task 6 is verification-only. If a verification failure requires changing files, return to the task that owns that file, apply the fix there, rerun that task's tests, and use that task's commit checkpoint. Do not create a generic verification commit.

Run:

```bash
git log --oneline -5
```

Expected: the five most recent commits correspond to Tasks 1 through 5, and no uncommitted implementation files remain.
