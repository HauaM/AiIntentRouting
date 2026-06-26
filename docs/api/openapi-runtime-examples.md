# Runtime API Examples

`POST /v1/intent-route`의 대표 응답 예시다. 성공 응답은 공통으로 `trace_id`,
`decision`, `release_version`을 포함하고, `confidence`는 decision에 따라 포함될 수 있다.

## Confident

```json
{
  "trace_id": "irt-20260625-000001",
  "request_id": "dify-workflow-run-001",
  "decision": "confident",
  "confidence": 0.94,
  "release_version": "rel-it-helpdesk-20260625-001",
  "intent_id": "intent-api-timeout",
  "route_key": "it.helpdesk.api_timeout"
}
```

## Clarify

```json
{
  "trace_id": "irt-20260625-000002",
  "request_id": "dify-workflow-run-002",
  "decision": "clarify",
  "confidence": 0.63,
  "release_version": "rel-it-helpdesk-20260625-001",
  "clarify_question": "어떤 timeout 문제인지 선택해 주세요.",
  "clarify": {
    "reason": "low_margin",
    "message": "어떤 timeout 문제인지 선택해 주세요.",
    "candidates": [
      {
        "intent_id": "intent-api-timeout",
        "route_key": "it.helpdesk.api_timeout",
        "display_name": "API timeout incident",
        "confidence": 0.63
      },
      {
        "intent_id": "intent-db-timeout",
        "route_key": "it.helpdesk.db_timeout",
        "display_name": "Database timeout",
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
  "release_version": "rel-it-helpdesk-20260625-001",
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
  "release_version": "rel-it-helpdesk-20260625-001",
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
  "release_version": "rel-it-helpdesk-20260625-001",
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
  "release_version": "rel-it-helpdesk-20260625-001",
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
  "release_version": "rel-it-helpdesk-20260625-001",
  "error": {
    "code": "VECTOR_STORE_UNAVAILABLE",
    "message": "Vector search is temporarily unavailable.",
    "category": "dependency_failure",
    "layer": "semantic_layer",
    "retryable": true
  }
}
```
