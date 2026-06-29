# Dify Handoff Checklist

Use this checklist before handing a Dify workflow to pilot operators. Attach the
completed evidence files to the pilot handoff ticket or release folder.

Dry-run rehearsal: `docs/integrations/dify-dry-run-rehearsal.md`
Dry-run evidence template: `docs/integrations/dify-dry-run-evidence-template.md`

## HTTP Request Node Mapping

- [ ] Method is `POST`.
- [ ] URL points to `/v1/intent-route` for the target environment.
- [ ] Timeout: 8 seconds.
- [ ] `Authorization` is `Bearer {{intent_routing_api_key}}`; Dify masks the `intent_routing_api_key secret variable`.
- [ ] `X-Key-Id` maps to `{{intent_routing_key_id}}`.
- [ ] `X-App-Id` is the approved app id, usually `dify-platform`.
- [ ] `X-Service-Id` maps to the pilot `service_id`.
- [ ] `X-Request-Id` maps to `workflow_run_id`.
- [ ] Body `query` maps to the user input variable.
- [ ] Body `user_context.workflow_run_id` maps to `workflow_run_id`.
- [ ] 408, 5xx, and timeout branches have no automatic retry loop.

## Decision Branches

- [ ] `confident`: route by `route_key` and preserve `trace_id`, `request_id`, and `release_version`.
- [ ] `clarify`: show `clarify_question` and candidate choices; preserve `trace_id` and `request_id`.
- [ ] `fallback`: return the approved fallback message or hand off to the default channel.
- [ ] `off_topic`: return the service-scope message and stop service-specific routing.
- [ ] `risk`: block the request and send `trace_id` to the security trace process.
- [ ] `unauthorized`: do not call a business route; log `trace_id`, `request_id`, and `service_id`.

## Error Branches

- [ ] `401`: triage `intent_routing_api_key`, `intent_routing_key_id`, and secret variable binding.
- [ ] `403`: triage `X-App-Id`, `X-Service-Id`, and API key route or service scope.
- [ ] `422`: triage body JSON, `query`, and `workflow_run_id` variable mapping.
- [ ] `408`: show fallback or human handoff; no automatic retry loop.
- [ ] `5xx`: show fallback or human handoff; no automatic retry loop.
- [ ] `timeout`: show fallback or human handoff; no automatic retry loop.

## Evidence Attachments

- [ ] `dify-smoke-matrix.json`
- [ ] `dify-smoke-matrix.md`
- [ ] `pilot-rehearsal-manifest.md`
- [ ] `readiness-report.md`
- [ ] threshold comparison Markdown
- [ ] screenshot or exported Dify workflow version identifier
- [ ] Dify workflow version identifier recorded through `--dify-workflow-version`.
- [ ] Dify UI evidence path recorded through `--dify-ui-evidence-path`; do not inline screenshot/export content into Markdown.
- [ ] Completed copy of `docs/integrations/dify-dry-run-evidence-template.md`.
- [ ] The rehearsal wrapper records only the Dify workflow version identifier and evidence path.
- [ ] Screenshots and workflow exports must show masked values only.
- [ ] Do not paste screenshot/export contents into pilot-rehearsal-manifest.md.

## Manual UI Checks

- [ ] Dify hides the `intent_routing_api_key secret variable`.
- [ ] `X-Request-Id` maps to `workflow_run_id`.
- [ ] Downstream nodes preserve `trace_id`, `request_id`, and `release_version`.
- [ ] risk branch does not call business route.

## Rehearsal Wrapper

Document the manual Dify UI dry-run result, then run the wrapper with the
version identifier and evidence path:

```bash
uv run python scripts/run_pilot_rehearsal.py \
  --mode local \
  --base-url http://127.0.0.1:8000 \
  --admin-token ${ADMIN_BOOTSTRAP_TOKEN} \
  --service-id ${SERVICE_ID} \
  --environment dev \
  --state-path ${STATE_PATH} \
  --csv-tier standard \
  --required-preset balanced \
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --dify-workflow-version "dify-workflow-export-YYYYMMDD-NNN" \
  --dify-ui-evidence-path "var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md" \
  --out-dir "var/evidence/${SERVICE_ID}/rehearsal"
```

Expected documented results: `pilot-rehearsal-manifest.md` includes the
workflow version identifier, includes the Dify UI evidence path, does not inline
screenshot or workflow export content, and the secret scan passes.
