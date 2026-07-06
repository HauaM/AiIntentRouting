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

## Verification

The first milestone is valid only if tests prove:

- Unauthenticated Admin UI/API access is rejected.
- A user can log in and retrieve their own accessible Services.
- A service-scoped developer can manage Intents only for assigned Services.
- The same user can have different roles on different Services.
- A user without Service membership receives `403 Forbidden`.
- `system_admin` can access all Services.
- Audit records use the authenticated user identity.

## Rollback Or Revisit Conditions

Revisit this decision if:

- Intent-level or route-level authorization is required before account login ships.
- Environment-specific permissions become mandatory for the first release.
- Two-person approval is required for every Intent change in the first release.
- External identity provider integration becomes mandatory before local account authentication is accepted.
