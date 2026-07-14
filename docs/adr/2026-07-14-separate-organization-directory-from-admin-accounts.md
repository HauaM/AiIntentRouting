# ADR: Separate Organization Directory From Admin Accounts

## Status

Accepted

## Context

The Admin Console already has account-based authentication and Service-scoped
RBAC. Existing access control uses:

- `admin_users` for login accounts.
- `admin_sessions` for authenticated browser sessions.
- `admin_user_roles` for global roles such as `system_admin`.
- `user_service_roles` for Service-scoped roles such as `service_developer`,
  `service_operator`, and `auditor`.

The next product need is to manage organization users and departments from the
Admin Console. Required organization user fields are:

- `id`
- `userNumber`
- `name`
- `useYn`

Required department fields are:

- `id`
- `deptNumber`
- `name`
- `useYn`

These fields describe the organization directory: employee number, Korean name,
department number, department name, and active/inactive state. They do not
describe login credentials, browser sessions, Service-scoped roles, API keys, or
audit actor identity.

The team explicitly considered whether to place administrator flags such as
`adminYn` on organization users. That approach would make the organization
directory a source of authorization, competing with the existing RBAC tables.

## Decision

Keep organization directory data separate from Admin Console account and
authorization data.

Add two organization master tables:

- `departments`
- `users`

Keep the existing Admin account tables for authentication and authorization:

- `admin_users`
- `admin_sessions`
- `admin_user_roles`
- `user_service_roles`

Link Admin accounts to organization users only when needed through a nullable
one-to-one relationship:

```text
admin_users.organization_user_id -> users.id
```

Do not add an authorization flag such as `users.admin_yn`. Authorization remains
derived from `admin_users`, `admin_user_roles`, and `user_service_roles`.

The conceptual ownership is:

```text
departments
  -> users
    -> admin_users
      -> admin_user_roles
      -> user_service_roles
```

`users.use_yn = 'N'` means the organization user is inactive. It is not itself a
role. If an inactive organization user is linked to an Admin account, normal
Admin authentication must deny access even if `admin_users.status` has not yet
been changed.

## Alternatives Considered

### Option 1: Separate Organization Directory And Admin Accounts

* Pros:
  * Keeps organization lifecycle separate from login and authorization
    lifecycle.
  * Allows many organization users to exist without Admin Console accounts.
  * Preserves the existing RBAC model as the only authorization source.
  * Supports future HR directory or SSO integration without merging unrelated
    concerns.
  * Makes audit actor identity stable through `admin_users.user_id` while still
    allowing department and employee metadata to be displayed.
* Cons:
  * Requires a nullable link between `admin_users` and `users`.
  * Requires UI copy to distinguish organization users from Admin accounts.

### Option 2: Extend `admin_users` With Organization Fields

* Pros:
  * Fewer tables at first.
  * Existing Service membership user search can keep using one table.
* Cons:
  * Makes every organization user look like a login account.
  * Mixes employee lifecycle with password, session, and RBAC lifecycle.
  * Makes future SSO or HR synchronization riskier because identity and
    directory records share one schema.

### Option 3: Add `users.admin_yn`

* Pros:
  * Simple to show an administrator marker in a table.
* Cons:
  * A single Y/N value cannot express `system_admin`, `service_owner`,
    `service_developer`, `service_operator`, or `auditor`.
  * Creates two competing authorization sources.
  * Increases the chance that UI code gates access from a directory flag instead
    of server-derived RBAC.

## Consequences

Organization user CRUD can manage every employee-like record without creating
login credentials. Admin Console access remains limited to rows in
`admin_users`.

Disabling an organization user and disabling Admin Console login are distinct
operations:

- `users.use_yn = 'N'` removes the person from active organization use.
- `admin_users.status = 'disabled'` blocks the Admin login account.

When an Admin account is linked to an inactive organization user, authentication
must fail. This protects the system if HR-style deactivation happens before the
Admin account is explicitly disabled.

The Service membership model remains unchanged. Service roles continue to target
`admin_users.user_id`, because only authenticated Admin accounts can perform
Admin Console actions.

The Admin UI must label the new area as organization directory or users and
departments management. It must not imply that a `users` row alone grants Admin
access.

## Implementation Notes

Expected schema:

```text
departments
- id uuid primary key
- dept_number text unique not null
- name text not null
- use_yn text not null check in ('Y', 'N')
- created_by text not null
- updated_by text not null
- created_at timestamptz not null
- updated_at timestamptz not null

users
- id uuid primary key
- user_number text unique not null
- name text not null
- department_id uuid not null references departments(id)
- use_yn text not null check in ('Y', 'N')
- created_by text not null
- updated_by text not null
- created_at timestamptz not null
- updated_at timestamptz not null

admin_users
- organization_user_id uuid null unique references users(id)
```

Expected Admin API shape:

```text
GET    /admin/v1/departments
POST   /admin/v1/departments
PATCH  /admin/v1/departments/{department_id}
DELETE /admin/v1/departments/{department_id}

GET    /admin/v1/organization-users
POST   /admin/v1/organization-users
PATCH  /admin/v1/organization-users/{organization_user_id}
DELETE /admin/v1/organization-users/{organization_user_id}
```

`DELETE` operations should behave as controlled deactivation:

- User delete sets `users.use_yn = 'N'`.
- Department delete sets `departments.use_yn = 'N'` only when no active users
  remain in that department.

The existing `GET /admin/v1/users` endpoint is reserved for Admin account lookup
used by Service membership assignment. Organization user APIs must use the
`/organization-users` path to avoid semantic conflict.

## Verification

The decision is valid only if tests prove:

- `departments.dept_number` is unique.
- `users.user_number` is unique.
- `users.department_id` references an existing department.
- `use_yn` accepts only `Y` or `N`.
- `admin_users.organization_user_id` is nullable and unique.
- Admin authentication fails when the linked organization user has
  `use_yn = 'N'`.
- Organization user CRUD does not create Service roles.
- Service membership grant and revoke still use `admin_users.user_id`.
- Normal browser Admin UI requests still use the `irt_admin_session` cookie and
  do not send trusted actor headers.

## Rollback or Revisit Conditions

Revisit this decision if:

- The product accepts a single-table identity model where every organization
  user is always an Admin Console account.
- An external IdP or HR source requires a different immutable key strategy.
- Organization department membership must become temporal with historical
  effective dates.
- Authorization moves from RBAC tables to a central external policy engine.
