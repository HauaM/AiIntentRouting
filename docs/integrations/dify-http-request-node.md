# Dify HTTP Request Node Integration

이 문서는 Dify Workflow의 HTTP Request 노드에서 Intent Routing Service를 호출하고,
응답 `decision`에 따라 다음 노드로 분기하는 최소 운영 계약을 설명한다.

Checked template: `docs/integrations/dify-http-request-node-template.json`
Branch playbook: `docs/integrations/dify-branching-playbook.md`
Handoff checklist: `docs/integrations/dify-handoff-checklist.md`
Dry-run rehearsal: `docs/integrations/dify-dry-run-rehearsal.md`
Dry-run evidence template: `docs/integrations/dify-dry-run-evidence-template.md`

## HTTP Request 노드 설정

- Method: `POST`
- URL: `http://intent-routing.internal/v1/intent-route`
- Timeout: 8 seconds.
- Workflow variable: Dify 시스템 변수 `{{sys.workflow_run_id}}`를 이전 노드에서 로컬 변수
  `{{workflow_run_id}}`로 매핑해 둔다. 아래 설정은 이 alias를 사용한다.
- Secret variable: `intent_routing_api_key secret variable` is masked in the Dify UI.

Headers:

```http
Authorization: Bearer {{intent_routing_api_key}}
X-App-Id: dify-platform
X-Service-Id: {{service_id}}
X-Key-Id: {{intent_routing_key_id}}
X-Request-Id: {{workflow_run_id}}
Content-Type: application/json
```

Body JSON:

```json
{
  "query": "{{user_query}}",
  "channel": "chat",
  "user_context": {
    "workflow_run_id": "{{workflow_run_id}}"
  }
}
```

## Decision 분기

HTTP 200 응답은 `decision`으로 분기한다.

```json
{
  "trace_id": "irt-...",
  "decision": "confident",
  "confidence": 0.94,
  "release_version": "rel-it-helpdesk-pilot-20260627-001",
  "intent_id": "it_api_timeout",
  "route_key": "it.api_timeout.manual_lookup"
}
```

- `decision=confident`: `route_key`로 분기한다. 예: `it.api_timeout.manual_lookup`이면 API 장애 처리 Agent 또는 업무 API 호출 노드로 연결한다.
- `decision=clarify`: Answer 노드에서 `clarify_question`을 출력하고, `clarify.candidates`를 선택지로 보여준다.
- `decision=fallback`: 고정 fallback 메시지를 반환하거나 상담원/기본 채널로 handoff한다.
- `decision=off_topic`: 서비스별 고정 메시지를 반환하거나 클라이언트의 기본 fallback 경로로 보낸다.
- `decision=risk`: 차단 메시지를 반환하거나 보안 검토 route로 보낸다.
- `decision=unauthorized`: route를 실행하지 않는다. `trace_id`, `request_id`, `service_id`를 로그에 남기고 handoff한다.

## HTTP 오류 처리

HTTP `401`, `403`, `422`는 route 실행 경로가 아니라 인증, 권한, 요청 형식 설정 오류로 triage한다.
API Key, `X-App-Id`, `X-Service-Id`, `X-Key-Id`, Body JSON 매핑을 먼저 확인한다.

HTTP `5xx`, `408`, 또는 timeout이면 Dify에서 고정 fallback 메시지를 반환하거나 human handoff로 전환한다.
이 경우 route 실행을 재시도하지 말고, `X-Request-Id={{workflow_run_id}}`와 Dify 실행 로그를 함께 남긴다.

## Local Pilot Smoke

After seeding:

```bash
uv run python scripts/smoke_runtime_dify.py \
  --base-url http://127.0.0.1:8000 \
  --state "${STATE_PATH}" \
  --query "API timeout 500 에러가 납니다" \
  --expect-decision confident \
  --expect-route-key it.api_timeout.manual_lookup \
  --request-id dify-smoke-local-001 \
  --timeout-seconds 8 \
  --output var/evidence/${SERVICE_ID}/dify-smoke-confident.json
```

## Dry-Run Rehearsal Metadata

During the Dify UI dry-run, complete
`docs/integrations/dify-dry-run-evidence-template.md`, record the `Dify
workflow version identifier` or export identifier, and pass the masked
screenshot/export path to `scripts/run_pilot_rehearsal.py` with
`--dify-ui-evidence-path`.

The rehearsal wrapper records only the Dify workflow version identifier and
evidence path. Screenshots and workflow exports must show masked values only.
Do not paste screenshot/export contents into pilot-rehearsal-manifest.md.

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

## Dify Variable Mapping

아래 표는 원래 Dify 시스템 변수 이름을 기준으로 적었고, 위 HTTP Request 예시는 사전 매핑 후
로컬 alias인 `{{workflow_run_id}}`를 사용한다.

| Intent Routing field | Dify source |
| --- | --- |
| `Authorization` | Secret variable `intent_routing_api_key` |
| `X-Key-Id` | Secret or environment variable `intent_routing_key_id` |
| `X-App-Id` | Literal `dify-platform` |
| `X-Service-Id` | Workflow variable `service_id` |
| `X-Request-Id` | `{{sys.workflow_run_id}}` |
| `query` | User input variable |
| `user_context.workflow_run_id` | `{{sys.workflow_run_id}}` |

## Recommended Dify Branches

| HTTP status | Branch |
| --- | --- |
| `200` with `decision=confident` | Route by `route_key` |
| `200` with `decision=clarify` | Answer node with `clarify_question` and candidate buttons |
| `200` with `decision=fallback` | Fixed fallback or handoff |
| `200` with `decision=off_topic` | Service-scope message |
| `200` with `decision=risk` | Block message and security trace |
| `200` with `decision=unauthorized` | Do not execute route; handoff with `trace_id` |
| `401`, `403`, `422` | Configuration error triage |
| `408`, `5xx`, timeout | Client fallback or human handoff |
