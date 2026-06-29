# Security Operations Runbook

This runbook defines the closed-network security operations contract for API keys, admin token handling, KEK handling, and raw query decrypt.

Use `docs/ops/pilot-rehearsal.md` as the top-level Sprint 5 execution path for
pilot security rehearsal and incident response evidence. The commands below
remain separately approved diagnostic workflows when the rehearsal manifest
identifies a security operations gap.

## API key lifecycle

Use API key rotation as an overlap-first workflow:

1. Create a new API key for the same `service_id`, `environment`, `app_id`, allowed intents, and allowed route keys.
2. Store the new secret only in the generated `.secret.json` state file.
3. Run a Dify-style smoke request with the new key.
4. Switch the Dify secret variable to the new key during the approved overlap window.
5. Revoke the old key after the smoke and Dify secret update succeed.
6. Keep the rotation report as evidence. It records key IDs and fingerprints, not raw secrets.

Rollback during the overlap window is to restore the old Dify secret variable and defer old-key revoke.
After revoke, rollback requires issuing another new key and repeating the smoke path.

Recommended command:

```bash
uv run python scripts/rotate_api_key.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --state ${STATE_PATH} \
  --catalog docs/pilot/it-helpdesk-pilot-catalog.json \
  --out-state var/pilot/${SERVICE_ID}.rotated.state.secret.json \
  --report-dir var/reports \
  --smoke-query "API timeout 500 에러가 납니다" \
  --revoke-old
```

## Admin token operations

`ADMIN_BOOTSTRAP_TOKEN` is a closed-network bootstrap secret. Store it only in the approved internal secret manager or equivalent controlled deployment secret channel.

Rotation procedure:

1. Create the replacement token in the approved secret store.
2. Schedule a short maintenance window for admin automation.
3. Restart the API and operator shell environment with the replacement `ADMIN_BOOTSTRAP_TOKEN`.
4. Verify admin access with a read-only admin request.
5. Remove the previous token from the secret store.

Admin role usage:

- `system_admin`: service creation, API key create/revoke, release create/activate/rollback, emergency operations.
- `service_developer`: scoped catalog and policy work for assigned services.
- `service_operator`: scoped masked runtime log inspection.
- `auditor`: scoped raw query decrypt after approval.

## KEK operations

Raw text uses application-level envelope encryption with per-record DEKs and an active KEK configured by `RAW_TEXT_KEK_ID` and `RAW_TEXT_KEK_BASE64`.

KEK requirements:

- Store KEK material in an approved internal secret manager, HSM, or KMS-equivalent control.
- Use separate KEKs per environment.
- Never place real base64 KEKs in `.env.closed-network.example`, reports, tickets, chat, or application logs.
- Base64 KEKs must only live in the approved secret manager or deployment secret channel.
- The runtime encrypts new raw text with a single active KEK while legacy KEKs are configured only for decrypting records during rotation.

Use the Sprint 3 KEK rewrap workflow in `docs/ops/security-lifecycle.md` before changing `RAW_TEXT_KEK_ID` or `RAW_TEXT_KEK_BASE64` for a service with encrypted raw text. The workflow covers `RAW_TEXT_LEGACY_KEKS_JSON`, dry-run, execute with approval ID, raw-text key summary validation, rollback, and secret leak checks.

After KEK rewrap or runtime raw-query retention, export consolidated operations evidence:

```bash
uv run python scripts/export_ops_evidence.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --out-dir var/evidence/${SERVICE_ID}/ops \
  --window-hours 24 \
  --actor-id ops-evidence \
  --environment ${INTENT_ROUTING_ENVIRONMENT:-dev}
```

## Raw query decrypt

Raw query decrypt is an exception workflow, not a routine debugging tool.

Required controls:

1. Obtain an approval ID from the approved security process.
2. Use a scoped `auditor` or `system_admin` role.
3. Provide a human-readable reason tied to an incident or audit ticket.
4. Run the trace audit drill with both `--approval-id` and `--view-reason`.
5. Keep the output evidence. The CLI output confirms `raw_query_viewed=true` but does not print the raw query.
6. Verify the admin API wrote a `raw_query.viewed` audit log.

Command:

```bash
uv run python scripts/trace_audit_drill.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --state ${STATE_PATH} \
  --trace-id <trace_id> \
  --approval-id SEC-20260628-001 \
  --view-reason "장애 분석 ticket INC-20260628-001"
```

The request reason sent to the admin API is:

```text
approval=SEC-20260628-001; reason=장애 분석 ticket INC-20260628-001
```
