# Task 6 Report

## Scope

Implemented Task 6 single-owner `system_admin` semantics for Application Admin:

- blocked generic admin-user patch from granting a second `system_admin`
- added an explicit `/admin/v1/system-admin-transfer` endpoint with atomic ownership transfer semantics
- updated startup provisioning to refuse a configured different owner email when a `system_admin` already exists
- aligned the startup provisioning ADR with the accepted single-owner policy
- added/updated tests to cover the new behaviors while respecting the shared single-owner test database

## Files Read

- `/home/haua/workspace/AiIntentRouting/.superpowers/sdd/2026-07-15-application-admin-task-6-brief.md`
- `/home/haua/workspace/AiIntentRouting/src/intent_routing/api/admin.py`
- `/home/haua/workspace/AiIntentRouting/src/intent_routing/security/admin_provisioning.py`
- `/home/haua/workspace/AiIntentRouting/src/intent_routing/db/repositories.py`
- `/home/haua/workspace/AiIntentRouting/tests/integration/test_admin_user_management_api.py`
- `/home/haua/workspace/AiIntentRouting/tests/integration/test_admin_account_auth_api.py`
- `/home/haua/workspace/AiIntentRouting/tests/unit/test_admin_provisioning.py`
- `/home/haua/workspace/AiIntentRouting/docs/adr/2026-07-08-startup-system-admin-provisioning.md`
- `/home/haua/workspace/AiIntentRouting/.superpowers/sdd/2026-07-15-application-admin-review-checklist-decision-log.md`
- superpowers skill docs used for process: `test-driven-development`, `using-superpowers`, and its Codex reference

## RED/GREEN Test Evidence

### RED

1. Command:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/integration/test_admin_user_management_api.py::test_cannot_grant_second_system_admin tests/integration/test_admin_user_management_api.py::test_system_admin_transfer_replaces_single_owner_atomically -q
```

Result:

- initial red run: `2 failed`
- first failure shape after test-isolation fix:
  - `test_cannot_grant_second_system_admin`: request raised existing repository `ValueError("system_admin already exists")` instead of returning API `409`
  - `test_system_admin_transfer_replaces_single_owner_atomically`: `404 Not Found` because the transfer endpoint did not exist yet

2. Command:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/unit/test_admin_provisioning.py::test_configure_startup_system_admin_refuses_different_email_when_owner_exists -q
```

Result:

- red run: `1 failed`
- failure shape: expected custom refusal message, got old behavior bubbling up as `ValueError("system_admin already exists")`

### GREEN

1. Command:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/integration/test_admin_user_management_api.py::test_cannot_grant_second_system_admin tests/integration/test_admin_user_management_api.py::test_system_admin_transfer_replaces_single_owner_atomically -q
```

Result:

- `2 passed, 1 warning in 1.89s`

2. Command:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/unit/test_admin_provisioning.py::test_configure_startup_system_admin_refuses_different_email_when_owner_exists -q
```

Result:

- `1 passed in 0.38s`

3. Required full task command:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/integration/test_admin_user_management_api.py tests/integration/test_admin_account_auth_api.py tests/unit/test_admin_provisioning.py -q
```

Result:

- `29 passed, 1 warning in 9.81s`

4. Pre-commit hygiene:

```bash
git diff --check
```

Result:

- no output, exit code `0`

## Changes Made

### `/home/haua/workspace/AiIntentRouting/src/intent_routing/api/admin.py`

- added `SystemAdminTransferRequest`
- added a conflict helper that returns `409` with `system_admin already exists. Use system_admin transfer.`
- updated generic admin-user patch to preflight `system_admin` grants and refuse second-owner promotion before partial mutation
- added `/admin/v1/system-admin-transfer`
  - requires current actor to be the current owner (`context.actor_id == from_admin_user_id`)
  - validates source has `system_admin`
  - validates target is active and already has `application_admin`
  - removes source `system_admin`
  - ensures source keeps `application_admin`
  - assigns target `system_admin`
  - removes target `application_admin`
  - audits `admin_user.system_admin_transferred`

### `/home/haua/workspace/AiIntentRouting/src/intent_routing/security/admin_provisioning.py`

- made startup provisioning explicitly check for an existing `system_admin`
- preserved first-owner create behavior when no owner exists
- preserved same-email password rotation / role sync behavior
- added refusal for a configured different email when another owner already exists

### `/home/haua/workspace/AiIntentRouting/tests/integration/test_admin_user_management_api.py`

- added `test_cannot_grant_second_system_admin`
- added `test_system_admin_transfer_replaces_single_owner_atomically`
- added test helpers that reuse or seed the canonical `system_admin` safely for the shared DB
- restored ownership state in transfer cleanup to avoid leaking extra owner rows across tests

### `/home/haua/workspace/AiIntentRouting/tests/unit/test_admin_provisioning.py`

- added refusal test for configured different-email startup provisioning
- updated the missing-role assignment test to reuse the canonical owner under the new single-owner policy

### `/home/haua/workspace/AiIntentRouting/docs/adr/2026-07-08-startup-system-admin-provisioning.md`

- updated the accepted ADR text to match the single-owner policy and refusal behavior

## Self-Review

- kept scope limited to Task 6 files plus the required ADR
- did not read `.env`
- did not stage or touch unrelated untracked files
- used `apply_patch` for manual edits
- verified the required targeted tests and the full Task 6 command
- checked `git diff --check` before commit preparation

## Concerns

- the transfer endpoint currently returns the target owner record only; that matches the current response-model choice, but callers needing both before/after records will have to read audit history or re-fetch the source user separately
- tests still emit the pre-existing `fastapi.testclient` deprecation warning from the environment; no Task 6 code change introduced it
