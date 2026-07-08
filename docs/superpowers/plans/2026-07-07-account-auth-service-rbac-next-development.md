# Account Auth And Service RBAC Next Development Handoff

## Context

Account login and service-scoped RBAC are already merged as the first milestone
from `docs/adr/2026-07-06-account-auth-service-rbac-to-fine-grained-authorization.md`.
Build follow-up Admin UI work on the cookie session model:

- normal authentication: `irt_admin_session` HttpOnly cookie
- current user: `GET /admin/v1/auth/me`
- service scope: `GET /admin/v1/me/services`
- bootstrap only: `POST /admin/v1/auth/bootstrap-admin` with `X-Admin-Token`

Do not reintroduce normal Admin UI trusted-header auth. `X-Admin-Token`,
`X-Actor-Id`, `X-Actor-Roles`, and `X-Service-Scope` are reserved for bootstrap,
break-glass, or controlled internal automation paths.

## Related Plans

- Account/RBAC architecture:
  `docs/adr/2026-07-06-account-auth-service-rbac-to-fine-grained-authorization.md`
- Phase 1 Admin UI writes:
  `docs/superpowers/plans/2026-07-06-admin-ui-phase1-rbac-write-flows.md`
- Governed Phase 2 backend contracts:
  `docs/superpowers/plans/2026-07-06-phase2-governed-backend-contracts.md`

## Next Implementation Scope

1. Keep `frontend/intent-routing-console/src/services/authServices.ts` focused on
   `/auth/login`, `/auth/logout`, `/auth/me`, and `/me/services` with
   `withCredentials: true`.
2. Gate Phase 1 write pages from the server-derived roles in `adminSession`, not
   client-injected headers.
3. Use the existing Phase 1 service functions and tests in
   `frontend/intent-routing-console/src/services/adminServices.ts` and
   `frontend/intent-routing-console/src/services/adminServices.test.ts`.
4. Keep Phase 2 approval, raw-query, export, and live polling capabilities
   disabled or informational until their backend contracts are implemented.

## Verification Commands

```bash
cd frontend/intent-routing-console
corepack pnpm max setup
corepack pnpm test:unit -- src/services/authServices.test.ts
corepack pnpm test:unit -- src/models/adminSession.test.ts src/services/adminServices.test.ts
corepack pnpm typecheck

cd ../..
uv run pytest tests/unit/test_admin_auth_api_contract.py tests/integration/test_admin_account_auth_api.py tests/integration/test_admin_service_rbac_flow.py
rg -n "bootstrap-admin|irt_admin_session|/auth/login|/auth/me|/me/services|X-Admin-Token" docs/ops/intent-routing-local-runbook.md
```
