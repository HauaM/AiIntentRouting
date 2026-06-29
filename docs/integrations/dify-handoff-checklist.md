# Dify Handoff Checklist

Use this checklist before handing a Dify workflow to pilot operators. Attach the
completed evidence files to the pilot handoff ticket or release folder.

## HTTP Request Node Mapping

- [ ] Method is `POST`.
- [ ] URL points to `/v1/intent-route` for the target environment.
- [ ] Timeout: 8 seconds.
- [ ] `Authorization` is `Bearer {{intent_routing_api_key}}`.
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
- [ ] `readiness-report.md`
- [ ] threshold comparison Markdown
- [ ] screenshot or exported Dify workflow version identifier

## Manual UI Checks

- [ ] Dify secret variable hides `intent_routing_api_key`.
- [ ] `X-Request-Id` maps to `workflow_run_id`.
- [ ] Downstream nodes preserve `trace_id`, `request_id`, and `release_version`.
- [ ] risk branch does not call business route.
