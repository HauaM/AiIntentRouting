# Admin Access Request Validation Fix Design

## Context

The public `/admin-access-request` form has no password confirmation field. It
also accepts values that the `POST /admin/v1/admin-access-requests` schema can
reject, while its error formatter does not render FastAPI/Pydantic validation
error arrays as useful field-level messages.

The confirmed contract in
`docs/superpowers/plans/2026-07-15-application-admin-approval-rbac.md`, Task 9b,
sends `user_number`, `name`, `department_id`, `email`, `password`, and
`access_reason`. Password confirmation is a browser-side validation value and
must not be added to the API payload.

## Scope

- Add a password confirmation input immediately after the password input.
- Require the confirmation value to match the password before submission.
- Align the access-reason form validation with the backend minimum of 10
  characters after trimming.
- Convert FastAPI/Pydantic 422 validation details into a readable form-level
  error instead of a generic request failure.
- Preserve the existing public Umi `request` call and API payload contract.

Out of scope:

- Changing the backend request schema.
- Sending the confirmation password over the network.
- Refactoring unrelated authentication or Admin Console screens.

## Component And Data Flow

`AdminAccessRequestFormValues` gains `password_confirm` for form state only.
`toAdminAccessRequestCreateRequest` continues to return the existing API type
and omits `password_confirm`.

The Ant Design form validates required fields, email shape, password length,
password equality, and the trimmed access-reason length. Only valid values are
normalized and passed to `submitAdminAccessRequest`.

If the server still returns a validation response, the page extracts the first
useful message from `detail` when it is an array. Existing string and structured
application-error formats remain supported, followed by the existing generic
fallback.

## Error Handling

- Password mismatch is shown on the confirmation field and prevents submit.
- Access reasons shorter than 10 characters after trimming are rejected by the
  browser with a Korean validation message.
- Backend validation errors are shown in the existing form-level `Alert`.
- Password values must never be included in error text or diagnostic output.

## Test Design

Tests are written before production changes and must initially fail for the
missing behavior:

1. Form normalization omits `password_confirm` from the API payload.
2. The page contains a password confirmation field with password dependency and
   equality validation.
3. The page applies the backend-compatible 10-character access-reason rule.
4. The error formatter converts a representative Pydantic 422 detail array into
   a readable message.

After the minimal implementation, run the focused form and auth-service tests,
then the frontend typecheck. Search changed files for prohibited Admin UI API
patterns listed in the project skill.

## Success Criteria

- Applicants cannot submit mismatched passwords.
- The confirmation password is absent from the network payload.
- Values accepted by the form satisfy the known backend access-reason length
  rule.
- A representative 422 response produces a specific readable error.
- Focused tests and frontend typecheck pass.
