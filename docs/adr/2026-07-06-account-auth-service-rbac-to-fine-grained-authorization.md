# ADR: Account Authentication And Service RBAC As The First Step Toward Fine-Grained Authorization

## Status

Accepted

## Context

The current Admin API uses bootstrap-style trusted headers:

- `X-Admin-Token`
- `X-Actor-Id`
- `X-Actor-Roles`
- `X-Service-Scope`

This was sufficient for API-only MVP and local Admin UI Phase 0 work, but the target product needs real users. The PRD already defines service developers who manage Intent Catalogs and examples only within their assigned `service_id` scope. The long-term goal is finer authorization than service-level roles, including resource-level permissions, environment-specific controls, approvals, and delegation.

The immediate product need is to let users log in and manage only the Services they are assigned to, while avoiding an overbuilt authorization engine before the core user and service membership flow is verified.

## Decision

Use account-based authentication and service-scoped RBAC as the first implementation milestone, while declaring fine-grained authorization as the destination architecture.

The first milestone will introduce:

- User accounts.
- Login sessions.
- Service membership records.
- Service-scoped role assignments.
- Authorization checks based on `(user, service_id, role, action)`.

The first milestone will not implement full fine-grained authorization. Instead, it must keep model names and boundaries compatible with later expansion to resource-level permissions and policy rules.

`ADMIN_BOOTSTRAP_TOKEN` should be reduced to bootstrap or break-glass use, such as initial system administrator creation or controlled local setup. It should not remain the normal Admin UI authentication mechanism.

For the C-2 Service membership and role-assignment slice, update this accepted
decision as follows:

- Use the existing Service-scoped RBAC model and update this ADR rather than
  creating a separate C-2 ADR.
- Implement role assignment as a Service-scoped API under
  `/admin/v1/services/{service_id}/members`.
- Use existing `user_service_roles` storage for the baseline C-2 contract. No
  new migration is required unless the scope expands to invitations, role
  expiry, revocation history outside audit logs, team inheritance, or
  environment-specific permissions.
- Make `system_admin` the only role that can grant or revoke Service roles in
  the first C-2 implementation.
- Keep `service_owner` delegation as a future increment. A later change may let
  `service_owner` manage lower roles only within their assigned Service, but
  that requires explicit guardrail tests and documentation before enablement.
- Continue to require normal browser Admin UI requests to use the
  `irt_admin_session` cookie. Browser UI must not send `X-Admin-Token`,
  `X-Actor-Id`, `X-Actor-Roles`, or `X-Service-Scope`.
- Place the first C-2 Admin UI membership controls inside the existing
  `/services` page as a selected-Service membership panel. A dedicated
  `/services/:serviceId/members` page can be revisited if the panel becomes too
  dense.

## Alternatives Considered

### Option 1: Admin-Only Login

* Pros:
  * Fastest to implement.
  * Simple mental model.
* Cons:
  * Does not support application owners or service developers.
  * Likely requires rework when non-admin users are added.
  * Conflicts with the PRD requirement that developers only see their assigned `service_id` scope.

### Option 2: Service-Scoped RBAC First

* Pros:
  * Directly supports users who manage Intent Catalogs for assigned Services.
  * Fits the existing service-centered domain model.
  * Provides a useful security boundary without building a full policy engine immediately.
  * Can evolve into fine-grained authorization if the model keeps clear user, role, service, and permission boundaries.
* Cons:
  * Does not immediately support intent-level, route-level, environment-level, or approval-based permissions.
  * Requires later migration or extension for the final authorization destination.

### Option 3: Full Fine-Grained Authorization Now

* Pros:
  * Closest to the long-term destination.
  * Can model organization, team, environment, resource, approval, and delegation policies from the start.
* Cons:
  * High initial complexity.
  * Risks implementing policy abstractions before real Admin UI workflows prove the required permission boundaries.
  * Slower delivery for the immediate login and service-owner use case.

## Consequences

The first implementation will give real users a login flow and will enforce Service-level access for Intent management. A user with a service developer or service owner role on a Service can manage that Service's Intent Catalog; users without a matching Service role receive `403 Forbidden`.

The system must record actors from authenticated sessions instead of trusting UI-provided actor headers. Audit logs should identify the authenticated user and the Service/action being accessed.

For C-2, Service role grant and revoke operations become auditable product
events. The baseline implementation remains simple because `system_admin` owns
membership changes, but Service teams still depend on system administrators for
every membership update until owner delegation is explicitly approved.

Future work remains mandatory for the final fine-grained authorization model. That future work is tracked separately in `docs/security/fine-grained-authorization-todo.md`.

## Implementation Notes

The first milestone should prefer a session or token model suitable for a browser Admin Console. The authorization context should be derived server-side from persisted users, sessions, and service memberships.

Expected initial domain concepts:

- `users`
- `sessions`
- `roles`
- `services`
- `user_service_roles` or equivalent service membership table

Expected initial roles:

- `system_admin`
- `service_owner`
- `service_developer`
- `service_operator`
- `auditor`

C-2 expected API shape:

- `GET /admin/v1/users?query={email_or_name}&limit=25`
- `GET /admin/v1/services/{service_id}/members`
- `POST /admin/v1/services/{service_id}/members/{user_id}/roles`
- `DELETE /admin/v1/services/{service_id}/members/{user_id}/roles/{role}`

C-2 expected audit events:

- `service_membership.role_granted`
- `service_membership.role_revoked`

The detailed implementation plan is recorded in
`docs/superpowers/plans/2026-07-08-admin-ui-c2-service-membership-roles.md`.

## Verification

The first milestone is valid only if tests prove:

- Unauthenticated Admin UI/API access is rejected.
- A user can log in and retrieve their own accessible Services.
- A service-scoped developer can manage Intents only for assigned Services.
- The same user can have different roles on different Services.
- A user without Service membership receives `403 Forbidden`.
- `system_admin` can access all Services.
- Audit records use the authenticated user identity.

C-2 verification must additionally prove:

- `system_admin` can grant and revoke Service-scoped roles.
- `/me/services` returns only Services derived from persisted membership for
  non-system-admin users.
- A user with a role on Service A cannot inspect or mutate Service B.
- A user without Service membership receives `403 Forbidden` for Service
  inspect and mutate paths.
- `service_developer` can manage Intents, examples, policy versions, catalog
  versions, and test runs only inside assigned Services.
- `service_operator` and `auditor` have only their approved read paths.
- Membership grant and revoke operations write append-only audit events.
- Normal browser Admin UI requests use the `irt_admin_session` cookie and do
  not send trusted actor headers.

## Rollback Or Revisit Conditions

Revisit this decision if:

- Intent-level or route-level authorization is required before account login ships.
- Environment-specific permissions become mandatory for the first release.
- Two-person approval is required for every Intent change in the first release.
- External identity provider integration becomes mandatory before local account authentication is accepted.
- Service owner delegation becomes mandatory for C-2 rather than a future
  increment.
- membership status, invitation, expiry, revocation history, team inheritance,
  or environment-specific role scope becomes mandatory for C-2.
