# Dify Dry-Run Rehearsal

Use this procedure after the API smoke matrix passes and before pilot handoff.
The goal is to prove the Dify workflow wiring without exposing any API keys,
screen captures, or workflow exports in `pilot-rehearsal-manifest.md`.

## Inputs

Set the target service and API endpoint before opening Dify:

```bash
export SERVICE_ID="it-helpdesk-pilot"
export STATE_PATH="var/evidence/${SERVICE_ID}/pilot.state.secret.json"
export TARGET_URL="http://intent-routing.internal/v1/intent-route"
```

Use the target URL for the Dify HTTP Request node and keep `STATE_PATH` outside
the evidence bundle. The state file is secret material and must not be attached.

## HTTP Request Node

Apply HTTP request node template values from
`docs/integrations/dify-http-request-node-template.json`.

- Method: `POST`.
- URL: `${TARGET_URL}`.
- Timeout: 8 seconds.
- `Authorization` uses the `intent_routing_api_key secret variable`.
- `X-Key-Id` uses `intent_routing_key_id`.
- `X-App-Id` is `dify-platform`.
- `X-Service-Id` maps to `${SERVICE_ID}`.
- `X-Request-Id` maps to `workflow_run_id`.
- Body `query` maps to the user input variable.
- Body `user_context.workflow_run_id` maps to `workflow_run_id`.

Verify Dify masks the `intent_routing_api_key secret variable` and key id value
in the UI. Screenshots or workflow exports must show masked values only.

## API Smoke Matrix

Run or inspect the API smoke matrix before Dify UI dry-run. Attach both files to
the evidence bundle:

- `dify-smoke-matrix.json`
- `dify-smoke-matrix.md`

The matrix must show representative API behavior for `confident`, `clarify`,
`fallback`, `off_topic`, `risk`, `unauthorized`, `401`, `403`, `422`, `408`,
`5xx`, and `timeout`.

## Dify UI Dry-Run

Run representative queries in the Dify UI for these successful HTTP 200
decisions:

- `confident`: confirm downstream routing uses `route_key` and preserves
  `trace_id`, `request_id`, and `release_version`.
- `clarify`: confirm the answer node shows `clarify_question` and candidates.
- `fallback`: confirm the approved fallback or human handoff path runs.
- `off_topic`: confirm service-specific routing stops.
- `risk`: confirm the block path runs and no business route is called.

For `unauthorized`, confirm no business route runs and the workflow preserves
`trace_id`, `request_id`, and service context for operator triage.

For `401`, `403`, `422`, `408`, `5xx`, and `timeout`, verify the configured
branches against `dify-smoke-matrix.md` and Dify branch settings. `408`, `5xx`,
and `timeout` must use no automatic retry loop; show a fixed fallback or human
handoff instead.

## Workflow Version And Evidence

Record the `Dify workflow version identifier` or export identifier after the
dry-run. If you keep screenshot or exported workflow evidence, inspect it before
handoff and confirm it does not expose secrets, tokens, or raw API keys.

Pass the evidence path and version identifier to the rehearsal wrapper:

```bash
uv run python scripts/run_pilot_rehearsal.py \
  --mode local \
  --base-url http://127.0.0.1:8000 \
  --service-id "${SERVICE_ID}" \
  --environment dev \
  --state-path "${STATE_PATH}" \
  --out-dir "var/evidence/${SERVICE_ID}/rehearsal" \
  --dify-workflow-version "dify-workflow-export-20260629-001" \
  --dify-ui-evidence-path "var/evidence/${SERVICE_ID}/dify-ui-export.md"
```

The wrapper records only the `Dify workflow version identifier` and evidence
path in `pilot-rehearsal-manifest.md`. It does not inline raw screenshot/export
content. If `--dify-ui-evidence-path` is provided, the file must exist and is
included in the rehearsal secret scan.

## Evidence Bundle

Attach these files to the pilot handoff ticket or release folder:

- `dify-smoke-matrix.json`
- `dify-smoke-matrix.md`
- `pilot-rehearsal-manifest.md`
- The masked screenshot/export file path recorded in the manifest.
- The recorded `Dify workflow version identifier`.
