# ADR: Phase 2 Governed Workflow Contracts

## Status

Accepted

## Context

Admin UI Phase 2 includes governed workflow actions that should not execute as
simple one-step writes: publish approval, raw query access, release diff review,
CSV export, and other approval policy controlled operations. These workflows
must build on account authentication, service-scoped RBAC, audit logs, and the
fine-grained authorization roadmap.

The UI must keep Phase 2 actions disabled or informational until the backend can
represent requests, approval state, authorization outcomes, and audit evidence
server-side.

## Decision

Model Phase 2 governed workflows as first-class server-side requests.

Each governed workflow request must have a server-owned identity, Service scope,
resource/action metadata, requester, status, reason, timestamps, and approval or
rejection decision data. Two-person approval, release diff approval, CSV export,
and raw query access must use explicit backend contracts instead of UI-only state
or direct privileged actions.

## Alternatives Considered

### Option 1: Direct Action APIs

* Pros:
  * Small API surface for each action.
  * Fastest path for individual operations.
* Cons:
  * Makes two-person approval and pending states hard to audit consistently.
  * Encourages bypassing approval policy checks at the action endpoint.
  * Gives the UI no durable governed workflow object to reload.

### Option 2: Generic Workflow Engine

* Pros:
  * Can model many future approval and delegation patterns.
  * Centralizes workflow state transitions.
* Cons:
  * Adds broad abstraction before Phase 2 requirements prove they need it.
  * Increases migration, authorization, and testing complexity.
  * Risks delaying raw query, release diff, and CSV export contracts.

### Option 3: Narrow Governed Workflow Tables

* Pros:
  * Gives Phase 2 durable request state without a full workflow engine.
  * Keeps authorization and audit log rules explicit per governed workflow.
  * Fits the first known workflows: raw query access, release approval, and
    masked CSV export.
* Cons:
  * May require consolidation if later workflows need shared policy execution.
  * Requires careful naming so narrow tables can evolve into the
    fine-grained authorization model.

## Consequences

Audit logs must record every governed workflow state transition, including
request creation, approval, rejection, expiration, release activation from an
approved request, raw query viewing, and CSV export generation. Audit records
must use authenticated server-side actor identity and must not include raw query
text, API key secrets, encrypted DEKs, ciphertext, or KEK material.

Authorization tests must cover Service scope, role/action permissions, approval
policy invariants, author-cannot-approve-own-request, two-person approval for
raw query access, and denied transitions. Tests must prove that privileged
actions cannot bypass the governed workflow request path.

Admin UI Phase 2 enablement depends on backend contracts and tests passing for
each workflow. Until then, UI controls for raw query access, release diff
approval, CSV export, and other governed workflow actions remain disabled or
informational.

## Implementation Notes

Prefer narrow server-side request models for the first Phase 2 contracts. Each
contract should define resource type, action name, status transitions,
authorization rule, audit event names, and UI-ready response shape before the UI
enables the action.

## Verification

This decision is valid when docs and backend tests confirm:

- Phase 2 governed workflow contracts are documented before UI enablement.
- Authorization matrix tests cover approval policy and denied transitions.
- Audit log tests cover every governed workflow state transition.
- Raw query, release diff, and CSV export flows cannot execute through
  ungoverned direct action paths.

## Rollback Or Revisit Conditions

Revisit this decision if narrow governed workflow tables cannot express required
approval policies, if a generic workflow engine becomes necessary for multiple
shared workflow types, or if the direct action API surface must remain for a
legacy compatibility contract.
