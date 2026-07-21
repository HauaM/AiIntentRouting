# ADR: Encrypted API Key Secret Reveal

## Status

Accepted

## Context

The API Keys page must allow an authorized Service owner to copy the actual runtime API secret after initial issuance. The previous C-3 baseline showed raw API secrets only once and stored only hash/fingerprint metadata, which prevented later copying from Runtime setup guidance.

## Decision

Persist API key secrets as AES-256-GCM envelope-encrypted secret material in `api_keys` while retaining hash/fingerprint fields for runtime authentication. Add an explicit audited service-scoped reveal endpoint for `system_admin` and selected-Service `service_owner`. The reveal allowlist is exactly `system_admin` and the selected-Service `service_owner`; `service_developer`, `service_operator`, and `auditor` are explicitly denied reveal access. Runtime setup guidance remains metadata/template-only and does not embed the raw secret. The API Keys live test may automatically reveal the secret and use it for one runtime call, but must not display or persist it.

## Alternatives Considered

### Option 1: Keep One-Time Secret Only

* Pros: lowest secret exposure.
* Cons: does not satisfy service_owner copy workflow after issuance.

### Option 2: Store Plaintext Secret

* Pros: simplest reveal implementation.
* Cons: unacceptable database compromise impact and conflicts with project security posture.

### Option 3: Store Encrypted Secret And Reveal On Explicit Action

* Pros: supports the workflow, avoids plaintext persistence, keeps audit evidence.
* Cons: requires KEK management, migration, reveal authorization, and rewrap planning.

## Consequences

New API keys can be revealed by authorized owners. Legacy keys without encrypted secret columns cannot be recovered: the reveal endpoint returns `409 Conflict` with the unavailable message `API key secret is unavailable; rotate or reissue this legacy key.` Operators must rotate or reissue legacy keys before a secret can be revealed. Reveal events become sensitive audit events, including live-test reveal actions. Runtime auth remains hash-based and does not decrypt secrets.

## Implementation Notes

Use nullable encrypted secret columns on `api_keys` with the same envelope shape as raw text fields. Add API-key-specific KEK configuration. The reveal endpoint returns the raw secret only in the response body and writes audit state with `api_key` redacted. The Admin UI live test should call reveal first, pass the raw secret only as a transient runtime request argument, and redact secret-derived response or error fields.

## Verification

Verify with docs contract tests, migration/model tests, backend integration tests for create/reveal/revoke, frontend service tests, API Keys page contract tests, mypy, ruff, TypeScript, and targeted Vitest.

## Rollback or Revisit Conditions

Revisit if security review disallows decryptable API secrets, KEK rotation cannot be operated safely, or audit evidence is insufficient.
