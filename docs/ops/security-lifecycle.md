# Security Lifecycle Runbook

This runbook covers the Sprint 3 KEK rewrap, runtime raw-query retention, and operations evidence workflow for one service.

Use `docs/ops/pilot-rehearsal.md` as the top-level Sprint 5 execution path for
pilot readiness and security rehearsal. The KEK rewrap and runtime raw-query
retention commands below remain diagnostic or separately approved lifecycle
workflows; the Sprint 5 wrapper runs dry evidence collection only and does not
execute destructive security operations.

## KEK rotation prerequisites

Before changing a raw-text KEK:

1. Confirm `DATABASE_URL` or `TEST_DATABASE_URL` points at the intended database.
2. Confirm `/readyz` is ready and the service has a known active release.
3. Record an approval ID from the approved security process.
4. Confirm the new active KEK and the previous KEK are present only in the approved secret manager or deployment secret channel.
5. Take the required database backup or snapshot for the deployment tier.
6. Create a working evidence directory such as `var/evidence/${SERVICE_ID}/security-lifecycle`.

Real base64 KEK values must not be pasted into tickets, reports, shell history captures, docs, or chat. Use secret-manager injection, masked shell prompts, or the deployment secret channel.

## Active and legacy KEK environment

Set the new active key ID and active KEK through the deployment secret channel:

```bash
export RAW_TEXT_KEK_ID="<new-active-key-id>"
export RAW_TEXT_KEK_BASE64="<new-active-kek-base64-from-secret-manager>"
```

Keep the previous KEK available as a legacy decrypt-only entry until rewrap validation is complete:

```bash
export RAW_TEXT_LEGACY_KEKS_JSON='{"<previous-key-id>":"<previous-kek-base64-from-secret-manager>"}'
```

The active key ID must not also appear in `RAW_TEXT_LEGACY_KEKS_JSON`.

## KEK rewrap dry-run command

Run the dry-run first and keep the generated report:

```bash
uv run python scripts/rewrap_raw_text.py \
  --service-id ${SERVICE_ID} \
  --actor-id security-operator \
  --report-dir var/evidence/${SERVICE_ID}/security-lifecycle \
  --include both \
  --dry-run \
  --batch-size 100 \
  --limit 1000
```

Review the dry-run report for `failed_count=0`, expected legacy counts, and `plaintext_exported=false`.

## KEK rewrap execute command

Execute only after the dry-run and approval are complete:

```bash
uv run python scripts/rewrap_raw_text.py \
  --service-id ${SERVICE_ID} \
  --actor-id security-operator \
  --report-dir var/evidence/${SERVICE_ID}/security-lifecycle \
  --include both \
  --execute \
  --approval-id ${APPROVAL_ID} \
  --confirm-active-key-id ${RAW_TEXT_KEK_ID} \
  --batch-size 100 \
  --limit 1000
```

The execute report records run IDs, key IDs, counts, approval ID, and status. It must not include plaintext, ciphertext, encrypted DEKs, or KEK material.

## Post-rewrap validation using raw-text key summary

Validate the key inventory through the admin raw-text key summary endpoint:

```bash
curl -s \
  -H "X-Admin-Token: ${ADMIN_BOOTSTRAP_TOKEN}" \
  -H "X-Actor-Id: ops-evidence" \
  -H "X-Actor-Roles: system_admin" \
  -H "X-Service-Scope: ${SERVICE_ID}" \
  "http://127.0.0.1:8000/admin/v1/services/${SERVICE_ID}/security/raw-text-key-summary"
```

Expected result: raw text records are counted under the new active `RAW_TEXT_KEK_ID`, and runtime logs already processed by retention remain counted as `raw_query_redacted`.

## Runtime raw-query retention

Dry-run retention first:

```bash
uv run python scripts/apply_log_retention.py \
  --service-id ${SERVICE_ID} \
  --older-than-days 30 \
  --limit 500 \
  --actor-id retention-operator \
  --reason "approval=${APPROVAL_ID}; retention policy" \
  --report-dir var/evidence/${SERVICE_ID}/security-lifecycle \
  --dry-run
```

Execute after approval:

```bash
uv run python scripts/apply_log_retention.py \
  --service-id ${SERVICE_ID} \
  --older-than-days 30 \
  --limit 500 \
  --actor-id retention-operator \
  --reason "approval=${APPROVAL_ID}; retention policy" \
  --report-dir var/evidence/${SERVICE_ID}/security-lifecycle \
  --execute \
  --approval-id ${APPROVAL_ID}
```

The retention reports record eligible, already redacted, and redacted counts without printing raw queries.

If an execute command commits database changes but fails while writing the local report files, do not rerun the mutation blindly. First export consolidated operations evidence, then query the relevant `raw_text_rewrap_runs`, runtime raw-query retention counts, and audit logs for the same `approval_id`. Store the regenerated evidence with an operator note that the original report write failed after execution.

## Metrics and evidence export commands

Export the consolidated operations evidence package after rewrap or retention work:

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

Expected outputs:

- `ops-evidence.json`
- `ops-evidence.md`

The export includes readiness, active release, runtime metrics, raw-text key summary, latest KEK rewrap run IDs, runtime raw-query retention counts, and audit event counts. `raw_query_retention.incomplete_count` and `raw_query_incomplete` key-summary rows indicate partial raw-query material that must be removed by the retention workflow.

## Rollback before rewrap

If validation fails before the execute command:

1. Restore the previous `RAW_TEXT_KEK_ID` and `RAW_TEXT_KEK_BASE64` through the approved secret channel.
2. Remove the pending legacy entry from `RAW_TEXT_LEGACY_KEKS_JSON`.
3. Restart the API with the previous secret set.
4. Verify `/readyz` and raw-text key summary.
5. Keep the failed dry-run report with the approval record.

## Rollback after rewrap

After execute succeeds, records may be encrypted under the new active key. Do not simply switch back to the previous active key unless one of these approved recovery paths is selected:

1. Restore the database snapshot taken before rewrap and restart with the previous active KEK.
2. Keep the new active KEK, keep the previous KEK as legacy until all validation passes, and roll back only application image or release changes.
3. Run an approved reverse rewrap that makes the previous key active again, with the current key configured as legacy, then validate using raw-text key summary.

Retain the execute report, audit events, and operations evidence export for the incident or change record.

## secret leak checks

Before attaching evidence outside the operator host, scan the generated evidence directory:

```bash
grep -R -n -E 'RAW_TEXT_KEK_BASE64|Bearer[[:space:]]+|secret state|encrypted_dek|ciphertext' \
  var/evidence/${SERVICE_ID}
```

The expected result is no matches in `ops-evidence.json`, `ops-evidence.md`, rewrap reports, or retention reports. Keep generated `.secret.json` state files outside evidence bundles.
