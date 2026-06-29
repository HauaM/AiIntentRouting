# Dify Dry-Run Evidence Template

Use this file as `docs/integrations/dify-dry-run-evidence-template.md` and save
the completed copy under `var/evidence/${SERVICE_ID}/dify-ui/`. The manual Dify
UI dry-run procedure is documented for operators; do not execute it from this
template.

## Target

- Service ID:
- Environment:
- Operator:
- Dry-run date:
- Intent Routing base URL:
- Timeout: 8 seconds.
- `workflow_run_id` source:

## HTTP Request Node Verification

| item | observed value or status | operator result |
| --- | --- | --- |
| Method is `POST` |  |  |
| URL points to `/v1/intent-route` |  |  |
| HTTP authorization header uses the approved `intent_routing_api_key secret variable` |  |  |
| `X-Key-Id` uses the approved key id variable |  |  |
| `X-App-Id` uses the approved Dify app id |  |  |
| `X-Service-Id` maps to the target service |  |  |
| `X-Request-Id` maps to `workflow_run_id` |  |  |
| Body `query` maps to user input |  |  |
| Body `user_context.workflow_run_id` maps to `workflow_run_id` |  |  |

## Decision Branch Results

| case | input or simulated condition | observed branch | trace_id | request_id | release_version | route execution allowed | operator result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| confident |  |  |  |  |  | yes |  |
| clarify |  |  |  |  |  | no |  |
| fallback |  |  |  |  |  | no |  |
| off_topic |  |  |  |  |  | no |  |
| risk |  |  |  |  |  | no |  |
| unauthorized |  |  |  |  |  | no |  |

## Error Branch Results

| case | input or simulated condition | observed branch | trace_id | request_id | release_version | route execution allowed | operator result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 401 | Invalid or missing API key binding |  |  |  |  | no |  |
| 403 | Invalid app, service, key id, or scope |  |  |  |  | no |  |
| 422 | Invalid body JSON or variable mapping |  |  |  |  | no |  |
| 408 | Simulated upstream request timeout; no automatic retry loop |  |  |  |  | no |  |
| 5xx | Simulated upstream server error; no automatic retry loop |  |  |  |  | no |  |
| timeout | Simulated Dify node timeout; no automatic retry loop |  |  |  |  | no |  |

## Secret Masking Review

- Screenshots and workflow exports must show masked values only.
- Record the masked screenshot or workflow export path:
- Confirm no raw token, API key, secret value, or unmasked key id appears in the
  evidence file.
- Confirm the `intent_routing_api_key secret variable` remains masked
  in the Dify UI.

## Workflow Version

- Dify workflow version identifier:
- Export identifier, if different:
- Confirm the identifier is the value passed to `--dify-workflow-version`.

## Evidence Paths

- Dify UI evidence path:
- API smoke matrix JSON:
- API smoke matrix Markdown:
- Rehearsal manifest: `pilot-rehearsal-manifest.md`
- The rehearsal wrapper records only the Dify workflow version identifier and
  evidence path.
- Do not paste screenshot/export contents into pilot-rehearsal-manifest.md.

## Operator Notes

- Note any branch mismatches, masked-evidence gaps, or required Dify follow-up:
- For `408`, `5xx`, and `timeout`, confirm route execution allowed = no and no
  automatic retry loop.

## Approval

- Operator approval:
- Reviewer approval:
- Secret scan passes:
