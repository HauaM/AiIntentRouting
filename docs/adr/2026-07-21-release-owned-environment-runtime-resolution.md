# ADR: Release-Owned Environment And Runtime Resolution

## Status

Accepted

## Context

The current implementation stores `environment` and
`default_threshold_preset` on `services`. Release creation, API key creation,
runtime setup guidance, and runtime authentication all inherit or validate
against the selected Service environment. This made a local Postman runtime
call fail when an API key and active release were created for `test`, but the
backend process was not started with `INTENT_ROUTING_ENVIRONMENT=test`.

That model makes Service identity too tightly coupled to deployment
environment. It also implies that operators must run separate backend
applications for `dev`, `qa`, and `prod` even when one runtime backend could
safely route by authenticated API key metadata.

The accepted product workflow is:

1. `system_admin` creates a logical Service and grants `service_owner` for it.
2. `service_owner` or `service_developer` configures intents and catalog
   versions inside an assigned Service.
3. `service_owner` or `service_developer` runs tests for a catalog and policy
   version.
4. `service_owner` creates releases from passed test runs and selects the
   target environment on release creation.
5. `service_owner` creates API keys for a selected released environment.
6. Runtime calls use the API key to resolve the Service and environment.

## Decision

Service becomes the logical business and authorization unit. Service creation
no longer collects `environment` or `default_threshold_preset`.

Environment is owned by releases and API keys:

- Supported runtime environments are `dev`, `qa`, and `prod`.
- Existing pilot runbooks may continue to use `pilot` in Service IDs, file
  names, and scenario names, but `pilot` is not a runtime `environment` value.
- A passed test run may be reused to create releases in multiple environments.
- A release is still scoped by `service_id + environment`.
- API keys are scoped by `service_id + environment + app_id` and follow the
  active release for that environment; they are not bound to one
  `release_version`.
- Runtime authentication resolves environment from the verified API key record,
  not from a trusted client header and not from a single process environment.
- Runtime processes may restrict the environments they serve through an
  operator-managed allowlist such as `ALLOWED_RUNTIME_ENVIRONMENTS=dev,qa,prod`.

`service_owner` replaces the old product meaning of `application_admin` for
assigned-Service ownership. `application_admin` may remain only as a global
login eligibility role during transition; it is not a Service operation role.

## Authorization Matrix

`system_admin` has every permission. Its main responsibilities are Service
creation, granting initial `service_owner`, and system-wide monitoring.

For assigned Services:

- `service_owner` can manage Service membership from the Services screen,
  manage Intent Catalog, Test Runs, Releases, API Keys, and Runtime Logs, but
  cannot access Organization Directory, Permission Management, or Audit Logs.
- `service_developer` can view the Services screen, manage Intent Catalog and
  Test Runs, view Releases, and view Runtime Logs. It cannot access
  Organization Directory, Permission Management, API Keys, or Audit Logs, and
  cannot create, activate, or rollback releases.

Existing security and operations roles such as `service_operator` and
`auditor` are not redefined by this ADR except where they intersect with the
new Service-owned workflow. Removing or redesigning those roles requires a
separate decision.

## Alternatives Considered

### Option 1: Keep Service-Owned Environment

* Pros:
  * Strong process-level isolation.
  * Minimal implementation change.
* Cons:
  * Multiplies backend application instances for `dev`, `qa`, and `prod`.
  * Forces environment decisions too early during Service registration.
  * Blocks one catalog/test evidence bundle from becoming releases in several
    environments.

### Option 2: Let Clients Send Environment Headers

* Pros:
  * Single backend can serve multiple environments.
  * Small runtime API change.
* Cons:
  * Trusts caller-supplied routing metadata.
  * Makes wrong-environment calls easier when a client or Postman collection is
    misconfigured.

### Option 3: Resolve Environment From API Key Metadata

* Pros:
  * Keeps a single backend deployment possible.
  * Environment cannot be forged by request headers.
  * API keys naturally point to the active release for their Service and
    environment.
  * Aligns Admin UI flow with how developers expect to test, release, and
    integrate one logical Service.
* Cons:
  * Requires schema, Admin API, runtime auth, UI, docs, and tests to change
    together.
  * Requires an allowlist guardrail so one backend does not accidentally serve
    an unapproved environment.

## Consequences

The implementation must remove environment and default preset from Service
create/list contracts and Admin UI forms. Existing local data does not need a
preserving migration because Services, releases, and API keys will be
re-registered.

Release candidate logic must allow the same passed test run to be released once
per environment. API key scope candidates must be loaded from the active
release for the key's selected environment. Runtime logs and metrics must
expose environment explicitly so mixed-environment requests remain observable.

The Admin UI navigation and server authorization gates must stop treating
`service_developer` as a release/API-key writer and must stop exposing Audit
Logs to `service_owner` and `service_developer`.

## Implementation Notes

Add a schema migration that drops `services.environment` and
`services.default_threshold_preset`, and adds `runtime_logs.environment`.
Because existing data will be deleted and re-registered, no data backfill is
required.

Change `AuthContext` to include `environment` from the verified API key record.
Runtime should call `_load_active_release(repository, service_id=auth.service_id,
environment=auth.environment)`.

Add config parsing for `ALLOWED_RUNTIME_ENVIRONMENTS`; accept only `dev`, `qa`,
and `prod` values. Reject API keys whose environment is outside the runtime
allowlist with `AUTHENTICATION_FAILED`.

## Verification

Implementation must be verified with:

- Schema tests proving Service no longer has environment/default preset and
  Runtime Logs has environment.
- Admin API integration tests for Service creation without environment/preset.
- Release flow tests proving one passed test run can create `dev`, `qa`, and
  `prod` releases.
- Runtime API tests proving one backend can authenticate API keys for multiple
  allowed environments and rejects keys outside the allowlist.
- RBAC tests proving `service_owner` can manage assigned-Service membership,
  releases, API keys, and runtime logs, while `service_developer` cannot write
  releases or API keys and cannot access Audit Logs.
- Admin UI contract tests proving menu visibility and disabled/write states
  match the authorization matrix.

## Rollback or Revisit Conditions

Revisit this decision if security review requires process-isolated prod
runtime, if a regulated deployment demands a separate backend per environment,
or if environment-specific test evidence becomes mandatory before prod release.
