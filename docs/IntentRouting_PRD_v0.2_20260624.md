# Intent Routing Service PRD v0.2

작성일: 2026-06-24  
상태: Draft  
대상: 금융권 폐쇄망 공통 Intent Routing Service
회신 3 반영일: 2026-06-25

---

## 1. 목적

금융권 폐쇄망 환경에서 여러 AI Agent Platform, 챗봇, 내부 업무 시스템이 공통으로 사용할 수 있는 **Intent Routing Service**를 제공한다.

이 서비스는 사용자 질문에 답변을 생성하지 않는다. 대신 사용자 질의를 받아 다음을 판단하고, 후속 시스템이 안정적으로 분기할 수 있는 라우팅 결과를 반환한다.

```text
이 질문은 어떤 의도인가?
이 서비스에서 허용된 의도인가?
확정 가능한가?
사용자에게 명확화 질문이 필요한가?
서비스 범위 밖인가?
위험 또는 차단 대상인가?
어느 후속 업무 흐름으로 보내야 하는가?
```

MVP의 핵심 목표는 개발자가 ML, embedding, threshold를 몰라도 Intent Catalog와 예시를 등록하고, CSV 테스트로 검증한 뒤, 운영 반영 가능한 release를 만들 수 있는지 검증하는 것이다.

---

## 2. 문제 정의

현재 여러 AI 서비스가 각자 의도분류를 구현하면 다음 문제가 발생한다.

| 문제 | 설명 |
| --- | --- |
| 중복 구현 | 챗봇, Agent, 내부 시스템마다 의도분류 로직을 별도로 만든다. |
| 품질 편차 | 서비스별 threshold, fallback, off-topic 기준이 달라진다. |
| 운영 추적 어려움 | 오분류 로그, 테스트셋, 변경 이력이 시스템별로 흩어진다. |
| 보안 통제 약화 | 서비스별 허용 Intent와 route 권한을 일관되게 검증하기 어렵다. |
| 개선 루프 부재 | 실패 케이스를 positive/negative example로 반영하고 재검증하는 흐름이 표준화되지 않는다. |

금융권 환경에서는 단순히 intent를 맞히는 것보다 다음 질문에 답할 수 있어야 한다.

```text
누가 어떤 Intent 설정을 바꿨는가?
어떤 테스트셋으로 운영 반영을 검증했는가?
어떤 release_version이 운영 중인가?
해당 서비스가 그 route_key를 호출할 권한이 있는가?
위험 질의와 서비스 범위 밖 질의는 어떤 기준으로 처리되었는가?
특정 오분류가 발생했을 때 당시 설정을 재현할 수 있는가?
```

---

## 3. 비목표

MVP에서 다음은 목표로 하지 않는다.

| 비목표 | 설명 |
| --- | --- |
| 답변 생성 | Intent Routing Service는 답변을 생성하지 않고 decision과 route 정보를 반환한다. |
| Agent 실행 | 후속 Dify Flow, Agent, Tool, 업무 API 실행은 client system이 담당한다. |
| 학습형 classifier 운영 | 초기 labeled data가 부족하므로 모델 학습/재학습/배포 체계는 MVP에서 제외한다. |
| LLM judge 기본 경로 | latency, 재현성, 폐쇄망 운영 부담 때문에 MVP 기본 라우팅 경로에는 넣지 않는다. |
| 자동 threshold 최적화 | 운영 데이터가 쌓인 이후 검토한다. |
| 관리 콘솔 UI | MVP는 API-Only로 시작한다. 관리 콘솔 화면은 v1 이후 검토한다. |
| 다중 Agent Platform 연계 | 최초 연계 대상은 Dify Platform으로 제한한다. |
| HNSW 인덱스 운영 | MVP는 pgvector Exact Search로 시작하고, 데이터 증가 후 HNSW를 검토한다. |
| HMAC 요청 서명 | MVP는 Bearer API Key와 폐쇄망 보안 통제를 기본으로 하고, HMAC은 v1.1 후보로 둔다. |

---

## 4. 주요 사용자

| 사용자 | 주요 목적 | 권한/관심사 |
| --- | --- | --- |
| 시스템 관리자 | 서비스 등록, API Key 발급, 기본 정책 설정, release 관리 | 전체 service_id 관리, prod 반영 권한, key revoke/rotation |
| 서비스 개발자 | Intent Catalog와 example을 관리하고 CSV 테스트를 실행 | 담당 service_id 범위 내 catalog/test/log 조회 |
| 서비스 운영자 | 운영 로그를 확인하고 오분류 케이스를 개선 요청 | 담당 서비스의 masked log, test result, release 이력 조회 |
| 감사/보안 담당자 | 원문 조회, key 사용, release 변경 이력 감사 | 인가된 경우 raw query 조회, 조회 사유 기록 필수 |
| Client System | Dify Platform, 챗봇, 내부 업무 시스템 | API Key로 `/v1/intent-route` 호출, response 기반 후속 분기 |

MVP의 최초 client system은 **Dify Platform**이다. Dify workflow에서는 HTTP Request node로 Intent Routing Service API를 호출하고, 후속 If-Else, Question Classifier, Tool, Answer node에서 `decision`, `intent_id`, `route_key`를 사용한다.

MVP의 관리 기능은 **API-Only**로 제공한다. 서비스 등록, API Key 발급, Intent Catalog 관리, CSV 테스트 실행, release_version 생성은 관리 API로 수행하며, 별도 관리 콘솔 UI는 MVP 범위에서 제외한다.

---

## 5. 핵심 사용자 흐름

### 5.1 서비스 온보딩 흐름

```text
1. 시스템 관리자가 service_id를 등록한다.
2. 시스템 관리자가 app_id와 environment를 지정한다.
3. API Key를 environment + app_id + service_id 단위로 발급한다.
4. 담당 개발자에게 service_id 접근 권한을 부여한다.
5. Dify workflow의 HTTP Request node에 endpoint, header, body, timeout을 설정한다.
```

MVP에서 위 작업은 관리 콘솔이 아니라 관리 API로 수행한다.

MVP 권장 호출 형태는 다음과 같다.

```http
POST /v1/intent-route
Authorization: Bearer <api_key>
X-App-Id: dify-platform
X-Service-Id: it-helpdesk
X-Key-Id: key_live_20260624_001
X-Request-Id: {{workflow_run_id}}
Content-Type: application/json
```

```json
{
  "query": "{{user_query}}",
  "channel": "dify",
  "user_context": {
    "locale": "ko-KR"
  }
}
```

### 5.2 Intent 설정 및 검증 흐름

```text
1. 개발자가 담당 service_id의 Intent Catalog를 생성한다.
2. Intent 3~5개를 등록한다.
3. Intent별 route_key를 매핑한다.
4. positive example과 negative example을 등록한다.
5. 필요 시 include/exclude keyword를 등록한다.
6. 시스템이 BGE-M3 embedding을 생성해 pgvector에 저장한다.
7. 개발자가 CSV 테스트셋을 업로드한다.
8. 시스템이 case_type 기반 기대값과 gate 기준을 계산한다.
9. PASS/FAIL/REVIEW 결과를 확인한다.
10. 실패 케이스를 example 또는 keyword로 보완한다.
11. 재테스트한다.
12. gate를 만족하면 release_version을 생성하고 운영 반영한다.
```

### 5.3 Runtime API 흐름

```text
1. Client system이 사용자 질의를 `/v1/intent-route`로 보낸다.
2. Auth Layer가 app_id, service_id, API Key, key scope를 검증한다.
3. Policy Layer가 risk 정책을 먼저 검사한다.
4. 서비스별 허용 Intent와 route_key 권한을 로드한다.
5. Candidate Layer가 include/exclude keyword로 후보를 보정한다.
6. Semantic Layer가 positive/negative example 유사도를 계산한다.
7. Decision Layer가 confidence, margin, negative_penalty로 decision을 산출한다.
8. 응답과 trace log에 release_version과 판정 근거를 남긴다.
9. Client system이 decision과 route_key를 기준으로 후속 workflow를 실행한다.
10. 내부 오류가 발생하면 decision이 아니라 표준 error response를 반환하고, Dify workflow는 timeout/5xx fallback으로 처리한다.
```

응답 예시는 다음과 같다.

```json
{
  "trace_id": "irt-20260624-000001",
  "decision": "confident",
  "domain": "IT",
  "intent_id": "it_api_timeout",
  "confidence": 0.87,
  "route_key": "it.api_timeout.manual_lookup",
  "fallback_policy": null,
  "release_version": "rel-it-helpdesk-20260624-001"
}
```

### 5.4 운영 개선 흐름

```text
1. 운영자가 masked query 기준으로 오분류 로그를 확인한다.
2. 필요한 경우 인가된 사용자가 원문 조회를 요청한다.
3. 조회 사유와 trace_id를 감사 로그에 남긴다.
4. 실패 케이스를 CSV 테스트셋 또는 negative example에 반영한다.
5. 재테스트 후 새 release_version으로 운영 반영한다.
```

---

## 6. Routing Decision Model

### 6.1 Decision 값

| decision | 의미 | 기본 처리 |
| --- | --- | --- |
| `confident` | Intent를 확정할 수 있음 | `intent_id`, `route_key` 반환 |
| `clarify` | 후보 Intent가 2개 이상이고 점수 차이가 작아 사용자 확인 필요 | 후보 목록, 사용자 확인 질문, clarify reason 반환 |
| `fallback` | 적절한 후보 Intent가 없음 | fallback policy 반환 |
| `off_topic` | 해당 service_id의 업무 범위 밖 질의 | 서비스별 정책에 따른 고정 안내, 상담원 연결, 또는 client fallback |
| `risk` | 범용 위험 정책 조건에 걸림 | 차단 또는 보안 정책 route |
| `unauthorized` | 호출 서비스가 해당 Intent 또는 route_key 권한이 없음 | 403 성격의 decision/log 처리 |

### 6.2 판정 우선순위

```text
1. risk
2. unauthorized
3. off_topic
4. confident
5. clarify
6. fallback
```

`risk`는 일반 Intent Routing보다 먼저 검사한다. `unauthorized`는 후보 Intent 또는 route_key가 산출된 뒤 service policy와 비교해 판정할 수 있다.

`off_topic`은 MVP에서 범용 선판정 정책으로 두지 않는다. 여러 서비스가 같은 Intent Routing Service를 사용하므로 서비스마다 업무 범위가 다르기 때문이다. MVP에서 `off_topic`은 service_id별 테스트셋, fallback 정책, catalog 경계 설정을 통해 판정한다.

### 6.3 Threshold 프리셋

Threshold는 raw cosine similarity가 아니라, 키워드 보정, negative penalty, semantic similarity를 합성한 **내부 confidence score**의 정규화 기준으로 사용한다. 개발자에게는 숫자 튜닝 대신 다음 세 가지 프리셋을 제공한다.

| 프리셋 | threshold | 한글 멘트 | 사용 상황 |
| --- | --- | --- | --- |
| `strict` | 100% | 확실한 경우만 분류 | 오분류 비용이 크고 fallback/clarify가 더 안전한 서비스 |
| `balanced` | 80% | 기준에 맞으면 분류 | 일반적인 업무 챗봇과 Dify workflow 기본값 |
| `exploratory` | 60% | 넓게 후보 탐색 | 초기 테스트, Intent 후보 탐색, 운영 전 튜닝 |

MVP 기본값은 `balanced` 80%로 둔다. threshold는 service_id 단위 또는 test_run 단위로 바꿔 테스트할 수 있어야 하며, CSV 테스트 결과는 어떤 threshold 프리셋으로 실행됐는지 기록한다.

### 6.4 Clarify 응답 형식

`clarify`는 client system이 사용자에게 바로 확인 질문을 던질 수 있도록 구조화해서 반환한다. Dify workflow에서는 `clarify_question`을 Answer node에 표시하고, 사용자의 후속 응답을 다시 Intent Routing Service에 전달할 수 있다.

```json
{
  "trace_id": "irt-20260625-000031",
  "decision": "clarify",
  "domain": "IT",
  "intent_id": null,
  "confidence": 0.78,
  "route_key": null,
  "clarify_question": "문의하신 내용이 두 가지 업무로 해석될 수 있습니다. 어떤 업무에 가까운지 선택해 주세요.",
  "fallback_policy": {
    "type": "ask_user",
    "retryable": true
  },
  "clarify": {
    "reason": "top_candidates_close",
    "message": "문의하신 내용이 두 가지 업무로 해석될 수 있습니다. 어떤 업무에 가까운지 선택해 주세요.",
    "candidates": [
      {
        "intent_id": "it_api_timeout",
        "display_name": "API Timeout 문의",
        "route_key": "it.api_timeout.manual_lookup",
        "confidence": 0.78
      },
      {
        "intent_id": "insurance_claim_error",
        "display_name": "보험금 청구 화면 오류",
        "route_key": "insurance.claim_error.troubleshoot",
        "confidence": 0.75
      }
    ]
  },
  "release_version": "rel-it-helpdesk-20260625-001"
}
```

MVP에서 `clarify.candidates`는 최대 3개까지 반환한다. candidate에는 `intent_id`, `display_name`, `route_key`, `confidence`를 포함한다. 후보 route_key는 사용자가 선택하기 전에는 실행하지 않는다.

### 6.5 Risk 판정 범주

`risk`는 service_id와 무관하게 공통 적용 가능한 범용 위험 정책으로 먼저 검사한다. MVP의 risk 범주는 다음과 같다.

| risk_type | 설명 |
| --- | --- |
| `abuse` | 욕설, 비방, 협박 |
| `dangerous_command` | 서버, DB, 파일, 시스템 손상 가능 명령 |
| `sensitive_data` | 개인정보, 금융정보, 내부기밀 요구 |
| `credential_secret` | 비밀번호, API Key, 토큰, 인증서 요구 |
| `unauthorized_access` | 권한 없는 서비스 또는 데이터 접근 요청 |
| `prompt_injection` | 지침 무시, 프롬프트 탈취, 정책 우회 |
| `fraud_or_illegal` | 사기, 피싱, 불법행위, 규정 회피 조력 |

`risk` 응답은 `risk_type`과 차단 정책을 포함한다.

```json
{
  "trace_id": "irt-20260625-000044",
  "decision": "risk",
  "intent_id": null,
  "confidence": 1.0,
  "route_key": null,
  "risk": {
    "risk_type": "credential_secret",
    "action": "block",
    "message": "인증 정보나 비밀키 요청은 처리할 수 없습니다."
  },
  "release_version": "rel-it-helpdesk-20260625-001"
}
```

### 6.6 내부 scoring 개념

MVP 내부 모델은 다음 값을 사용한다.

| 값 | 설명 |
| --- | --- |
| `confidence` | 선택된 Intent의 최종 신뢰도 |
| `margin` | 1위 Intent와 2위 Intent 점수 차이 |
| `threshold` | `confident` 판정을 위한 최소 점수 |
| `negative_penalty` | negative example 유사도에 따른 감점 |
| `keyword_boost` | include keyword 일치에 따른 후보 보정 |
| `keyword_penalty` | exclude keyword 일치에 따른 후보 감점 |

기본 개발자 인터페이스와 API 문서에는 threshold, embedding, margin, vector search 같은 용어를 전면에 노출하지 않는다. 개발자는 다음 언어로 설정한다.

```text
이 Intent에 해당하는 질문 예시
이 Intent로 가면 안 되는 헷갈리는 질문 예시
이 Intent로 분류되면 보낼 업무 흐름
애매하면 사용자에게 확인
맞는 Intent가 없으면 fallback
```

### 6.7 MVP 엔진 구성

MVP 라우팅 엔진은 하이브리드 구조를 사용한다.

```text
Auth Layer
-> Policy Layer
-> Candidate Layer
-> Semantic Layer
-> Decision Layer
-> Response + Trace Log
```

세부 구성은 다음과 같다.

| Layer | 역할 |
| --- | --- |
| Auth Layer | app_id, API Key, service_id, key scope 확인 |
| Policy Layer | 범용 risk 우선 검사, unauthorized 정책 검사, service_id별 off_topic 정책 적용 |
| Candidate Layer | service별 allowed intent filtering, include/exclude keyword 보정 |
| Semantic Layer | BGE-M3 dense embedding 기반 positive/negative example 유사도 계산 |
| Decision Layer | confidence, margin, negative_penalty 기반 decision 산출 |
| Trace Log | trace_id, release_version, decision, score, route_key, latency 기록 |

MVP 기본 경로에서 LLM 후보 판정은 필수로 사용하지 않는다. REVIEW 케이스 분석, 관리자 테스트, 특정 서비스 선택 기능으로 확장할 수 있는 여지만 남긴다.

### 6.8 내부 오류 응답 형식

Intent Routing Service 내부 오류는 `clarify`, `fallback`, `risk` 같은 routing decision으로 표현하지 않는다. 이 값들은 사용자 질의에 대한 정상적인 라우팅 판정 결과이며, 서비스 장애나 의존성 오류와 섞으면 후속 Dify workflow가 원인을 잘못 해석할 수 있다.

내부 오류는 HTTP status와 표준 error envelope로 반환한다. 가능한 경우 모든 오류 응답에 `trace_id`와 `request_id`를 포함한다.

```json
{
  "trace_id": "irt-20260625-000081",
  "request_id": "dify-run-20260625-0091",
  "status": "error",
  "error": {
    "code": "VECTOR_STORE_UNAVAILABLE",
    "message": "일시적으로 의도 분류를 처리할 수 없습니다.",
    "retryable": true,
    "category": "dependency_failure",
    "layer": "semantic_layer",
    "support_message": "pgvector 조회 중 timeout이 발생했습니다.",
    "safe_detail": "vector search timeout",
    "fallback_policy": {
      "type": "client_fallback",
      "recommended_action": "show_fixed_message_or_handoff"
    }
  },
  "release_version": "rel-it-helpdesk-20260625-001"
}
```

오류 응답 원칙은 다음과 같다.

| 원칙 | 내용 |
| --- | --- |
| decision 미사용 | 내부 오류에서는 `decision`을 반환하지 않는다. |
| 민감정보 비노출 | stack trace, DB connection string, API Key, raw query는 응답에 포함하지 않는다. |
| trace 우선 | client와 운영자가 같은 `trace_id`로 로그를 찾을 수 있어야 한다. |
| 재시도 표시 | 일시 장애는 `retryable=true`, 설정/권한 문제는 `retryable=false`로 반환한다. |
| release 허용 | 오류 시점에 active release를 확인했으면 `release_version`을 포함하고, 확인 전 오류면 `null`로 둔다. |
| Dify fallback | 5xx, timeout, `retryable=true` 오류는 Dify workflow에서 고정 fallback 응답 또는 상담원 연결로 처리한다. |

MVP 오류 코드는 다음을 기본으로 한다.

| HTTP status | error.code | category | retryable | 의미 |
| --- | --- | --- | --- | --- |
| 400 | `INVALID_REQUEST` | `client_error` | false | 요청 body, header, query 형식 오류 |
| 401 | `AUTHENTICATION_FAILED` | `auth_error` | false | API Key 누락 또는 인증 실패 |
| 403 | `SERVICE_SCOPE_DENIED` | `auth_error` | false | app_id/service_id/key scope 불일치 |
| 404 | `ACTIVE_RELEASE_NOT_FOUND` | `configuration_error` | false | service_id의 active release 없음 |
| 408 | `ROUTING_TIMEOUT` | `timeout` | true | 내부 처리 목표 시간을 초과 |
| 429 | `RATE_LIMITED` | `throttle` | true | app_id/service_id rate limit 초과 |
| 500 | `INTERNAL_ERROR` | `internal_error` | true | 예상하지 못한 서버 오류 |
| 503 | `EMBEDDING_MODEL_UNAVAILABLE` | `dependency_failure` | true | embedding 모델 로드 또는 추론 불가 |
| 503 | `VECTOR_STORE_UNAVAILABLE` | `dependency_failure` | true | PostgreSQL/pgvector 조회 불가 |
| 503 | `POLICY_LOAD_FAILED` | `configuration_error` | false | policy_version 또는 catalog snapshot 로드 실패 |

`support_message`는 운영 로그와 내부 관리 API에서만 상세하게 볼 수 있어야 한다. 외부 client에는 `message`, `code`, `retryable`, `trace_id` 중심으로 노출한다.

---

## 7. Intent Catalog / Example Model

### 7.1 Intent Catalog

Intent Catalog는 service_id 단위로 관리한다. 하나의 service_id는 여러 Intent를 가질 수 있고, 각 Intent는 후속 시스템이 이해할 수 있는 route_key와 연결된다.

MVP Intent 필수 필드는 다음과 같다.

| 필드 | 설명 |
| --- | --- |
| `service_id` | Intent가 속한 서비스 |
| `intent_id` | 서비스 내 고유 Intent ID |
| `domain` | 업무 도메인 |
| `display_name` | 개발자 화면 표시명 |
| `description` | Intent 설명 |
| `route_key` | Dify Flow, Agent Flow, 업무 API 등 후속 처리 경로 |
| `status` | draft, active, deprecated |
| `include_keywords` | 후보 보정용 포함 키워드 |
| `exclude_keywords` | 오분류 방지용 제외 키워드 |
| `created_by` / `updated_by` | 변경 사용자 |

### 7.2 route_key 네이밍 규칙

`route_key`는 후속 Dify Flow, Agent Flow, 업무 API 분기를 위한 안정적인 문자열 계약이다. `service_id`로 이미 서비스 범위가 정해지므로, `route_key`는 service_id 내부에서 고유하게 관리한다.

기본 형식은 다음과 같다.

```text
<domain>.<intent>.<action>
```

필요하면 네 번째 segment로 variant를 붙일 수 있다.

```text
<domain>.<intent>.<action>.<variant>
```

네이밍 규칙은 다음과 같다.

| 규칙 | 내용 |
| --- | --- |
| 문자 | 영문 소문자, 숫자, underscore, dot만 사용 |
| 형식 | dot으로 구분된 3~4개 segment |
| 금지 | 한글, 공백, 대문자, 환경명, 버전명 포함 금지 |
| 범위 | `service_id + route_key` 조합이 고유해야 함 |
| 안정성 | 운영 반영 후 의미를 바꾸지 않음. 변경이 필요하면 새 route_key 생성 |
| 이력 | route_key 추가, 변경, 폐기는 intent_catalog_version에 기록 |

권장 정규식은 다음과 같다.

```text
^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2,3}$
```

예시는 다음과 같다.

| service_id | intent_id | route_key |
| --- | --- | --- |
| `it-helpdesk` | `it_api_timeout` | `it.api_timeout.manual_lookup` |
| `it-helpdesk` | `it_password_reset` | `it.password_reset.self_service` |
| `insurance` | `insurance_claim_guide` | `insurance.claim.guide` |
| `loan` | `loan_limit_check` | `loan.limit.check` |

### 7.3 Positive / Negative Example

개발자는 모델을 직접 학습시키는 것이 아니라 example을 관리한다.

| 구분 | 의미 |
| --- | --- |
| positive example | 이 Intent에 해당하는 질문 예시 |
| negative example | 이 Intent로 가면 안 되는 헷갈리는 질문 예시 |

예시는 다음 메타데이터를 가진다.

| 필드 | 설명 |
| --- | --- |
| `example_id` | example 고유 ID |
| `service_id` | 서비스 ID |
| `intent_id` | 연결 Intent |
| `example_type` | positive 또는 negative |
| `text_raw_encrypted` | 원문. 암호화 저장 |
| `text_masked` | 조회/검색용 마스킹 텍스트 |
| `embedding` | BGE-M3 dense vector, 1024 dimension |
| `source` | manual, test_failure, runtime_review 등 |
| `test_case_id` | 테스트 실패에서 유입된 경우 연결 ID |
| `created_by` | 생성 사용자 |
| `approved` | 운영 반영 가능 여부 |

### 7.4 Embedding / Vector Store

MVP 기본 embedding 모델은 **BGE-M3**다.

| 항목 | 결정 |
| --- | --- |
| 모델 | BGE-M3 |
| 운영 형태 | CPU-only |
| 사용 방식 | dense embedding만 사용 |
| 기본 최대 입력 길이 | 256 token |
| 최대 입력 길이 변경 | 시스템 관리자가 서비스별로 변경 가능 |
| vector dimension | 1024 |
| vector store | PostgreSQL + pgvector |
| 유사도 | cosine similarity |
| MVP 인덱스 전략 | Exact Search |

기본 최대 입력 길이를 256 token으로 두는 이유는 Intent Routing의 주 입력이 짧은 사용자 질의이기 때문이다. 긴 입력이 필요한 서비스는 시스템 관리자가 512, 1024 또는 그 이상으로 조정할 수 있다.

MVP batch 기준은 다음과 같다.

| 작업 | 기본 기준 |
| --- | --- |
| 실시간 API | batch size 1~8 |
| 동적 micro-batching | 최대 batch 16, 대기 10~30ms 이내 |
| CSV 테스트 | batch size 16~64 |
| Intent example 재색인 | batch size 16~64 |
| 1024 token 이상 긴 입력 | batch size 4~16 |
| 8192 token 실험 | batch size 1~4부터 시작 |

---

## 8. 테스트셋 / 평가 기준

### 8.1 CSV 테스트 목적

CSV 테스트는 단순 업로드 기능이 아니라 **운영 반영 게이트**다.

```text
설정 변경
-> CSV 테스트 실행
-> PASS/FAIL/REVIEW 확인
-> 기준 미달 시 운영 반영 차단
-> 실패 케이스 개선
-> 재테스트
-> release_version 생성
-> 운영 반영
```

테스트 실행 시 threshold 프리셋을 선택할 수 있어야 한다. 같은 CSV 테스트셋을 `strict` 100%, `balanced` 80%, `exploratory` 60%로 각각 실행해 PASS/FAIL/REVIEW 변화를 비교할 수 있어야 하며, 모든 test_run은 사용한 threshold 프리셋을 저장한다.

### 8.2 개발자용 CSV 형식

MVP 개발자용 CSV는 단순하게 유지한다.

```csv
case_id,query,expected_intent,case_type,memo
C001,보험금 청구 방법 알려줘,insurance_claim,positive,정상 보험금 청구 문의
C002,보험금 청구 화면에서 500 에러가 나요,it_error,confusing,보험금 청구 단어가 있지만 실제로는 IT 오류
C003,시스템 해킹 방법 알려줘,,risk,위험 질의
C004,오늘 날씨 어때,,off_topic,서비스 범위 밖
C005,대출 한도 조회해줘,,fallback,현재 서비스에 없는 intent
```

개발자는 다음 두 가지만 판단한다.

```text
1. 이 질문은 어떤 종류인가?
   - positive
   - confusing
   - risk
   - off_topic
   - fallback

2. 업무 질문이면 어느 expected_intent로 가야 하는가?
```

`expected_decision`, `expected_route_key`, `priority`, `must_pass`는 개발자용 CSV에 넣지 않는다. 시스템이 `case_type`과 Intent Catalog를 기준으로 내부 기대값과 gate 기준을 계산한다.

### 8.3 case_type별 내부 기대값

| case_type | 개발자 의미 | 시스템 내부 기대값 |
| --- | --- | --- |
| `positive` | 정상 질문 | `decision=confident`, `intent_id=expected_intent` |
| `confusing` | 단어는 헷갈리지만 정답 Intent가 명확한 질문 | `decision=confident`, `intent_id=expected_intent` |
| `risk` | 위험 질문 | `decision=risk` |
| `off_topic` | 해당 서비스의 범위 밖 질문 | `decision=off_topic`. 단, 범용 선판정이 아니라 service_id별 정책/테스트 기준으로 평가 |
| `fallback` | 등록된 Intent에 없는 질문 | `decision=fallback` |

### 8.4 운영 반영 Gate

| 기준 | 운영 반영 판단 |
| --- | --- |
| risk case | 1건이라도 실패하면 차단 |
| 전체 PASS율 | 최소 70% 이상 통과해야 운영 반영 가능 |
| off_topic case | 범용 hard gate가 아니라 service_id별 품질 기준으로 평가 |
| positive case | 실패 건 수정 필요 |
| confusing case | 실패 건 수정 필요 |
| fallback case | 실패 건 수정 필요 |
| REVIEW 비율 | MVP에서는 hard gate가 아니라 15% 초과 시 개선 권고 |
| 테스트 미실행 | 운영 반영 차단 |
| 기존 PASS 회귀 | 운영 반영 전 확인 필수 |

MVP의 운영 반영 최소 기준은 전체 PASS율 70% 이상이다. threshold 변경에 따른 품질 변화를 확인하기 위해 test_run 결과에는 `threshold_preset`, `threshold_value`, `pass_rate`, `review_rate`, `risk_pass_rate`를 남긴다.

### 8.5 테스트 결과 표시 원칙

테스트 결과 응답은 모델 지표보다 실패 원인과 다음 조치를 먼저 보여준다.

```text
테스트 결과: 운영 반영 불가

위험 질문: 3/3 통과
범위 밖 질문: 2/2 통과, 서비스별 참고 기준
정상 질문: 8/10 통과
헷갈리는 질문: 7/8 통과
없는 업무 질문: 2/2 통과
검토 필요: 2건
threshold: 기준에 맞으면 분류, 80%

수정 필요:
- "보험금 청구 화면에서 500 에러가 나요"가 insurance_claim으로 분류됨
  -> it_error positive example 또는 insurance_claim negative example 추가 권장
```

---

## 9. 보안 / 권한

### 9.1 호출 시스템 인증

MVP는 Dify HTTP Request node와의 연계를 고려해 Bearer API Key 기반 인증을 사용한다.

단, API Key만으로 금융권 폐쇄망 서비스를 보호하지 않는다. 다음 통제를 함께 적용한다.

```text
API Key
+ app_id/service_id scope
+ 내부망 또는 API Gateway 접근 제한
+ IP allowlist
+ TLS
+ rate limit
+ 감사 로그
+ 주기적 회전
+ 즉시 폐기
```

가능하면 API Gateway 또는 service mesh 계층에서 mTLS를 적용한다. Dify HTTP Request node 자체에서 client certificate 운용이 어렵다면 Dify가 위치한 내부망 구간과 API Gateway에서 인증서를 처리한다.

### 9.2 API Key 정책

| 항목 | 정책 |
| --- | --- |
| 발급 단위 | `environment + app_id + service_id` |
| 환경 분리 | dev, staging, prod key 분리 |
| 권한 범위 | 허용 service_id, route_key, intent scope 명시 |
| 생성 | 256-bit 이상 난수 secret |
| 저장 | 원문 secret 저장 금지. hash 또는 HSM/secret manager 저장 |
| 표시 | 최초 발급 시 1회만 표시 |
| 로그 | key 원문 금지. key fingerprint 또는 마지막 4자리만 기록 |
| 만료 | prod 기본 90일, 예외 승인 시 최대 180일 |
| 회전 | 신규 key와 기존 key를 최대 7일 병행 허용 |
| 폐기 | 유출, 담당자 변경, 서비스 종료 시 즉시 revoke |
| rate limit | app_id/service_id 단위 제한 |

### 9.3 관리 사용자 권한

MVP의 관리 기능은 관리 API로 제공하며, 사용자 인증과 리소스 권한을 분리한다.

| 영역 | MVP 기준 |
| --- | --- |
| 사용자 인증 | 사내 SSO/OIDC 연계 후보. MVP 상세 구현은 환경에 맞춰 결정 |
| 리소스 권한 | service_id 단위 접근 제어 |
| 변경 권한 | draft 수정, 테스트 실행, 운영 반영 권한 분리 |
| 로그 권한 | masked log 조회와 raw query 조회 권한 분리 |
| 운영 반영 권한 | prod release 생성 권한은 제한 |

개발자는 자신이 담당하지 않는 service_id의 Intent, 테스트 결과, 운영 로그, API Key 정보를 볼 수 없어야 한다.

---

## 10. 감사 로그 / 버전 관리

### 10.1 로그 저장 및 PII 마스킹

요청 원문은 저장한다. 다만 운영 화면, 테스트 결과, 로그 조회, 외부 반출용 export에서는 다음 정보를 마스킹한다.

| 대상 | 예시 | 마스킹 예시 |
| --- | --- | --- |
| 주민등록번호 | `900101-1234567` | `900101-1******` |
| 사업자번호/사업자등록번호 | `123-45-67890` | `123-45-*****` |
| 휴대폰번호 | `010-1234-5678` | `010-****-5678` |

MVP 저장 구조는 다음과 같다.

| 필드 | 설명 |
| --- | --- |
| `query_raw_encrypted` | 원문 질의. DB 암호화 또는 application-level encryption 적용 |
| `query_masked` | 운영 화면과 검색에 사용하는 마스킹 질의 |

`query_raw_encrypted` 조회는 시스템 오류 분석 또는 감사 대응 목적으로만 허용한다. 인가된 사용자는 조회 사유를 입력해야 하며, 원문 조회 자체를 감사 로그로 남긴다.

### 10.2 원문 암호화 방식

원문 질의는 application-level envelope encryption을 기본으로 한다. DB 투명 암호화만으로는 애플리케이션 권한 오남용을 충분히 통제하기 어렵기 때문에, 애플리케이션에서 원문을 암호화한 뒤 저장한다.

MVP 암호화 규칙은 다음과 같다.

| 항목 | 규칙 |
| --- | --- |
| 암호화 방식 | AES-256-GCM |
| 키 구조 | record별 DEK(Data Encryption Key) 생성, KEK(Key Encryption Key)로 DEK 암호화 |
| KEK 보관 | 내부 KMS, HSM, 또는 금융권 표준 secret manager에 보관 |
| DB 저장 | `ciphertext`, `encrypted_dek`, `key_id`, `iv`, `auth_tag`, `algorithm` 저장 |
| 검색/조회 | 기본 검색과 화면 노출은 `query_masked`만 사용 |
| 로그 | raw query와 API Key secret은 application log에 남기지 않음 |
| 권한 | raw decrypt API는 별도 권한과 조회 사유를 요구 |
| 회전 | KEK rotation 시 기존 encrypted_dek를 재암호화 |
| 환경 분리 | dev, staging, prod key 분리 |
| 백업 | 백업 데이터도 암호화 상태를 유지 |

원문 복호화는 감사 목적 또는 장애 분석 목적에 한정한다. 복호화 API는 `trace_id`, `service_id`, `view_reason`, `requester_id`를 필수로 받고, 승인되지 않은 사용자는 masked query만 조회할 수 있다.

### 10.3 원문 조회 감사 로그

원문 조회가 발생하면 다음 정보를 남긴다.

```text
trace_id
viewed_by
view_reason
view_time
source_ip
service_id
```

### 10.4 Runtime Log 필수 필드

라우팅 API 응답과 내부 로그는 다음 필드를 남긴다.

```text
trace_id
request_id
app_id
service_id
release_version
policy_version
intent_catalog_version
model_version
vector_index_version
decision
intent_id
confidence
margin
threshold_preset
threshold_value
route_key
error_code
error_category
error_layer
http_status
retryable
latency_ms
query_masked
created_at
```

`error_code`, `error_category`, `error_layer`, `http_status`, `retryable`은 정상 routing decision에서는 null일 수 있다. 내부 오류나 인증/요청 오류가 발생한 경우에는 반드시 기록한다.

### 10.5 운영 버전 모델

운영 버전 모델은 "지금 운영 중인 라우팅 결과를 나중에 정확히 재현할 수 있게 만드는 체계"다.

`release_version`은 다음 버전을 하나로 묶는 운영 단위다.

| 버전 | 의미 |
| --- | --- |
| `policy_version` | decision 기준, threshold, margin, risk/off_topic/unauthorized 정책 |
| `intent_catalog_version` | Intent 정의, route_key, example, keyword |
| `model_version` | embedding 모델명, weight checksum, tokenizer, inference parameter |
| `vector_index_version` | 특정 catalog와 model로 생성한 pgvector embedding/index snapshot |
| `test_dataset_version` | 운영 반영 전 검증에 사용한 CSV 테스트셋 snapshot |
| `release_version` | 운영에 올라가는 불변 묶음 |

MVP에서 실제로 강제해야 하는 최소 버전은 다음 네 가지다.

```text
release_version
policy_version
intent_catalog_version
test_run_id
```

`model_version`과 `vector_index_version`도 로그 필드에는 포함한다. 단, UI에서 상세 관리하는 기능은 Sprint 0 이후로 미룰 수 있다.

### 10.6 운영 반영 흐름

```text
1. Draft 수정
   - Intent example, keyword, threshold, risk policy 수정

2. Snapshot 생성
   - policy_version 생성
   - intent_catalog_version 생성
   - model_version 확인
   - vector_index_version 생성

3. CSV 테스트 실행
   - test_dataset_version 고정
   - test_run_id 생성
   - PASS/FAIL/REVIEW 산출

4. Gate 판단
   - risk case 100% PASS
   - 전체 PASS율 70% 이상
   - off_topic case는 service_id별 품질 기준으로 확인
   - positive/confusing/fallback 실패 건 확인 및 수정
   - REVIEW 비율 15% 초과 시 개선 권고

5. Release 생성
   - release_version 생성
   - 운영 active pointer 변경

6. Runtime 호출
   - 모든 응답 로그에 release_version 기록

7. Rollback
   - 이전 release_version으로 active pointer 복구
```

---

## 11. MVP 범위

MVP는 독립 Intent Routing Service로 구현한다. 다만 처음부터 거대한 플랫폼을 만들지 않고 다음 세로 흐름만 검증한다.

```text
서비스 등록
-> API Key 발급
-> Intent 3~5개 등록
-> positive/negative example 등록
-> route_key 매핑
-> threshold 프리셋 선택
-> Dify HTTP Request node에서 API 호출
-> CSV 테스트 실행
-> PASS/FAIL/REVIEW 결과 확인
-> 실패 케이스를 example로 추가
-> 재테스트
-> release_version 생성
-> 기본 로그 확인
```

MVP 포함 범위는 다음과 같다.

| 영역 | 포함 기능 |
| --- | --- |
| 아키텍처 | 독립 Intent Routing API |
| 관리 방식 | API-Only 관리 기능 |
| 최초 연계 | Dify Platform HTTP Request node |
| 인증 | app_id, service_id, API Key 기반 호출 인증 |
| 권한 | service_id 단위 기본 접근 제어 |
| Catalog | Intent 3~5개 등록, route_key 매핑 |
| Example | positive/negative example 등록 |
| Keyword | include/exclude keyword 보정 |
| Embedding | BGE-M3, CPU-only, dense embedding, 256 token 기본 |
| Vector Store | PostgreSQL + pgvector, Exact Search |
| Threshold | strict 100%, balanced 80%, exploratory 60% |
| Decision | confidence/margin 기반 confident/clarify/fallback/off_topic/risk/unauthorized |
| Risk | 7개 범용 risk_type 우선 판정 |
| Off-topic | 범용 선판정 제외, service_id별 정책/테스트로 판단 |
| 테스트 | 개발자용 CSV 업로드, threshold별 PASS/FAIL/REVIEW, 70% gate 계산 |
| 오류 응답 | 내부 오류 표준 error envelope, trace_id 기반 로그 연결 |
| 로그 | trace_id, masked query, release_version 기반 기본 로그 |
| 버전 | release_version, policy_version, intent_catalog_version, test_run_id |
| PII | 주민등록번호, 사업자번호/사업자등록번호, 휴대폰번호 마스킹 |
| 원문 암호화 | AES-256-GCM 기반 application-level envelope encryption |

---

## 12. MVP 제외 범위

| 제외 항목 | 비고 |
| --- | --- |
| 모델 선택 UI | 시스템 관리자 설정 또는 환경 변수 수준으로 제한 |
| 자동 threshold 최적화 | 운영 데이터 축적 후 검토 |
| 실시간 A/B 테스트 | v1 이후 검토 |
| 복잡한 승인 워크플로우 | MVP는 운영 반영 권한 분리와 로그 중심 |
| 학습형 classifier | labeled data 축적 후 v1.x/v2 후보 |
| LLM judge 기본 경로 | 관리자 테스트 또는 REVIEW 분석 보조 후보 |
| 관리 콘솔 UI | MVP는 API-Only로 제공 |
| 고급 대시보드 | v1 이후 검토 |
| 다중 외부 시스템 연계 | 최초는 Dify만 대상으로 검증 |
| HNSW index | Exact Search p95 latency가 한계에 도달하면 전환 검토 |
| sparse/multi-vector retrieval | BGE-M3 dense retrieval 안정화 후 검토 |
| HMAC 요청 서명 | Dify Code node 또는 Gateway plugin 활용 가능 시 v1.1 후보 |
| MLflow/DVC 도입 | 버전 개념은 PRD에 반영하되 도구 도입은 MVP 제외 |

---

## 13. 성공 기준

MVP 성공 기준은 기능 완성보다 **검증 가능한 운영 흐름의 성립**이다.

| 기준 | 목표 |
| --- | --- |
| 서비스 온보딩 | 신규 service_id 등록, API Key 발급, Dify 호출 설정이 가능하다. |
| Intent 설정 | 개발자가 Intent 3~5개와 positive/negative example을 등록할 수 있다. |
| Runtime 응답 | `/v1/intent-route`가 `decision`, `intent_id`, `confidence`, `route_key`, `trace_id`, `release_version`을 반환한다. |
| 오류 응답 | 내부 오류 발생 시 `decision`이 아닌 표준 error envelope를 반환하고 `trace_id`로 추적할 수 있다. |
| CSV 테스트 | 개발자용 단순 CSV를 업로드하고 PASS/FAIL/REVIEW를 확인할 수 있다. |
| Gate | 테스트 미실행, risk 실패, 전체 PASS율 70% 미만이면 운영 반영을 차단한다. |
| 품질 목표 | 초기 테스트셋 기준 전체 PASS율 70% 이상을 운영 반영 최소 기준으로 둔다. |
| Critical case | risk case는 운영 반영 전 100% PASS해야 한다. |
| Off-topic | 범용 critical gate가 아니라 service_id별 품질 기준으로 평가한다. |
| REVIEW 비율 | MVP에서는 hard gate가 아니며 15% 초과 시 개선 권고한다. |
| Threshold 테스트 | 같은 CSV 테스트셋을 100%, 80%, 60% threshold로 실행하고 결과를 비교할 수 있다. |
| Latency | Intent Routing Service 내부 처리 기준 p95 5초 이하를 만족한다. |
| Client timeout | Dify workflow client timeout은 6~8초 권장, timeout/5xx 시 Dify fallback 처리한다. |
| 보안 | API Key scope, service_id 권한, masked log, key rotation 정책이 정의되어 있다. |
| 감사 | release_version, test_run_id, 변경자, 원문 조회 로그를 추적할 수 있다. |
| 재현성 | 운영 중 발생한 trace_id로 당시 release_version과 catalog/policy를 확인할 수 있다. |

Latency 측정 기준은 Dify 전체 workflow 왕복 시간이 아니라 **Intent Routing Service 내부 처리 시간**이다. HTTP 또는 HTTPS 요청이 Intent Routing Service에 도착한 시점부터 response body를 반환하는 시점까지를 측정한다.

권장 내부 목표는 다음과 같다.

| 구분 | 목표 |
| --- | --- |
| p50 latency | 1초 이하 |
| p95 latency | 5초 이하 |
| timeout | client 설정 기준 6~8초 |
| fallback | timeout 또는 5xx 발생 시 Dify workflow에서 고정 fallback 응답 또는 상담원 연결 |

---

## 14. 미결정 사항

### 14.1 회신 3으로 결정된 사항

2026-06-25 회신 3 기준으로 다음 항목은 PRD v0.2 결정사항으로 닫는다.

| 항목 | 결정 |
| --- | --- |
| 관리 콘솔 범위 | MVP는 API-Only. 관리 콘솔 UI는 v1 이후 검토 |
| threshold 기본값 | strict 100%, balanced 80%, exploratory 60% |
| threshold 한글 멘트 | 확실한 경우만 분류, 기준에 맞으면 분류, 넓게 후보 탐색 |
| clarify 응답 형식 | 후보 최대 3개, 사용자 확인 메시지, reason, candidate별 intent_id/display_name/route_key/confidence 반환 |
| off_topic 초기 판정 | 범용 선판정에서 제외. service_id별 업무 범위와 테스트셋 기준으로 판단 |
| risk policy 세트 | 7개 risk_type 적용: abuse, dangerous_command, sensitive_data, credential_secret, unauthorized_access, prompt_injection, fraud_or_illegal |
| route_key 표준 | service_id 내부 고유한 `<domain>.<intent>.<action>` 형식 |
| 테스트 gate | 전체 PASS율 70% 이상. threshold 프리셋별 테스트 실행/비교 가능 |
| 원문 암호화 방식 | AES-256-GCM 기반 application-level envelope encryption, KMS/HSM 또는 secret manager 기반 KEK 관리 |
| 내부 오류 응답 | routing decision과 분리된 표준 error envelope 사용. `trace_id`, `error.code`, `retryable`, `fallback_policy` 포함 |

### 14.2 남은 미결정 사항

다음 항목은 PRD v0.2 이후 Sprint 0 또는 상세 설계에서 결정한다.

| 항목 | 현재 상태 | 결정 필요 사항 |
| --- | --- | --- |
| SSO/OIDC 연계 방식 | 필요성은 확정 | 사내 IAM, Keycloak, 별도 연계 방식 |
| mTLS 적용 위치 | 권장 | Gateway, service mesh, Dify 구간 적용 가능성 |
| HNSW 전환 기준 | MVP 제외 | 데이터 규모, p95 latency, recall 기준 |
| LLM 후보 판정 | MVP 기본 제외 | 관리자 REVIEW 보조 기능의 도입 시점 |
| 운영 승인 절차 | 복잡한 workflow 제외 | prod release 생성 시 1인/2인 승인 필요 여부 |
| 보관 기간 | 로그 저장 필요 | raw/masked log, test result, release history retention |
