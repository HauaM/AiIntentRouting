# Startup System Admin Provisioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create or synchronize a `system_admin` account from environment variables when the backend application starts.

**Architecture:** Add a small startup provisioning service that reads explicit admin login environment variables, opens a DB session through the existing session factory, and applies an idempotent account upsert. The service does nothing when the environment variables are absent, creates a `system_admin` account when missing, updates the password when the configured password differs, and leaves the account untouched when it already matches.

**Tech Stack:** FastAPI lifespan startup hook, SQLAlchemy ORM repository pattern, existing `admin_users` / `admin_user_roles` tables, existing `hash_admin_password` and `verify_admin_password` helpers, pytest + FastAPI TestClient.

---

## Related Requirements And Specs

- `docs/adr/2026-07-06-account-auth-service-rbac-to-fine-grained-authorization.md`
  - Decision: account-based authentication and service-scoped RBAC.
  - Implementation note: `ADMIN_BOOTSTRAP_TOKEN` should be reduced to bootstrap or break-glass use.
- `docs/security/fine-grained-authorization-todo.md`
  - Future direction for account authorization and avoiding client-trusted actor headers.
- User requirement from 2026-07-08:
  - If `.env` has no admin id/password, do not create anything.
  - If `.env` has admin id/password, run startup provisioning.
  - If the id exists and password matches, stop.
  - If the id exists and password differs, update the password.
  - If no system administrator account exists for that id, create it.

## Terminology

- **Admin id:** The current schema has no separate username column. In this plan, admin id means the account email used by `/admin/v1/auth/login`.
- **System admin:** A row in `admin_users` plus a `system_admin` role row in `admin_user_roles`.
- **Provisioning:** Startup-time creation or synchronization of a local/configured account from trusted environment variables.
- **Idempotent:** Running the same startup logic repeatedly results in the same final database state without duplicate rows.

## Environment Contract

Use new backend-owned environment names instead of the local script-only `ADMIN_UI_*` names:

- `ADMIN_SYSTEM_ADMIN_EMAIL`
- `ADMIN_SYSTEM_ADMIN_PASSWORD`
- `ADMIN_SYSTEM_ADMIN_DISPLAY_NAME`

Rules:

- If both `ADMIN_SYSTEM_ADMIN_EMAIL` and `ADMIN_SYSTEM_ADMIN_PASSWORD` are absent or blank, provisioning is skipped.
- If exactly one of `ADMIN_SYSTEM_ADMIN_EMAIL` or `ADMIN_SYSTEM_ADMIN_PASSWORD` is present, app startup fails fast with a clear error. This prevents a misconfigured deployment from silently running without the intended admin account.
- `ADMIN_SYSTEM_ADMIN_PASSWORD` must satisfy the existing minimum password length used by `AdminAuthBootstrapRequest`: at least 8 characters.
- `ADMIN_SYSTEM_ADMIN_DISPLAY_NAME` is optional and defaults to the email local-part for new accounts.
- Do not log the configured password or password hash.

## File Structure

- Create: `src/intent_routing/security/admin_provisioning.py`
  - Owns env parsing and idempotent startup system admin provisioning.
  - Contains a pure configuration parser and a DB-backed provisioning function.
- Modify: `src/intent_routing/db/repositories.py`
  - Add `update_admin_user_password`.
  - Add `ensure_admin_user_role`.
- Modify: `src/intent_routing/main.py`
  - Register a FastAPI lifespan startup hook that invokes provisioning with `session_scope`.
- Modify: `.env.example`
  - Add commented examples only, so no account is created unless the operator explicitly sets values.
- Modify: `docs/ops/intent-routing-local-runbook.md`
  - Document backend startup provisioning variables.
- Modify: `scripts/run_local_dev_stack.sh`
  - Replace API-level bootstrap logic with the backend-owned startup env variables.
- Test: `tests/unit/test_admin_provisioning.py`
  - Unit tests for config parsing and idempotent provisioning behavior.
- Test: `tests/unit/test_env_contract.py`
  - Verify `.env.example` documents the variables as comments, not active defaults.
- Test: `tests/unit/test_local_dev_stack_script.py`
  - Verify local stack exports the new backend-owned variables.
- Test: `tests/integration/test_admin_account_auth_api.py`
  - Verify app startup creates/synchronizes the admin account and login succeeds.
- Create or update ADR: `docs/adr/2026-07-08-startup-system-admin-provisioning.md`
  - Record why startup provisioning is accepted and how it relates to bootstrap token reduction.

---

### Task 1: Record The Auth Decision

**Files:**
- Create: `docs/adr/2026-07-08-startup-system-admin-provisioning.md`

- [ ] **Step 1: Write the ADR**

Create `docs/adr/2026-07-08-startup-system-admin-provisioning.md`:

```markdown
# ADR: Startup System Admin Provisioning

## Status

Accepted

## Context

The Admin UI now uses account login and session cookies. Local and controlled
deployments still need a deterministic way to create the initial `system_admin`
without relying on browser-side trusted headers or a one-off manual API call.

The existing account auth ADR says `ADMIN_BOOTSTRAP_TOKEN` should be reduced to
bootstrap or break-glass use. Startup provisioning from explicitly configured
environment variables gives operators a repeatable bootstrap path while keeping
normal Admin UI access account based.

## Decision

When `ADMIN_SYSTEM_ADMIN_EMAIL` and `ADMIN_SYSTEM_ADMIN_PASSWORD` are both set,
the backend will create or synchronize that account during application startup.

If neither value is set, the backend does nothing.

If only one value is set, startup fails fast.

For an existing user with the same normalized email, the backend verifies the
configured password. If it matches, no password change is made. If it differs,
the backend replaces the stored password hash with a hash of the configured
password. The backend also ensures the user has the `system_admin` global role.

For a missing user, the backend creates an active admin user and assigns the
`system_admin` role.

## Alternatives Considered

### Option 1: Keep only `/admin/v1/auth/bootstrap-admin`

* Pros:
  * No startup DB writes.
  * Existing API behavior remains unchanged.
* Cons:
  * Fresh local databases still return 401 until an operator manually calls the
    bootstrap endpoint.
  * Scripts must carry account bootstrap behavior outside the application.

### Option 2: Local script bootstrap only

* Pros:
  * Works for local development.
  * Avoids production startup writes.
* Cons:
  * Does not help non-local deployments that run the backend directly.
  * Duplicates account creation logic outside the backend.

### Option 3: Backend startup provisioning from explicit env vars

* Pros:
  * One authoritative bootstrap path.
  * Idempotent across restarts.
  * Works for local and controlled deployments.
  * Reduces dependence on normal use of bootstrap token APIs.
* Cons:
  * Startup performs a DB write when configured.
  * Misconfigured production secrets could rotate a password unexpectedly.

## Consequences

Operators must treat `ADMIN_SYSTEM_ADMIN_PASSWORD` as a secret. Startup logs must
never include the password or hash.

Deployments that do not set the variables keep the current behavior.

Setting the variables becomes an intentional password synchronization mechanism:
changing the environment password changes the system admin password at next
startup.

## Implementation Notes

Use the existing `admin_users` and `admin_user_roles` tables. Do not add a
schema migration. Use the existing password hashing and verification helpers.

Use an advisory transaction lock to avoid duplicate creation when multiple app
workers start concurrently.

## Verification

Automated tests must prove:

* Missing env values skip provisioning.
* Partial env values fail.
* Missing user is created with `system_admin`.
* Existing user with matching password is unchanged.
* Existing user with different password receives a new password hash.
* Existing user without `system_admin` gets the role.
* Login succeeds after startup provisioning.

## Rollback Or Revisit Conditions

Revisit this decision if an external identity provider becomes mandatory, if
startup DB writes are disallowed in deployment policy, or if secret rotation must
be handled by a dedicated operator workflow instead of app startup.
```

- [ ] **Step 2: Verify the ADR exists and has required sections**

Run:

```bash
rg -n "## Status|## Context|## Decision|## Alternatives Considered|## Consequences|## Verification" docs/adr/2026-07-08-startup-system-admin-provisioning.md
```

Expected: all six headings are found.

- [ ] **Step 3: Commit**

```bash
git add docs/adr/2026-07-08-startup-system-admin-provisioning.md
git commit -m "docs: record startup admin provisioning decision"
```

---

### Task 2: Add Repository Helpers

**Files:**
- Modify: `src/intent_routing/db/repositories.py`
- Test: `tests/unit/test_account_auth_schema_contract.py`

- [ ] **Step 1: Write the failing repository contract test**

In `tests/unit/test_account_auth_schema_contract.py`, extend `test_repository_exposes_account_auth_helpers` so the expected method list includes:

```python
        "update_admin_user_password",
        "ensure_admin_user_role",
```

Add a new test below the existing repository flow test:

```python
def test_repository_updates_admin_password_and_ensures_role(db_session: Session) -> None:
    now = datetime.now(UTC)
    user_id = "admin-password-sync"
    repository = IntentRoutingRepository(db_session)

    db_session.execute(
        text("delete from admin_user_roles where user_id = :user_id"),
        {"user_id": user_id},
    )
    db_session.execute(
        text("delete from admin_users where user_id = :user_id"),
        {"user_id": user_id},
    )
    db_session.commit()

    try:
        user = repository.create_admin_user(
            user_id=user_id,
            email="password-sync@example.com",
            display_name="Password Sync",
            password_hash="old-password-hash",
            status="active",
            created_at=now,
            updated_at=now,
        )

        repository.update_admin_user_password(
            user,
            password_hash="new-password-hash",
            updated_at=now,
        )
        role = repository.ensure_admin_user_role(
            user_id=user_id,
            role="system_admin",
            assigned_by="startup-provisioning",
            assigned_at=now,
        )
        duplicate_role = repository.ensure_admin_user_role(
            user_id=user_id,
            role="system_admin",
            assigned_by="startup-provisioning",
            assigned_at=now,
        )
        db_session.commit()

        assert user.password_hash == "new-password-hash"
        assert user.updated_at == now
        assert role is duplicate_role
        assert [role.role for role in repository.list_admin_user_roles(user_id)] == [
            "system_admin"
        ]
    finally:
        db_session.execute(
            text("delete from admin_user_roles where user_id = :user_id"),
            {"user_id": user_id},
        )
        db_session.execute(
            text("delete from admin_users where user_id = :user_id"),
            {"user_id": user_id},
        )
        db_session.commit()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/unit/test_account_auth_schema_contract.py::test_repository_exposes_account_auth_helpers tests/unit/test_account_auth_schema_contract.py::test_repository_updates_admin_password_and_ensures_role -q
```

Expected: FAIL because `update_admin_user_password` and `ensure_admin_user_role` do not exist.

- [ ] **Step 3: Implement repository helpers**

In `src/intent_routing/db/repositories.py`, add `update_admin_user_password` after `update_admin_user_login`:

```python
    def update_admin_user_password(
        self,
        user: models.AdminUser,
        *,
        password_hash: str,
        updated_at: datetime,
    ) -> models.AdminUser:
        if not password_hash.strip():
            raise ValueError("admin user password_hash must not be blank")
        user.password_hash = password_hash
        user.updated_at = updated_at
        self.session.flush()
        return user
```

Add `ensure_admin_user_role` after `assign_admin_user_role`:

```python
    def ensure_admin_user_role(self, **values: Any) -> models.AdminUserRole:
        user_id = values.get("user_id")
        role = _require_allowed_value(
            values.get("role"),
            field_name="admin user role",
            allowed=GLOBAL_ADMIN_ROLES,
        )
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("admin user role user_id must be provided")
        existing = self.session.get(models.AdminUserRole, (user_id, role))
        if existing is not None:
            return existing
        return self.assign_admin_user_role(**values)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/unit/test_account_auth_schema_contract.py::test_repository_exposes_account_auth_helpers tests/unit/test_account_auth_schema_contract.py::test_repository_updates_admin_password_and_ensures_role -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/intent_routing/db/repositories.py tests/unit/test_account_auth_schema_contract.py
git commit -m "feat: add admin password sync repository helpers"
```

---

### Task 3: Add Startup Provisioning Service

**Files:**
- Create: `src/intent_routing/security/admin_provisioning.py`
- Test: `tests/unit/test_admin_provisioning.py`

- [ ] **Step 1: Write failing tests for config parsing**

Create `tests/unit/test_admin_provisioning.py`:

```python
from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.orm import Session

from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.security.admin_passwords import (
    hash_admin_password,
    verify_admin_password,
)
from intent_routing.security.admin_provisioning import (
    AdminProvisioningConfig,
    configure_startup_system_admin,
    load_admin_provisioning_config,
)


def test_load_admin_provisioning_config_skips_when_credentials_absent() -> None:
    assert (
        load_admin_provisioning_config(
            {
                "ADMIN_SYSTEM_ADMIN_EMAIL": "",
                "ADMIN_SYSTEM_ADMIN_PASSWORD": "",
            }
        )
        is None
    )


def test_load_admin_provisioning_config_rejects_partial_credentials() -> None:
    with pytest.raises(ValueError, match="both ADMIN_SYSTEM_ADMIN_EMAIL and ADMIN_SYSTEM_ADMIN_PASSWORD"):
        load_admin_provisioning_config({"ADMIN_SYSTEM_ADMIN_EMAIL": "admin@example.com"})


def test_load_admin_provisioning_config_requires_minimum_password_length() -> None:
    with pytest.raises(ValueError, match="at least 8 characters"):
        load_admin_provisioning_config(
            {
                "ADMIN_SYSTEM_ADMIN_EMAIL": "admin@example.com",
                "ADMIN_SYSTEM_ADMIN_PASSWORD": "short",
            }
        )


def test_load_admin_provisioning_config_defaults_display_name() -> None:
    config = load_admin_provisioning_config(
        {
            "ADMIN_SYSTEM_ADMIN_EMAIL": " Admin@Example.COM ",
            "ADMIN_SYSTEM_ADMIN_PASSWORD": "local-admin-password",
        }
    )

    assert config == AdminProvisioningConfig(
        email="Admin@Example.COM",
        password="local-admin-password",
        display_name="Admin",
    )
```

- [ ] **Step 2: Run config tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/test_admin_provisioning.py::test_load_admin_provisioning_config_skips_when_credentials_absent tests/unit/test_admin_provisioning.py::test_load_admin_provisioning_config_rejects_partial_credentials tests/unit/test_admin_provisioning.py::test_load_admin_provisioning_config_requires_minimum_password_length tests/unit/test_admin_provisioning.py::test_load_admin_provisioning_config_defaults_display_name -q
```

Expected: FAIL because `intent_routing.security.admin_provisioning` does not exist.

- [ ] **Step 3: Implement config parsing**

Create `src/intent_routing/security/admin_provisioning.py`:

```python
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from os import environ
from uuid import uuid4

from sqlalchemy.orm import Session

from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.security.admin_passwords import (
    hash_admin_password,
    verify_admin_password,
)


MIN_STARTUP_ADMIN_PASSWORD_LENGTH = 8
STARTUP_ADMIN_LOCK_KEY = "startup-system-admin-provisioning"


@dataclass(frozen=True, slots=True)
class AdminProvisioningConfig:
    email: str
    password: str
    display_name: str


def load_admin_provisioning_config(
    env: Mapping[str, str] | None = None,
) -> AdminProvisioningConfig | None:
    values = environ if env is None else env
    email = values.get("ADMIN_SYSTEM_ADMIN_EMAIL", "").strip()
    password = values.get("ADMIN_SYSTEM_ADMIN_PASSWORD", "")
    display_name = values.get("ADMIN_SYSTEM_ADMIN_DISPLAY_NAME", "").strip()

    if not email and not password:
        return None
    if not email or not password:
        raise ValueError(
            "both ADMIN_SYSTEM_ADMIN_EMAIL and ADMIN_SYSTEM_ADMIN_PASSWORD must be set"
        )
    if len(password) < MIN_STARTUP_ADMIN_PASSWORD_LENGTH:
        raise ValueError(
            "ADMIN_SYSTEM_ADMIN_PASSWORD must be at least 8 characters"
        )

    return AdminProvisioningConfig(
        email=email,
        password=password,
        display_name=display_name or email.split("@", 1)[0],
    )
```

- [ ] **Step 4: Run config tests to verify they pass**

Run:

```bash
uv run pytest tests/unit/test_admin_provisioning.py::test_load_admin_provisioning_config_skips_when_credentials_absent tests/unit/test_admin_provisioning.py::test_load_admin_provisioning_config_rejects_partial_credentials tests/unit/test_admin_provisioning.py::test_load_admin_provisioning_config_requires_minimum_password_length tests/unit/test_admin_provisioning.py::test_load_admin_provisioning_config_defaults_display_name -q
```

Expected: PASS.

- [ ] **Step 5: Add provisioning behavior tests**

Append to `tests/unit/test_admin_provisioning.py`:

```python
def _purge_admin(db_session: Session, email: str) -> None:
    repository = IntentRoutingRepository(db_session)
    existing = repository.get_admin_user_by_email(email)
    if existing is None:
        return
    db_session.execute(
        text("delete from admin_user_roles where user_id = :user_id"),
        {"user_id": existing.user_id},
    )
    db_session.execute(
        text("delete from admin_sessions where user_id = :user_id"),
        {"user_id": existing.user_id},
    )
    db_session.execute(
        text("delete from user_service_roles where user_id = :user_id"),
        {"user_id": existing.user_id},
    )
    db_session.execute(
        text("delete from admin_users where user_id = :user_id"),
        {"user_id": existing.user_id},
    )
    db_session.commit()
```

Also add the missing import near the top:

```python
from sqlalchemy import text
```

Add tests:

```python
def test_configure_startup_system_admin_creates_missing_admin(db_session: Session) -> None:
    email = "startup-create@example.com"
    _purge_admin(db_session, email)
    try:
        result = configure_startup_system_admin(
            lambda: _yield_session(db_session),
            env={
                "ADMIN_SYSTEM_ADMIN_EMAIL": email,
                "ADMIN_SYSTEM_ADMIN_PASSWORD": "local-admin-password",
                "ADMIN_SYSTEM_ADMIN_DISPLAY_NAME": "Startup Create",
            },
        )
        repository = IntentRoutingRepository(db_session)
        user = repository.get_admin_user_by_email(email)

        assert result == "created"
        assert user is not None
        assert user.email == email
        assert user.display_name == "Startup Create"
        assert user.status == "active"
        assert verify_admin_password("local-admin-password", user.password_hash)
        assert [role.role for role in repository.list_admin_user_roles(user.user_id)] == [
            "system_admin"
        ]
    finally:
        _purge_admin(db_session, email)


def test_configure_startup_system_admin_leaves_matching_admin_unchanged(
    db_session: Session,
) -> None:
    email = "startup-match@example.com"
    now = datetime.now(UTC)
    _purge_admin(db_session, email)
    try:
        repository = IntentRoutingRepository(db_session)
        user = repository.create_admin_user(
            user_id="startup-match-admin",
            email=email,
            display_name="Startup Match",
            password_hash=hash_admin_password("local-admin-password"),
            status="active",
            created_at=now,
            updated_at=now,
        )
        repository.assign_admin_user_role(
            user_id=user.user_id,
            role="system_admin",
            assigned_by="test",
            assigned_at=now,
        )
        original_hash = user.password_hash
        db_session.commit()

        result = configure_startup_system_admin(
            lambda: _yield_session(db_session),
            env={
                "ADMIN_SYSTEM_ADMIN_EMAIL": email,
                "ADMIN_SYSTEM_ADMIN_PASSWORD": "local-admin-password",
            },
        )

        assert result == "unchanged"
        assert user.password_hash == original_hash
        assert user.updated_at == now
    finally:
        _purge_admin(db_session, email)


def test_configure_startup_system_admin_updates_different_password(
    db_session: Session,
) -> None:
    email = "startup-update@example.com"
    now = datetime.now(UTC)
    _purge_admin(db_session, email)
    try:
        repository = IntentRoutingRepository(db_session)
        user = repository.create_admin_user(
            user_id="startup-update-admin",
            email=email,
            display_name="Startup Update",
            password_hash=hash_admin_password("old-admin-password"),
            status="active",
            created_at=now,
            updated_at=now,
        )
        repository.assign_admin_user_role(
            user_id=user.user_id,
            role="system_admin",
            assigned_by="test",
            assigned_at=now,
        )
        old_hash = user.password_hash
        db_session.commit()

        result = configure_startup_system_admin(
            lambda: _yield_session(db_session),
            env={
                "ADMIN_SYSTEM_ADMIN_EMAIL": email,
                "ADMIN_SYSTEM_ADMIN_PASSWORD": "new-admin-password",
            },
        )

        assert result == "updated"
        assert user.password_hash != old_hash
        assert verify_admin_password("new-admin-password", user.password_hash)
    finally:
        _purge_admin(db_session, email)


def test_configure_startup_system_admin_assigns_missing_system_admin_role(
    db_session: Session,
) -> None:
    email = "startup-role@example.com"
    now = datetime.now(UTC)
    _purge_admin(db_session, email)
    try:
        repository = IntentRoutingRepository(db_session)
        user = repository.create_admin_user(
            user_id="startup-role-admin",
            email=email,
            display_name="Startup Role",
            password_hash=hash_admin_password("local-admin-password"),
            status="active",
            created_at=now,
            updated_at=now,
        )
        db_session.commit()

        result = configure_startup_system_admin(
            lambda: _yield_session(db_session),
            env={
                "ADMIN_SYSTEM_ADMIN_EMAIL": email,
                "ADMIN_SYSTEM_ADMIN_PASSWORD": "local-admin-password",
            },
        )

        assert result == "role_assigned"
        assert [role.role for role in repository.list_admin_user_roles(user.user_id)] == [
            "system_admin"
        ]
    finally:
        _purge_admin(db_session, email)


def _yield_session(db_session: Session) -> Iterator[Session]:
    try:
        yield db_session
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise
```

- [ ] **Step 6: Run behavior tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/test_admin_provisioning.py -q
```

Expected: FAIL because `configure_startup_system_admin` is not implemented.

- [ ] **Step 7: Implement provisioning behavior**

Append to `src/intent_routing/security/admin_provisioning.py`:

```python
SessionScope = Callable[[], object]


def configure_startup_system_admin(
    session_scope_factory: Callable[[], object],
    *,
    env: Mapping[str, str] | None = None,
) -> str:
    config = load_admin_provisioning_config(env)
    if config is None:
        return "skipped"

    with session_scope_factory() as session:
        assert isinstance(session, Session)
        repository = IntentRoutingRepository(session)
        repository.acquire_advisory_xact_lock(STARTUP_ADMIN_LOCK_KEY)
        now = datetime.now(UTC)
        user = repository.get_admin_user_by_email(config.email)

        if user is None:
            user = repository.create_admin_user(
                user_id=f"admin_{uuid4().hex}",
                email=config.email,
                display_name=config.display_name,
                password_hash=hash_admin_password(config.password),
                status="active",
                created_at=now,
                updated_at=now,
            )
            repository.ensure_admin_user_role(
                user_id=user.user_id,
                role="system_admin",
                assigned_by="startup-provisioning",
                assigned_at=now,
            )
            return "created"

        has_matching_password = verify_admin_password(config.password, user.password_hash)
        roles_before = {role.role for role in repository.list_admin_user_roles(user.user_id)}
        if not has_matching_password:
            repository.update_admin_user_password(
                user,
                password_hash=hash_admin_password(config.password),
                updated_at=now,
            )
        repository.ensure_admin_user_role(
            user_id=user.user_id,
            role="system_admin",
            assigned_by="startup-provisioning",
            assigned_at=now,
        )

        if not has_matching_password:
            return "updated"
        if "system_admin" not in roles_before:
            return "role_assigned"
        return "unchanged"
```

- [ ] **Step 8: Run behavior tests to verify they pass**

Run:

```bash
uv run pytest tests/unit/test_admin_provisioning.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/intent_routing/security/admin_provisioning.py tests/unit/test_admin_provisioning.py
git commit -m "feat: provision startup system admin"
```

---

### Task 4: Wire Provisioning Into Backend Startup

**Files:**
- Modify: `src/intent_routing/main.py`
- Test: `tests/unit/test_admin_auth_api_contract.py`
- Test: `tests/integration/test_admin_account_auth_api.py`

- [ ] **Step 1: Write failing unit test for lifespan registration**

In `tests/unit/test_admin_auth_api_contract.py`, add:

```python
def test_app_startup_runs_system_admin_provisioning(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def fake_configure(session_scope_factory: object) -> str:
        calls.append(session_scope_factory)
        return "skipped"

    monkeypatch.setattr(
        "intent_routing.main.configure_startup_system_admin",
        fake_configure,
    )

    with TestClient(create_app()):
        pass

    assert len(calls) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/unit/test_admin_auth_api_contract.py::test_app_startup_runs_system_admin_provisioning -q
```

Expected: FAIL because `main.py` does not import or call `configure_startup_system_admin`.

- [ ] **Step 3: Wire startup hook in `main.py`**

Modify imports in `src/intent_routing/main.py`:

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
```

Add:

```python
from intent_routing.security.admin_provisioning import configure_startup_system_admin
```

Add above `create_app`:

```python
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_startup_system_admin(session_scope)
    yield
```

Change app construction:

```python
def create_app() -> FastAPI:
    app = FastAPI(title="Intent Routing Service", lifespan=lifespan)
```

- [ ] **Step 4: Run unit test to verify it passes**

Run:

```bash
uv run pytest tests/unit/test_admin_auth_api_contract.py::test_app_startup_runs_system_admin_provisioning -q
```

Expected: PASS.

- [ ] **Step 5: Write integration test for login after startup provisioning**

In `tests/integration/test_admin_account_auth_api.py`, add:

```python
def test_admin_startup_provisioning_creates_login_account(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = "startup-login@example.com"
    password = "startup-login-password"

    _purge_account_auth_rows(db_session, user_id="unused", service_id="unused")
    db_session.execute(
        text("delete from admin_user_roles where user_id in (select user_id from admin_users where email_normalized = :email)"),
        {"email": email.lower()},
    )
    db_session.execute(
        text("delete from admin_users where email_normalized = :email"),
        {"email": email.lower()},
    )
    db_session.commit()

    monkeypatch.setenv("ADMIN_SYSTEM_ADMIN_EMAIL", email)
    monkeypatch.setenv("ADMIN_SYSTEM_ADMIN_PASSWORD", password)
    monkeypatch.setenv("ADMIN_SYSTEM_ADMIN_DISPLAY_NAME", "Startup Login")

    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session

    try:
        with TestClient(app) as client:
            response = client.post(
                "/admin/v1/auth/login",
                json={"email": email, "password": password},
            )

        assert response.status_code == 200
        assert response.json()["user"]["email"] == email
        assert response.json()["global_roles"] == ["system_admin"]
    finally:
        db_session.execute(
            text("delete from admin_user_roles where user_id in (select user_id from admin_users where email_normalized = :email)"),
            {"email": email.lower()},
        )
        db_session.execute(
            text("delete from admin_users where email_normalized = :email"),
            {"email": email.lower()},
        )
        db_session.commit()
```

- [ ] **Step 6: Run integration test**

Run:

```bash
uv run pytest tests/integration/test_admin_account_auth_api.py::test_admin_startup_provisioning_creates_login_account -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/intent_routing/main.py tests/unit/test_admin_auth_api_contract.py tests/integration/test_admin_account_auth_api.py
git commit -m "feat: run admin provisioning at startup"
```

---

### Task 5: Update Environment, Docs, And Local Stack

**Files:**
- Modify: `.env.example`
- Modify: `docs/ops/intent-routing-local-runbook.md`
- Modify: `scripts/run_local_dev_stack.sh`
- Modify: `tests/unit/test_env_contract.py`
- Modify: `tests/unit/test_local_dev_stack_script.py`

- [ ] **Step 1: Update `.env.example` with commented variables**

Append to `.env.example`:

```dotenv
# Optional startup system admin provisioning.
# Leave commented/empty to skip account creation.
# ADMIN_SYSTEM_ADMIN_EMAIL=local-admin@example.com
# ADMIN_SYSTEM_ADMIN_PASSWORD=local-admin-password
# ADMIN_SYSTEM_ADMIN_DISPLAY_NAME=Local Admin
```

- [ ] **Step 2: Update env contract test**

In `tests/unit/test_env_contract.py`, add assertions to `test_env_example_uses_runtime_local_defaults`:

```python
    assert "# ADMIN_SYSTEM_ADMIN_EMAIL=local-admin@example.com" in text
    assert "# ADMIN_SYSTEM_ADMIN_PASSWORD=local-admin-password" in text
    assert "# ADMIN_SYSTEM_ADMIN_DISPLAY_NAME=Local Admin" in text
    assert "ADMIN_SYSTEM_ADMIN_EMAIL" not in values
    assert "ADMIN_SYSTEM_ADMIN_PASSWORD" not in values
```

- [ ] **Step 3: Update local stack script**

In `scripts/run_local_dev_stack.sh`, replace:

```bash
export ADMIN_UI_EMAIL="${ADMIN_UI_EMAIL:-local-admin@example.com}"
export ADMIN_UI_PASSWORD="${ADMIN_UI_PASSWORD:-local-admin-password}"
export ADMIN_UI_DISPLAY_NAME="${ADMIN_UI_DISPLAY_NAME:-Local Admin}"
```

with:

```bash
export ADMIN_SYSTEM_ADMIN_EMAIL="${ADMIN_SYSTEM_ADMIN_EMAIL:-local-admin@example.com}"
export ADMIN_SYSTEM_ADMIN_PASSWORD="${ADMIN_SYSTEM_ADMIN_PASSWORD:-local-admin-password}"
export ADMIN_SYSTEM_ADMIN_DISPLAY_NAME="${ADMIN_SYSTEM_ADMIN_DISPLAY_NAME:-Local Admin}"
```

Remove `admin_auth_payload`, `admin_login_status`, and `bootstrap_local_admin_account` functions because backend startup owns provisioning.

Remove this call from `main()`:

```bash
  bootstrap_local_admin_account
```

The local stack should still display the login account after backend readiness:

```bash
  log "Admin UI login account is configured: ${ADMIN_SYSTEM_ADMIN_EMAIL}"
```

- [ ] **Step 4: Update local stack tests**

In `tests/unit/test_local_dev_stack_script.py`, replace checks for `ADMIN_UI_EMAIL`, `ADMIN_UI_PASSWORD`, and `bootstrap_local_admin_account` with:

```python
    assert (
        'ADMIN_SYSTEM_ADMIN_EMAIL="${ADMIN_SYSTEM_ADMIN_EMAIL:-local-admin@example.com}"'
        in text
    )
    assert (
        'ADMIN_SYSTEM_ADMIN_PASSWORD="${ADMIN_SYSTEM_ADMIN_PASSWORD:-local-admin-password}"'
        in text
    )
    assert (
        'ADMIN_SYSTEM_ADMIN_DISPLAY_NAME="${ADMIN_SYSTEM_ADMIN_DISPLAY_NAME:-Local Admin}"'
        in text
    )
    assert "bootstrap_local_admin_account" not in text
    assert "/admin/v1/auth/bootstrap-admin" not in text
```

Remove `test_local_dev_stack_bootstraps_local_login_account`.

- [ ] **Step 5: Update local runbook**

In `docs/ops/intent-routing-local-runbook.md`, replace the default login note with:

```markdown
- Admin login: `local-admin@example.com` / `local-admin-password` from startup provisioning variables
```

Add:

```markdown
The script exports `ADMIN_SYSTEM_ADMIN_EMAIL`, `ADMIN_SYSTEM_ADMIN_PASSWORD`,
and `ADMIN_SYSTEM_ADMIN_DISPLAY_NAME` so the backend creates or synchronizes the
local `system_admin` during startup. In non-local deployments, omit those
variables to skip startup account creation.
```

- [ ] **Step 6: Run docs and script tests**

Run:

```bash
uv run pytest tests/unit/test_env_contract.py tests/unit/test_local_dev_stack_script.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add .env.example docs/ops/intent-routing-local-runbook.md scripts/run_local_dev_stack.sh tests/unit/test_env_contract.py tests/unit/test_local_dev_stack_script.py
git commit -m "docs: document startup admin provisioning"
```

---

### Task 6: Final Verification And PR

**Files:**
- No additional source files unless tests reveal issues.

- [ ] **Step 1: Run targeted backend auth tests**

Run:

```bash
uv run pytest tests/unit/test_admin_provisioning.py tests/unit/test_admin_auth_api_contract.py tests/unit/test_account_auth_schema_contract.py tests/integration/test_admin_account_auth_api.py -q
```

Expected: PASS.

- [ ] **Step 2: Run environment and local stack contract tests**

Run:

```bash
uv run pytest tests/unit/test_env_contract.py tests/unit/test_local_dev_stack_script.py -q
```

Expected: PASS.

- [ ] **Step 3: Run static checks**

Run:

```bash
uv run ruff check src/intent_routing/security/admin_provisioning.py src/intent_routing/db/repositories.py src/intent_routing/main.py tests/unit/test_admin_provisioning.py tests/unit/test_admin_auth_api_contract.py tests/unit/test_account_auth_schema_contract.py tests/integration/test_admin_account_auth_api.py
uv run mypy src tests
```

Expected: both commands pass.

- [ ] **Step 4: Manually verify local startup login**

Run:

```bash
./scripts/run_local_dev_stack.sh
```

In another shell:

```bash
tmp_cookie="$(mktemp)"
curl -sS -o /tmp/admin-login.json -w '%{http_code}\n' -c "${tmp_cookie}" \
  -X POST http://127.0.0.1:30141/admin/v1/auth/login \
  -H 'Content-Type: application/json' \
  --data '{"email":"local-admin@example.com","password":"local-admin-password"}'
curl -sS -o /tmp/admin-me.json -w '%{http_code}\n' -b "${tmp_cookie}" \
  http://127.0.0.1:30141/admin/v1/auth/me
rm -f "${tmp_cookie}" /tmp/admin-login.json /tmp/admin-me.json
```

Expected:

```text
200
200
```

- [ ] **Step 5: Open PR**

```bash
git status --short
git push -u origin <branch-name>
gh pr create --draft --base main --head <branch-name> --title "[codex] Provision startup system admin" --body-file <pr-body-file>
```

PR body must include:

```markdown
## Summary
- Adds backend startup system admin provisioning from explicit environment variables.
- Synchronizes existing account password when the configured password changes.
- Moves local dev account bootstrap ownership from the shell script into backend startup.

## Verification
- `uv run pytest tests/unit/test_admin_provisioning.py tests/unit/test_admin_auth_api_contract.py tests/unit/test_account_auth_schema_contract.py tests/integration/test_admin_account_auth_api.py -q`
- `uv run pytest tests/unit/test_env_contract.py tests/unit/test_local_dev_stack_script.py -q`
- `uv run ruff check ...`
- `uv run mypy src tests`
- Manual local login smoke returned `200` for `/auth/login` and `/auth/me`
```

---

## Self-Review Checklist

- [ ] User flow 1 is covered: absent env values return `"skipped"` and do not create an account.
- [ ] User flow 2 is covered: present env values run provisioning at backend startup.
- [ ] User flow 2-1 is covered: existing account lookup uses normalized email.
- [ ] User flow 2-1-1 is covered: matching password returns `"unchanged"`.
- [ ] User flow 2-1-2 is covered: mismatched password updates password hash.
- [ ] User flow 2-2 is covered: missing account creates active `system_admin`.
- [ ] The plan does not log or expose password values.
- [ ] The plan adds no database migration because existing tables already support the feature.
- [ ] The local dev script no longer duplicates account bootstrap API logic.
