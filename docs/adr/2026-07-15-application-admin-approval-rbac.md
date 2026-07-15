# ADR: Application Admin Approval RBAC

## Status

Accepted

## Context

The Admin Console needs two different operator groups:

- `system_admin`: the single platform operator who approves Admin Console access, creates Services, and grants Service roles.
- `application_admin`: an approved application developer who may use the Admin UI only inside Services assigned through `user_service_roles`.

The organization directory `users` table must remain separate from authorization. A `users` row alone must not grant Admin Console access.

## Decision

Add `application_admin` to `admin_user_roles.role`.

`system_admin` remains a global platform role and must exist at most once. `application_admin` is a global access role only. It allows Admin Console login for an approved account, but it does not grant Service access, Service creation, Permission Management access, or Service membership management.

Actual application work remains scoped through `user_service_roles`.

Introduce `admin_access_requests` for self-service registration. Only one pending request may exist per `email_normalized` and per `user_number`. A pending request contains the requested organization user data, login email, hashed password, and required access reason. Approved and rejected requests may retain historical rows with `password_hash = null`. Approval by `system_admin` creates the `users` row, the linked `admin_users` row, and the `application_admin` global role in one transaction. Batch imports continue to create only `users`.

## Consequences

`system_admin` is the only role allowed to manage Admin users, Services, Service membership, and Permission Management. `application_admin` must receive one or more Service roles before it can operate on a Service.

Login eligibility requires an active `admin_users` row, an active linked organization user when linked, and either `system_admin` or `application_admin`.

## Verification

Tests must prove that only one `system_admin` can exist, `application_admin` can log in but cannot access Permission Management without Service roles, and Service operations remain limited by `user_service_roles`.
