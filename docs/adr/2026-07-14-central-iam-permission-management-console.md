# ADR: Central IAM Permission Management Console

## Status

Accepted

## Context

The Admin Console now separates organization directory records from Admin
login accounts:

- `users` and `departments` describe organization people and departments.
- `admin_users` describes Admin Console login accounts.
- `admin_user_roles` stores global Admin roles such as `system_admin`.
- `user_service_roles` stores Service-scoped roles such as `service_owner`,
  `service_developer`, `service_operator`, and `auditor`.
- `audit_logs` stores append-only evidence for Admin and Service operations.

The current organization user edit modal can show and manage the Admin account
linked to one organization user. That is useful for point-in-time user
maintenance, but it does not answer operational IAM questions such as:

- Who currently has Admin Console access?
- Who currently has `system_admin`?
- Which Admin users hold Service-scoped roles?
- Which permission changes happened recently?
- Are there risky states such as an inactive organization user linked to an
  active Admin account?

The existing C-2 Service membership decision deliberately placed first Service
role assignment controls near the selected Service workflow. The product now
needs a central permission management area for cross-user, cross-Service, and
audit-oriented operations while preserving the existing Service membership
API contracts and ADR separation between organization users and Admin accounts.

## Decision

Introduce a central IAM-style Permission Management console as the long-term
home for Admin account, global role, Service role, permission history, and
permission risk review workflows.

The console must keep the existing data ownership model:

```text
departments
  -> users
    -> admin_users
      -> admin_user_roles
      -> user_service_roles
      -> audit_logs
```

The console must not make `users` an authorization source. It must continue to
derive access from `admin_users`, `admin_user_roles`, and `user_service_roles`.

The first implementation should be incremental:

1. Add a Permission Management page and summary APIs for `system_admin`.
2. Show Admin accounts, global roles, linked organization user metadata, and
   Admin permission audit history.
3. Add Service role visibility and grant/revoke actions using the existing
   Service membership model.
4. Add read-only risk findings derived from existing tables.
5. Review application admin registration requests and approve them as
   `system_admin`.

Permission Management remains `system_admin` only. `application_admin` can be
reviewed there as a pending access request, but it must not gain Permission
Management access itself.

The existing user edit modal may keep a compact Admin Access section, but the
central console becomes the canonical place for full permission operations and
history review.

## Alternatives Considered

### Option 1: Keep Permission Management Inside Users & Departments

* Pros:
  * Smaller navigation change.
  * Keeps organization user maintenance and linked Admin account maintenance in
    one place.
* Cons:
  * Mixes directory ownership with authorization ownership.
  * Operators must inspect individual users to understand global access state.
  * The Users & Departments page becomes dense and less focused.

### Option 2: Add A Narrow Admin Account Page

* Pros:
  * Fastest way to list `admin_users` and `system_admin` assignments.
  * Low risk for the existing Service membership flow.
* Cons:
  * Does not solve cross-Service role visibility.
  * Leaves permission audit history split between global and Service screens.
  * Becomes a stepping stone that is likely to be replaced by a broader IAM
    console.

### Option 3: Central IAM Permission Management Console

* Pros:
  * Gives operators a single place to answer who has which access.
  * Fits financial audit needs by pairing current permissions with change
    history.
  * Preserves the existing table separation while improving visibility.
  * Can grow toward future fine-grained authorization without moving pages
    again.
* Cons:
  * Larger UI and API scope.
  * Needs careful role gates so `system_admin` remains the only baseline
    permission-management writer.
  * Requires additional tests around global audit visibility and cross-Service
    permission summaries.

## Consequences

The Admin UI will have both workflow-local controls and central IAM controls:

- `/services` remains the selected-Service workflow surface.
- `/organization-directory` remains the organization directory surface.
- `/permission-management` becomes the central IAM and audit surface.

The first central IAM APIs should be `system_admin` only. Existing Service
membership endpoints can continue to enforce the existing C-2 rules. Owner
delegation remains a separate future decision.

The audit model remains append-only. The new console may show sanitized audit
metadata, but it must not expose password hashes, session tokens, API secrets,
or raw before/after state that has not been explicitly reviewed for UI safety.

No schema migration is required for the first implementation if all summaries
and risk findings are derived from existing tables. A schema change should be
considered only if future requirements add temporal permission snapshots,
approval workflows, role expiry, teams, or policy inheritance.

## Implementation Notes

Expected first routes:

```text
GET /admin/v1/permission-management/admin-users
GET /admin/v1/permission-management/service-roles
GET /admin/v1/permission-management/audit-logs
GET /admin/v1/permission-management/risk-findings
```

Expected frontend route:

```text
/permission-management
```

Expected tabs:

```text
Admin 계정
전역 권한
서비스 권한
권한 변경 이력
운영 점검
```

The page should use Admin UI v04 patterns: `AdminShell`, ProComponents,
Umi `request`, server-derived session roles, compact tables, and
`ConfirmActionButton` for dangerous mutations.

## Verification

The decision is valid only if tests prove:

- `system_admin` can access central IAM summaries.
- Non-`system_admin` users cannot access central IAM summary or write APIs.
- Admin account summaries include linked organization user metadata without
  adding authorization fields to `users`.
- Service role summaries reflect `user_service_roles`.
- Permission history includes `admin_user.*` and `service_membership.*` audit
  events.
- Dangerous actions still protect the current user's last active
  `system_admin` grant.
- Normal browser Admin UI requests use the session cookie and do not send
  trusted actor headers or `Authorization: Bearer`.

## Rollback Or Revisit Conditions

Revisit this decision if:

- The central IAM page duplicates so much of `/services` that operators cannot
  tell where to perform Service role changes.
- Owner delegation becomes mandatory before the central IAM baseline ships.
- Fine-grained authorization requires new resource-level or environment-level
  storage.
- Security review rejects cross-Service audit visibility for all
  `system_admin` users.
