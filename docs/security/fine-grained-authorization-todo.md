# Fine-Grained Authorization TODO

This document records mandatory follow-up work for the long-term authorization destination. The first implementation milestone is service-scoped RBAC, but the product direction is fine-grained authorization.

Related ADR:

- `docs/adr/2026-07-06-account-auth-service-rbac-to-fine-grained-authorization.md`

## Destination

Support authorization beyond Service-level roles:

- Who can manage which Service.
- Who can manage which Intent.
- Who can manage which route key.
- Who can act in each environment.
- Who can approve sensitive or operational changes.
- Who can temporarily delegate or receive access.

## Mandatory TODOs

- [ ] Define a resource model for fine-grained permissions.
  - Candidate resource types: `service`, `intent`, `route_key`, `release`, `policy`, `api_key`, `runtime_log`, `raw_query`.

- [ ] Define action names independently from UI labels.
  - Candidate actions: `read`, `create`, `update`, `delete`, `approve`, `activate`, `rollback`, `decrypt`, `export`, `delegate`.

- [ ] Add environment-scoped authorization.
  - Required distinction: `dev`, `stage`, `prod`.
  - Example: user can edit Intents in `dev` but only read in `prod`.

- [ ] Add Intent-level permissions.
  - Example: user can update `password_reset` Intent but not `account_unlock` Intent in the same Service.

- [ ] Add route-key-level permissions.
  - Example: user can manage route keys under `it.password_reset.*` but not `it.account_unlock.*`.

- [ ] Add approval policy support.
  - Required policy examples: two-person approval, author cannot approve own change, risk-related Intent changes require auditor or owner approval.

- [ ] Add release-operation separation.
  - Example: service developer can create catalog changes, but service owner or operator must activate a release.

- [ ] Add temporary delegation.
  - Example: service owner delegates Intent update rights to another user until a specified time.

- [ ] Add organization or team grouping if needed.
  - Example: team membership grants default access to a group of Services.

- [ ] Add explicit deny or conflict resolution rules.
  - Required before multiple sources of permissions exist, such as direct grants, team grants, and temporary delegation.

- [ ] Add permission audit visibility.
  - Required views: who granted access, who changed permissions, who approved, who delegated, when the permission expires.

- [ ] Add permission simulation or explainability.
  - Example: "Why can this user update this Intent?" and "Why was this action denied?"

- [ ] Add migration path from service-scoped RBAC to fine-grained permissions.
  - Service-level roles should map cleanly to initial fine-grained permission grants.

- [ ] Add automated authorization matrix tests.
  - Cover role, service, intent, route key, environment, approval, delegation, and denial cases.

## Non-Goals For First Milestone

These items are intentionally deferred from the first service-scoped RBAC milestone:

- Intent-level permission enforcement.
- Route-key-level permission enforcement.
- Organization hierarchy.
- Team inheritance.
- Temporary delegation.
- Policy engine integration.
- Two-person approval workflow.
- Permission simulation UI.

## First Milestone Compatibility Requirements

The service-scoped RBAC implementation must not block this TODO roadmap. In particular:

- Do not hard-code authorization only around `system_admin`.
- Do not store roles only as global user attributes.
- Do not trust client-provided actor headers after account login exists.
- Do not mix UI labels with server-side permission action names.
- Do not design audit logs without authenticated user identity.
- Do not assume one user has the same role on every Service.
