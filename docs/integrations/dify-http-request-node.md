# Dify HTTP Request Node Integration

이 문서는 Dify Workflow의 HTTP Request 노드에서 Intent Routing Service를 호출하고,
응답 `decision`에 따라 다음 노드로 분기하는 최소 운영 계약을 설명한다.

## HTTP Request 노드 설정

- Method: `POST`
- URL: `http://intent-routing.internal/v1/intent-route`
- Timeout: connect/read/write를 합산한 클라이언트 총 timeout이 6~8초가 되도록 설정한다.
- Workflow variable: Dify 시스템 변수 `{{sys.workflow_run_id}}`를 이전 노드에서 로컬 변수
  `{{workflow_run_id}}`로 매핑해 둔다. 아래 설정은 이 alias를 사용한다.

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
  "release_version": "rel-it-helpdesk-20260625-001",
  "intent_id": "intent-api-timeout",
  "route_key": "it.helpdesk.api_timeout"
}
```

- `decision=confident`: `route_key`로 분기한다. 예: `it.helpdesk.api_timeout`이면 API 장애 처리 Agent 또는 업무 API 호출 노드로 연결한다.
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
