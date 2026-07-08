# ADR: Startup System Admin Provisioning

## Status

Accepted

## Context

Admin UI uses account login and session cookies. Local and controlled
deployments need deterministic initial `system_admin` creation without
browser-side trusted headers or manual API calls.

The existing account-auth ADR says `ADMIN_BOOTSTRAP_TOKEN` should be reduced to
bootstrap or break-glass use.

## Decision

If `ADMIN_SYSTEM_ADMIN_EMAIL` and `ADMIN_SYSTEM_ADMIN_PASSWORD` are both set,
the backend creates or synchronizes that account during startup.

If neither variable is set, startup does nothing. If only one variable is set,
startup fails.

For an existing user with the same normalized email:

- Verify the password.
- If the password matches, leave the password hash unchanged.
- If the password differs, replace the password hash.
- Ensure the user has the `system_admin` role.

For a missing user, create an active admin user and assign the `system_admin`
role.

## Alternatives Considered

### Option 1: Keep Only `/bootstrap-admin` API

* Pros:
  * Preserves the existing explicit bootstrap flow.
* Cons:
  * Still requires a manual API call or browser-adjacent bootstrap path.
  * Leaves local and controlled deployments without deterministic startup setup.

### Option 2: Local Script Bootstrap Only

* Pros:
  * Keeps startup free of account writes.
  * Can be run only when operators choose.
* Cons:
  * Adds a separate operational step.
  * Is easier to forget or run inconsistently across environments.

### Option 3: Backend Startup Provisioning From Explicit Env Vars

* Pros:
  * Deterministic for local and controlled deployments.
  * Keeps browser-side trusted headers out of normal Admin UI login.
  * Supports password rotation by changing the configured secret.
* Cons:
  * Startup can write to the database.
  * `ADMIN_SYSTEM_ADMIN_PASSWORD` must be handled as a secret.

## Consequences

`ADMIN_SYSTEM_ADMIN_PASSWORD` is a secret. The password and password hash must
not be logged.

Omitted variables keep current behavior. Changing the environment password
rotates the account password at the next startup.

## Implementation Notes

Use existing `admin_users` and `admin_user_roles` storage. No schema migration
is required.

Use the existing password hash and verify logic. Use an advisory transaction
lock for concurrent workers.

## Verification

Verify with tests for:

- Missing environment variables skip provisioning.
- Partial environment variables fail startup.
- Missing user is created.
- Matching password leaves the password hash unchanged.
- Different password updates the password hash.
- Missing `system_admin` role is assigned.
- Login succeeds after startup provisioning.

## Rollback Or Revisit Conditions

Revisit this decision if:

- IdP becomes mandatory.
- Startup database writes are disallowed.
- Secret rotation needs a dedicated operator workflow.
