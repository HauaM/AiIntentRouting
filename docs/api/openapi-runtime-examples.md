# Runtime API Examples

`POST /v1/intent-route`의 대표 응답 예시다. 성공 응답은 공통으로 `trace_id`,
`decision`, `release_version`을 포함하고, `confidence`는 decision에 따라 포함될 수 있다.

## Pilot Request

```http
POST /v1/intent-route
Authorization: Bearer <api_key>
X-Key-Id: key_live_<generated>
X-App-Id: dify-platform
X-Service-Id: it-helpdesk-pilot
X-Request-Id: dify-workflow-run-001
Content-Type: application/json
```

```json
{
  "query": "API timeout 500 에러가 납니다",
  "channel": "chat",
  "user_context": {
    "workflow_run_id": "dify-workflow-run-001"
  }
}
```

## Confident

```json
{
  "trace_id": "irt-20260625-000001",
  "request_id": "dify-workflow-run-001",
  "decision": "confident",
  "confidence": 0.94,
  "release_version": "rel-it-helpdesk-pilot-20260627-001",
  "intent_id": "it_api_timeout",
  "route_key": "it.api_timeout.manual_lookup"
}
```

## Clarify

```json
{
  "trace_id": "irt-20260625-000002",
  "request_id": "dify-workflow-run-002",
  "decision": "clarify",
  "confidence": 0.63,
  "release_version": "rel-it-helpdesk-pilot-20260627-001",
  "clarify_question": "어떤 IT 문의인지 선택해 주세요.",
  "clarify": {
    "reason": "low_margin",
    "message": "어떤 IT 문의인지 선택해 주세요.",
    "candidates": [
      {
        "intent_id": "it_api_timeout",
        "route_key": "it.api_timeout.manual_lookup",
        "display_name": "API timeout incident",
        "confidence": 0.63
      },
      {
        "intent_id": "it_password_reset",
        "route_key": "it.password_reset.self_service",
        "display_name": "Password reset",
        "confidence": 0.59
      }
    ]
  }
}
```

## Risk

```json
{
  "trace_id": "irt-20260625-000003",
  "request_id": "dify-workflow-run-003",
  "decision": "risk",
  "confidence": 1.0,
  "release_version": "rel-it-helpdesk-pilot-20260627-001",
  "risk": {
    "risk_type": "credential_secret",
    "action": "block",
    "message": "Blocked by risk policy: credential_secret"
  }
}
```

## Fallback

```json
{
  "trace_id": "irt-20260625-000004",
  "request_id": "dify-workflow-run-004",
  "decision": "fallback",
  "confidence": 0.31,
  "release_version": "rel-it-helpdesk-pilot-20260627-001",
  "fallback_policy": {
    "type": "client_fallback",
    "retryable": true,
    "recommended_action": "ask_for_rephrase",
    "message": "No confident intent match found."
  }
}
```

## Off Topic

```json
{
  "trace_id": "irt-20260625-000005",
  "request_id": "dify-workflow-run-005",
  "decision": "off_topic",
  "confidence": 1.0,
  "release_version": "rel-it-helpdesk-pilot-20260627-001",
  "fallback_policy": {
    "type": "fixed_message",
    "retryable": false,
    "recommended_action": "client_fallback",
    "message": "That request is outside the service policy."
  }
}
```

## Unauthorized

```json
{
  "trace_id": "irt-20260625-000006",
  "request_id": "dify-workflow-run-006",
  "decision": "unauthorized",
  "confidence": 0.91,
  "release_version": "rel-it-helpdesk-pilot-20260627-001",
  "fallback_policy": {
    "type": "client_fallback",
    "retryable": false,
    "recommended_action": "deny_route"
  }
}
```

## AUTHENTICATION_FAILED

```json
{
  "status": "error",
  "trace_id": "irt-20260625-000007",
  "request_id": "dify-workflow-run-007",
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "API key authentication failed.",
    "retryable": false
  }
}
```

## VECTOR_STORE_UNAVAILABLE

```json
{
  "status": "error",
  "trace_id": "irt-20260625-000008",
  "request_id": "dify-workflow-run-008",
  "release_version": "rel-it-helpdesk-pilot-20260627-001",
  "error": {
    "code": "VECTOR_STORE_UNAVAILABLE",
    "message": "Vector search is temporarily unavailable.",
    "category": "dependency_failure",
    "layer": "semantic_layer",
    "retryable": true
  }
}
```
