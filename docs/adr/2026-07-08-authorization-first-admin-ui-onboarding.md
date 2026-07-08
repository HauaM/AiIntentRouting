# ADR: Authorization-First Admin UI Onboarding

## Status

Accepted

## Context

The product target is a financial closed-network environment where multiple
internal services use a shared Intent Routing Service. In that environment,
Service registration, user assignment, runtime API access, release operations,
and audit evidence are part of the same onboarding boundary.

The PRD defines separate actors such as system administrators, service
developers, service operators, auditors, and client systems. The existing
account authentication and Service RBAC ADR establishes account login and
service-scoped roles as the first authorization milestone. The Admin UI now
needs an onboarding direction that preserves that boundary from the start,
instead of treating permissions as a later add-on.

If the Admin UI only implements a system-admin happy path first, later work for
Service membership, role assignment, API-key scope, runtime setup, and audit
evidence may require broad changes to navigation, page ownership, API contracts,
and manual QA scenarios.

## Decision

Use an authorization-first Admin UI onboarding model.

The target product flow is C: Service registration, Service membership and role
assignment, developer configuration, validation, release, API-key scope,
runtime integration guidance, and operational evidence.

Implementation may still proceed in small vertical slices, but every slice must
preserve the C target flow:

- C-1: Service onboarding.
  - A `system_admin` registers a Service.
  - The Service becomes available through server-derived Service scope.
  - Service creation is audited.
  - The UI must not require trusted actor headers from the browser.
- C-2: Role-scoped developer setup and validation.
  - A `system_admin` or authorized owner assigns Service roles.
  - A `service_developer` configures Intent Catalogs, route keys, examples,
    policy/catalog versions, and test runs only inside assigned Services.
  - Users without Service membership cannot inspect or mutate that Service.
- C-3: Runtime integration and operations.
  - A `system_admin` creates scoped API keys from known intent and route
    candidates.
  - The UI guides client systems such as Dify to call the runtime API with the
    correct service, app, key, and request headers.
  - Runtime logs remain masked by default.
  - Audit logs remain append-only evidence for onboarding, release, key, and
    operational actions.

Permission and audit requirements are not test setup. They are part of the
product workflow and must be represented in the Admin UI documentation and QA
scenarios before C-2 and C-3 implementation begins.

## Alternatives Considered

### Option 1: Implement Service Registration Only First

* Pros:
  * Smallest immediate UI increment.
  * Quickly removes the current true-E2E blocker.
* Cons:
  * Can optimize the UI around a single `system_admin` path.
  * Risks treating role assignment and runtime integration as bolt-on screens.
  * May require later navigation and flow rework when non-admin users are added.

### Option 2: Implement The Entire C Flow At Once

* Pros:
  * Most complete representation of the final onboarding product.
  * Can align all pages, APIs, and QA scenarios in one design pass.
* Cons:
  * High delivery risk and longer feedback loop.
  * Some C-2 and C-3 backend contracts may need separate design and approval.
  * Easier to overbuild before the C-1 Service onboarding experience is tested.

### Option 3: Commit To C, Implement In Phased Vertical Slices

* Pros:
  * Keeps the financial closed-network authorization model explicit from the
    beginning.
  * Allows C-1 to ship and be tested without losing C-2 and C-3 requirements.
  * Reduces future rework by designing Service scope, roles, audit, and runtime
    handoff as one product workflow.
  * Matches the existing account authentication and Service RBAC direction.
* Cons:
  * Requires documentation and QA scenarios to track future slices that are not
    fully implemented yet.
  * Requires discipline to avoid adding temporary UI shortcuts that conflict
    with server-derived roles and Service scope.

## Consequences

The Admin UI cannot call itself complete after only Service creation. Service
registration is the first slice of a broader onboarding workflow.

Future Admin UI work must keep Service scope visible and server-derived. Normal
browser requests continue to use account login and the `irt_admin_session`
cookie, not `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`, or
`X-Service-Scope`.

Role assignment, API-key scope, release actions, runtime setup guidance, masked
runtime logs, and append-only audit logs become part of the onboarding quality
bar. Manual QA must verify both user convenience and authorization boundaries.

Some C-2 and C-3 features may require new backend contracts. Until those
contracts exist, the UI must render unavailable capabilities as disabled or
informational rather than faking state.

## Implementation Notes

Admin UI documentation should describe the C flow as:

1. Service onboarding.
2. Service membership and role assignment.
3. Intent/example setup.
4. Validation bundle and CSV test run.
5. Release candidate and release activation.
6. Scoped API key creation.
7. Runtime client setup guidance.
8. Runtime and audit evidence review.
9. Failure-case improvement loop.

The C-1 implementation should be built so C-2 can add membership and role
assignment without changing the Service model or Service picker contract.

The C-3 implementation should build on release candidates and intent/route
candidates instead of asking users to manually type internal IDs or route scope
values.

## Verification

This decision is valid only if documentation and manual QA scenarios verify:

- Service registration is possible from the UI or explicitly recorded as a C-1
  blocker.
- Service picker options come from server-derived accessible Services.
- Service role gates hide or disable actions the current user cannot perform.
- A user without Service membership cannot inspect or mutate the Service.
- API keys are scoped from known intent and route candidates.
- API key inventory never exposes raw secrets.
- Runtime logs show masked query text by default.
- Audit logs record Service, actor, and target evidence for onboarding and
  operational actions.

## Rollback Or Revisit Conditions

Revisit this decision if:

- the product no longer targets a financial closed-network environment.
- a single-tenant or single-service deployment becomes the accepted product
  scope.
- external identity provider integration changes the Service membership model.
- security review rejects Service-scoped RBAC as an acceptable first
  authorization milestone.
- C-2 or C-3 contracts require a full fine-grained authorization engine before
  any Service onboarding UI can ship.
