# Final Review Reactivation Fix Report

## Scope

Fixed the last final-review issue for the organization directory feature:
preventing organization-user reactivation inside an inactive department when
`PATCH /admin/v1/organization-users/{id}` omits `department_id`.

## Changes

1. Added a regression test that creates a department and user, deactivates the
   user, deactivates the department, then verifies `PATCH {"use_yn":"Y"}`
   returns `409 INVALID_REQUEST` and leaves the persisted user inactive.
2. Updated the organization-user patch handler to resolve the effective
   department from the request payload or the existing user record and require
   that department to be active before accepting `use_yn="Y"`.

## Verification

Focused regression file:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/integration/test_organization_directory_api.py -q
```

Result: `11 passed, 1 warning`

Backend bundle:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/unit/test_organization_directory_schema.py tests/unit/test_admin_auth_api_contract.py tests/integration/test_organization_directory_api.py tests/integration/test_admin_account_auth_api.py tests/unit/test_admin_sessions.py -q
```

Result: `54 passed, 1 skipped, 1 warning`

## Residual Risks

- The patch now validates reactivation against the effective department, but I
  did not broaden behavior beyond this final-review issue.
