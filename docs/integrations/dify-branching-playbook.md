# Dify Branching Playbook

Template: `docs/integrations/dify-http-request-node-template.json`
Handoff checklist: `docs/integrations/dify-handoff-checklist.md`
Dry-run rehearsal: `docs/integrations/dify-dry-run-rehearsal.md`

## Runtime Branches

- `decision=confident`: route by `route_key`. Carry `trace_id`, `request_id`, `route_key`, and `release_version` to the downstream Agent or business API node.
- `decision=clarify`: answer with `clarify_question`, render candidate labels from `clarify.candidates`, and keep `trace_id` plus `request_id` in the conversation state.
- `decision=fallback`: return the fixed fallback message or hand off to the human/default channel.
- `decision=off_topic`: return the service-scope message and stop service-specific routing.
- `decision=risk`: return a block message and hand off `trace_id` to the security trace process.
- `decision=unauthorized`: do not execute any route. Log `trace_id`, `request_id`, `service_id`, and `route_key` if present for operator triage.

## Error Branches

- `401`: API key or `X-Key-Id` configuration error.
- `403`: `X-App-Id`, `X-Service-Id`, or key scope configuration error.
- `422`: request body or variable mapping error.
- `408`: client fallback or human handoff.
- `5xx`: client fallback or human handoff.
- `timeout`: client fallback or human handoff.

For `408`, `5xx`, and `timeout`, use no automatic retry loop. Dify should show a fixed fallback or hand off with `workflow_run_id`, `trace_id` when available, and `request_id`.

## Dry-Run Evidence

Before handoff, compare the Dify UI branch settings with `dify-smoke-matrix.json`
and `dify-smoke-matrix.md`, then record the `Dify workflow version identifier`
in `pilot-rehearsal-manifest.md`. Confirm the `intent_routing_api_key secret
variable` is masked and the workflow keeps `release_version` wherever the API
returns it.
