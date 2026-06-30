# Dify Dry-Run Rehearsal

Use this procedure after the API smoke matrix passes and before pilot handoff.
The goal is to prove the Dify workflow wiring without exposing any API keys,
screen captures, or workflow exports in `pilot-rehearsal-manifest.md`.

Evidence template: `docs/integrations/dify-dry-run-evidence-template.md`

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

Before opening the Dify UI, copy
`docs/integrations/dify-dry-run-evidence-template.md` into the service evidence
directory, for example
`var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md`. Complete it while
running the manual UI dry-run and keep screenshots or workflow exports as
masked evidence files referenced by path. Attach the completed service-specific
copy under `var/evidence/${SERVICE_ID}/dify-ui/`; do not attach the source
template as pilot evidence.

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

## Release Closure Order

1. Copy `docs/integrations/dify-dry-run-evidence-template.md` to
   `var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md`.
2. Complete every decision branch and error branch row.
3. Record the Dify workflow version identifier.
4. Run `scripts/run_pilot_rehearsal.py` with `--dify-workflow-version` and
   `--dify-ui-evidence-path`.
5. Confirm `pilot-rehearsal-manifest.md` records only the version identifier
   and evidence path.
6. Copy the Dify evidence path and reviewer into
   `var/evidence/${SERVICE_ID}/release-ticket.md`; if blocked, also copy the
   condition owner and follow-up approval ID.
7. Copy the Dify status into
   `var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md`.

## Workflow Version And Evidence

Record the `Dify workflow version identifier` or export identifier after the
dry-run. If you keep screenshot or exported workflow evidence, inspect it before
handoff and confirm it does not expose secrets, tokens, or raw API keys.
Screenshots and workflow exports must show masked values only.

Pass the evidence path and version identifier to the rehearsal wrapper:

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

The rehearsal wrapper records only the Dify workflow version identifier and
evidence path. Screenshots and workflow exports must show masked values only. Do
not paste screenshot/export contents into pilot-rehearsal-manifest.md. If
`--dify-ui-evidence-path` is provided, the file must exist and is included in
the rehearsal secret scan.

Expected documented results:

- `pilot-rehearsal-manifest.md` includes the workflow version identifier.
- `pilot-rehearsal-manifest.md` includes the Dify UI evidence path.
- `pilot-rehearsal-manifest.md` does not inline screenshot or workflow export
  content.
- secret scan passes.

## Evidence Bundle

Attach these files to the pilot handoff ticket or release folder:

- `dify-smoke-matrix.json`
- `dify-smoke-matrix.md`
- `pilot-rehearsal-manifest.md`
- The masked screenshot/export file path recorded in the manifest.
- The recorded `Dify workflow version identifier`.
- Completed service-specific copy saved under
  `var/evidence/${SERVICE_ID}/dify-ui/dify-dry-run-evidence.md`.
