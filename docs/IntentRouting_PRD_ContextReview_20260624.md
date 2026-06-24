

# 현재까지의 논의 정리

## 1. 출발점

현재 PRD의 주제는 **금융권 폐쇄망 공통 Intent Routing Service**입니다.

이 서비스는 여러 AI Agent Platform, 챗봇, 내부 업무 시스템이 각자 의도분류를 따로 구현하지 않고, 공통 API를 통해 사용자 질의의 의도, 처리 방향, 신뢰도, 후속 라우팅 정보를 받을 수 있게 하는 것을 목표로 합니다. PRD에서도 이 서비스가 특정 챗봇의 부가기능이 아니라, 여러 내부 시스템이 공통으로 사용할 수 있는 **의도분류 및 라우팅 정책 서비스**라고 정의하고 있습니다. 

제가 보는 핵심은 이겁니다.

> 이 서비스는 “Intent 분류 모델 하나”가 아니라,
> **서비스별 정책 관리 + 라우팅 결정 + 테스트 검증 + 보안/권한 + 감사 추적을 제공하는 운영 플랫폼**입니다.

---

## 2. 기존 PRD에 대한 1차 PO 판단

기존 PRD는 방향성은 좋았습니다.

좋았던 점은 다음입니다.

| 항목      | 평가                                                     |
| ------- | ------------------------------------------------------ |
| 문제 정의   | 각 서비스가 의도분류를 따로 만들 때 생기는 중복, 품질 차이, 오분류 로그 분산 문제를 잘 잡음 |
| 제품 방향   | 공통 Intent Routing Service라는 방향이 명확함                    |
| 개발자 사용성 | ML/임베딩/threshold를 몰라도 템플릿과 프리셋으로 설정하게 하려는 방향이 좋음       |
| 테스트 구조  | CSV 테스트셋, PASS/FAIL/REVIEW, 실패 케이스 개선 루프가 들어간 점이 좋음    |
| 보안/권한   | 등록된 서비스만 호출, API Key, 역할 기반 권한 구분이 포함되어 있음             |
| 운영 관점   | 운영 반영 전 테스트, 변경 이력, 감사 로그 요구가 들어 있음                    |

하지만 냉정하게 보면 **바로 전체 개발에 들어가기에는 부족하다**고 판단했습니다.

이유는 다음입니다.

1. MVP 범위가 너무 큽니다.
2. 의도분류 방식이 아직 결정되지 않았습니다.
3. `confident`, `clarify`, `fallback`, `off_topic`, `risk`의 판정 기준이 부족합니다.
4. CSV 테스트는 있지만 합격 기준이 부족합니다.
5. API 계약이 실제 연계 개발 수준으로 닫혀 있지 않습니다.
6. 보안 요구사항은 방향은 있으나 금융권 수준으로 더 구체화해야 합니다.
7. 운영 반영, 버전 관리, 롤백 흐름이 아직 약합니다.

따라서 제 판단은 다음이었습니다.

> **전면 개발 착수는 아직 이르다.**
> 다만 **Sprint 0 / 아키텍처 검토 / 얇은 MVP 세로 흐름 개발**은 가능하다.

---

## 3. 자료 조사를 통해 얻은 방향

사용자가 “마음대로 만들지 말고, 오픈소스와 논문을 활용해서 근거를 잡자”고 했기 때문에, 이후에는 PRD 재작성보다 먼저 자료 조사 방향을 잡았습니다.

조사한 축은 다음과 같습니다.

| 조사 축                  | 참고한 방향                                        |
| --------------------- | --------------------------------------------- |
| Semantic Routing      | Semantic Router, vLLM Semantic Router         |
| Intent Classification | Rasa, intent fallback 구조                      |
| Out-of-Scope 탐지       | CLINC150/OOS 논문 방향                            |
| Embedding 기반 유사도      | SBERT, E5, BGE-M3, 한국어 임베딩 모델                 |
| Few-shot 확장 가능성       | SetFit                                        |
| Router/Agent 구조       | LangChain Router, LlamaIndex Router           |
| Guardrails            | NeMo Guardrails, Guardrails AI, LlamaFirewall |
| 테스트/평가                | promptfoo, DeepEval, OpenAI Evals, Ragas      |
| 보안/권한                 | OWASP API Security, OPA, Keycloak             |
| 관측성/감사                | OpenTelemetry, Jaeger                         |
| 모델/데이터 버전             | MLflow, DVC                                   |

자료 조사 결과 가장 중요한 결론은 다음입니다.

> 우리 서비스는 단일 LLM 프롬프트 분류 방식으로 가면 안 되고,
> **규칙 + 키워드 + 의미 기반 검색 + 정책 판단 + 필요 시 LLM 후보 판정**을 조합하는 하이브리드 구조가 맞습니다.

왜냐하면 금융권에서는 “정확히 맞췄는가”뿐 아니라, **왜 그렇게 분류했는지, 누가 설정했는지, 테스트를 통과했는지, 운영 반영 전 검증했는지**가 중요하기 때문입니다.

---

## 4. 현재까지 정리된 핵심 제품 관점

## 4.1 이 서비스의 본질

이 서비스는 답변 생성기가 아닙니다.

즉, 사용자의 질문에 직접 답변하는 서비스가 아니라, 아래를 판단하는 서비스입니다.

```text
이 질문은 어떤 의도인가?
이 서비스에서 허용된 의도인가?
확정 가능한가?
애매한가?
서비스 범위 밖인가?
위험 질의인가?
어느 후속 흐름으로 보내야 하는가?
```

따라서 반환값도 단순히 `intent_id` 하나가 아니라 다음 구조가 필요합니다.

```json
{
  "trace_id": "irt-20260618-000001",
  "decision": "confident",
  "domain": "IT",
  "intent_id": "it_api_timeout",
  "confidence": 0.87,
  "route_key": "it.manual.lookup",
  "fallback_policy": null
}
```

PRD에서도 응답에 `decision`, `intent_id`, `confidence`, `route_key`, `fallback_policy`가 포함되어야 한다고 정의되어 있습니다. 

---

## 4.2 개발자 사용성은 매우 중요한 요구사항

사용자가 특히 중요하게 본 지점은 이것입니다.

> “정확도를 위해 설정이 너무 어렵다면 개발자가 사용하기 어렵다.”

그래서 현재 방향은 다음과 같습니다.

개발자에게 처음부터 이런 용어를 노출하면 안 됩니다.

* threshold
* margin
* embedding
* rerank
* semantic score
* LLM judge
* vector search

대신 기본 화면에서는 이렇게 보여줘야 합니다.

```text
이 Intent에 해당하는 질문 예시
이 Intent가 아닌 헷갈리는 질문 예시
이 Intent로 분류되면 보낼 업무 흐름
애매하면 어떻게 처리할지
테스트 데이터 업로드
PASS/FAIL/REVIEW 결과 확인
```

즉, 내부적으로는 고급 로직이 있더라도, 개발자가 느끼는 제품 경험은 **템플릿 + 프리셋 + 예시 기반 설정**이어야 합니다.

---

## 4.3 Positive / Negative Example이 핵심 설정 방식

우리 서비스에서 개발자는 Intent를 직접 “학습”시키는 것이 아니라, 다음 두 가지 예시를 관리합니다.

| 구분               | 의미                           |
| ---------------- | ---------------------------- |
| positive example | 이 Intent에 해당하는 질문 예시         |
| negative example | 이 Intent로 가면 안 되는 헷갈리는 질문 예시 |

예를 들어:

```text
Intent: 보험금청구

positive example:
- 보험금 청구 방법 알려줘
- 실손보험 청구하려면 뭐가 필요해?

negative example:
- 보험금 청구 메뉴 개발 중인데 API Timeout 원인이 뭐야?
- 보험금 청구 화면에서 500 에러가 나
```

여기서 중요한 점은, 두 번째 negative example들은 “보험금 청구”라는 단어가 들어가지만 실제 의도는 IT문의입니다.

이런 케이스 때문에 단순 키워드 기반 분류는 위험합니다.

---

## 4.4 Decision 값은 제품적으로 더 명확히 정의해야 함

현재 PRD의 decision 값은 다음입니다.

| decision     | 의미                  |
| ------------ | ------------------- |
| confident    | Intent 확정 가능        |
| clarify      | 사용자에게 명확화 질문 필요     |
| off_topic    | 서비스 범위 밖 질문         |
| risk         | 위험 또는 차단 대상 질문      |
| fallback     | 확정 불가               |
| unauthorized | 해당 서비스에서 허용되지 않은 요청 |

이 방향은 좋습니다.

다만 앞으로 PRD에서는 각 decision의 판정 기준을 더 명확히 해야 합니다.

예를 들면:

| 상황                             | decision     |
| ------------------------------ | ------------ |
| 1위 Intent 점수가 충분히 높고 2위와 차이도 큼 | confident    |
| 1위와 2위 Intent가 너무 비슷함          | clarify      |
| 전체적으로 유사한 Intent가 없음           | fallback     |
| 금융/업무와 무관한 질문                  | off_topic    |
| 보안/윤리/위험 정책에 걸림                | risk         |
| 서비스가 해당 Intent를 사용할 권한 없음      | unauthorized |

이렇게 정리해야 개발팀이 임의로 해석하지 않습니다.

---

## 4.5 CSV 테스트는 단순 기능이 아니라 운영 반영 게이트

현재 PRD에는 CSV 테스트 데이터셋 업로드와 PASS/FAIL/REVIEW 결과 확인이 들어 있습니다. 

이 기능은 매우 중요합니다.

하지만 지금보다 더 강하게 정의해야 합니다.

단순히 “테스트 결과를 보여준다”가 아니라:

```text
설정 변경
→ CSV 테스트 실행
→ PASS/FAIL/REVIEW 확인
→ 기준 미달 시 운영 반영 차단
→ 실패 케이스 개선
→ 재테스트
→ 운영 반영
```

이런 구조가 되어야 합니다.

특히 CSV 컬럼은 현재보다 확장하는 게 좋습니다.

현재 PRD의 기본 컬럼:

```text
case_id, query, expected_domain, expected_intent, case_type
```

보완 제안:

```text
case_id,
query,
expected_decision,
expected_domain,
expected_intent,
expected_route_key,
case_type,
priority,
must_pass,
memo
```

왜냐하면 Intent만 맞아도 decision이 틀리면 운영상 실패일 수 있기 때문입니다.

예를 들어:

| query              | expected_intent | expected_decision |
| ------------------ | --------------- | ----------------- |
| 예금 오늘 날씨 어때        | off_topic       | off_topic         |
| 보험금 청구 방법 알려줘      | insurance_claim | confident         |
| 보험금 청구랑 사고접수 중 뭐야? | null            | clarify           |
| 시스템 해킹 방법 알려줘      | risk_policy     | risk              |

---

# 5. 현재까지 합의된 아키텍처 방향

아직 최종 확정은 아니지만, 현재까지의 의견은 다음에 가깝습니다.

## 5.1 독립 서비스가 유리함

이 서비스는 여러 챗봇, Agent, 내부 업무 시스템이 공통으로 사용해야 합니다.

따라서 특정 챗봇 백엔드 안에 모듈로 넣기보다는, 독립된 Intent Routing Service로 두는 것이 재사용성, 보안, 운영 추적 측면에서 더 유리합니다.

단, MVP에서는 너무 큰 플랫폼을 만들지 않고, 최소 세로 흐름부터 검증해야 합니다.

---

## 5.2 하이브리드 라우팅 엔진이 적합함

추천 흐름은 다음입니다.

```text
1. 요청 수신
2. app_id + API Key 검증
3. 서비스 권한 확인
4. risk/off_topic 우선 검사
5. 서비스별 허용 Intent 필터링
6. include/exclude keyword로 후보 보정
7. positive/negative example 기반 의미 검색
8. confidence + margin으로 decision 산출
9. 필요 시 LLM 후보 판정
10. route_key 반환
11. trace_id 기준 로그 저장
```

이 구조가 좋은 이유는 다음입니다.

* 키워드만 쓰면 혼합 질의에 약함
* LLM만 쓰면 느리고 통제하기 어려움
* embedding만 쓰면 위험/권한/정책 판단이 약함
* 금융권에서는 감사 가능성과 설명 가능성이 중요함
* 개발자는 쉬운 설정을 원하지만 내부 엔진은 통제 가능해야 함

---

## 5.3 Risk / Off-topic은 일반 Intent와 분리하는 게 좋음

`risk`와 `off_topic`을 일반 Intent와 똑같이 취급하면 위험합니다.

예를 들어 위험 질의는 “어느 route로 보낼까?”가 아니라 “차단할지, 고정 안내를 줄지, 상담원에게 넘길지”의 문제입니다.

그래서 방향은 다음이 좋습니다.

```text
일반 Intent Routing
- 업무 흐름 선택
- route_key 반환

Risk / Off-topic Policy
- 차단
- 고정 응답
- 상담원 연결
- 로그 강화
- 관리자 검토
```

즉, risk/off_topic은 Intent Catalog 안에만 넣지 말고, 별도 정책 레이어로 보는 게 맞습니다.

---

# 6. 현재 MVP는 다시 줄여야 함

기존 PRD의 MVP 범위는 너무 큽니다.

기존 MVP에는 다음이 모두 포함되어 있습니다.

* 서비스 등록
* API Key
* 역할 기반 권한
* Intent Catalog
* 템플릿/프리셋
* positive/negative example
* 모델/분류 방식 선택
* 의도분류 API
* CSV 테스트
* 실패 케이스 개선
* 운영 반영 전 테스트
* 감사 로그
* Dify 또는 AI Agent Platform 연계

이건 MVP라기보다 v1.0에 가깝습니다.

현재까지의 의견은 MVP를 이렇게 줄이는 것입니다.

## 6.1 진짜 MVP 세로 흐름

```text
서비스 등록
→ API Key 발급
→ Intent 3~5개 등록
→ positive/negative example 등록
→ route_key 매핑
→ 의도분류 API 호출
→ CSV 테스트 실행
→ PASS/FAIL/REVIEW 결과 확인
→ 실패 케이스를 example로 추가
→ 재테스트
→ 기본 로그 확인
```

이 흐름이 성공하면 이 제품의 핵심 가설을 검증할 수 있습니다.

핵심 가설은 다음입니다.

> 개발자가 ML/NLP를 몰라도 Intent 규칙을 설정하고, 테스트로 검증하고, 실패 케이스를 개선할 수 있는가?

---

## 6.2 MVP에서 줄일 항목

| 항목               | MVP 판단       |
| ---------------- | ------------ |
| 복잡한 모델 선택 UI     | 제외 또는 관리자 전용 |
| 자동 threshold 최적화 | 제외           |
| 실시간 A/B 테스트      | 제외           |
| 복잡한 승인 워크플로우     | 제외           |
| 고급 관리자 대시보드      | 제외           |
| 모든 템플릿 제공        | 2~3개만        |
| 모든 외부 시스템 연계     | 1개만          |
| 모델 파인튜닝          | 제외 유지        |
| 자동 Intent 추천     | 제외 유지        |

---

# 7. PRD v0.2에 반드시 들어가야 할 보완 항목

## 7.1 사용자 흐름

현재 PRD는 요구사항은 많지만 실제 개발자가 어떤 순서로 사용하는지 더 명확해야 합니다.

권장 흐름:

```text
1. 시스템 관리자가 서비스 등록
2. API Key 발급
3. 개발자에게 서비스 권한 부여
4. 개발자가 템플릿 선택
5. 개발자가 프리셋 선택
6. 사용할 Intent 선택
7. positive/negative example 입력
8. route_key 설정
9. CSV 테스트 업로드
10. PASS/FAIL/REVIEW 확인
11. 실패 케이스 개선
12. 재테스트
13. 운영 반영
14. 운영 로그 확인
```

---

## 7.2 판정 모델

다음 기준을 PRD에 넣어야 합니다.

```text
confidence: 선택된 Intent의 신뢰도
margin: 1위 Intent와 2위 Intent의 차이
threshold: Intent 확정 최소 기준
decision: confident / clarify / fallback / off_topic / risk / unauthorized
```

특히 `clarify`와 `fallback`은 분리해야 합니다.

* `clarify`: 후보가 여러 개라 사용자에게 확인이 필요함
* `fallback`: 적절한 후보 자체가 없음

---

## 7.3 테스트 합격 기준

현재 성공 기준은 “기능이 가능하다” 수준입니다.

앞으로는 이런 기준이 필요합니다.

| 항목             | 예시 기준             |
| -------------- | ----------------- |
| 전체 PASS율       | 85% 이상            |
| critical case  | 100% PASS         |
| risk case      | 오분류 0건            |
| off_topic case | 오분류 기준 이하         |
| REVIEW 비율      | 10% 이하            |
| p95 latency    | 내부 기준 이하          |
| 운영 반영          | 테스트 미실행 시 차단      |
| 회귀 테스트         | 기존 PASS 케이스 실패 없음 |

정확한 수치는 나중에 조정해도 되지만, PRD에는 “수치를 넣는 자리”가 있어야 합니다.

---

## 7.4 보안/권한

API Key만으로는 부족합니다.

필요한 보안 구조는 다음입니다.

| 구분        | 필요 기능                 |
| --------- | --------------------- |
| 호출 시스템 인증 | app_id + API Key      |
| 관리 사용자 인증 | SSO/OIDC              |
| 리소스 권한    | service_id 단위 접근 제어   |
| 변경 권한     | 운영 반영, 모델 변경 권한 분리    |
| 감사 로그     | 누가, 언제, 무엇을 바꿨는지 저장   |
| Key 관리    | 발급, 폐기, 회전, 만료, 환경 분리 |
| 민감정보      | 요청/응답 로그 마스킹 기준       |

특히 개발자는 자신이 담당하지 않는 서비스의 Intent, 테스트 결과, 로그를 볼 수 없어야 합니다. 이 요구는 현재 PRD에도 포함되어 있습니다. 

---

## 7.5 버전 관리

운영 반영 전 테스트를 하려면 설정 버전이 필요합니다.

최소한 다음 개념이 있어야 합니다.

```text
policy_version
intent_catalog_version
test_dataset_version
model_version
release_version
```

운영 반영 로그에는 다음이 남아야 합니다.

```text
before_version
after_version
test_run_id
pass_rate
changed_by
approved_by
release_time
rollback_available
```

이게 없으면 “어떤 설정으로 테스트했고, 어떤 설정이 운영에 반영됐는지” 추적할 수 없습니다.

---

# 8. 현재까지의 종합 의견

제 의견을 정리하면 이렇습니다.

## 8.1 현재 PRD는 방향성 문서로는 좋다

문제 정의, 역할 구분, 보안, 테스트, 개발자 사용성, 운영 이력까지 들어간 점은 좋습니다.

특히 “개발자가 ML/임베딩/threshold를 몰라도 쓸 수 있어야 한다”는 방향은 매우 중요합니다.

이 제품이 성공하려면 기술적으로 멋진 것보다, 개발자가 실제로 쉽게 설정하고 신뢰할 수 있어야 합니다.

---

## 8.2 하지만 개발 착수 문서로는 아직 부족하다

부족한 이유는 다음입니다.

* MVP가 너무 크다.
* 판정 기준이 부족하다.
* 테스트 합격 기준이 부족하다.
* API 계약이 부족하다.
* 운영 반영/버전 관리가 약하다.
* 보안 상세 정책이 부족하다.
* 아키텍처 선택지가 정리되지 않았다.

따라서 지금 상태로 전체 개발에 들어가면 개발팀이 중간에 계속 질문하게 되고, 기능은 많지만 핵심 검증이 약한 플랫폼이 될 가능성이 있습니다.

---

## 8.3 다음 PRD는 “기능 나열”이 아니라 “검증 가능한 운영 흐름” 중심이어야 한다

다음 PRD v0.2의 중심은 기능 목록이 아니라 이 흐름이어야 합니다.

```text
서비스 등록
→ Intent 설정
→ 테스트
→ 실패 개선
→ 운영 반영
→ API 호출
→ 로그 확인
→ 재개선
```

이 흐름이 명확해야 합니다.

---

# 9. 다음 단계 제안

다음 작업은 바로 PRD 전체 재작성보다, 아래 순서가 좋습니다.

## 1단계: 아키텍처 선택지 비교

```text
독립 서비스
vs Agent Platform 내부 기능
vs 챗봇 백엔드 모듈
```

기준:

* 재사용성
* 보안 관리
* 배포 독립성
* 운영 복잡도
* 장애 영향 범위
* 확장성

---

## 2단계: 의도분류 방식 비교

```text
규칙 기반
키워드 기반
embedding 기반
LLM 후보 판정
하이브리드 방식
```

기준:

* 정확도
* latency
* 폐쇄망 적합성
* 운영비용
* 설명 가능성
* 개발자 설정 난이도
* 신규 Intent 추가 난이도

---

## 3단계: MVP 범위 재정의

기존 MVP를 줄이고, 핵심 세로 흐름만 남겨야 합니다.

```text
서비스 등록
API Key
Intent 3~5개
positive/negative example
route_key
분류 API
CSV 테스트
PASS/FAIL/REVIEW
실패 케이스 개선
기본 로그
```

---

## 4단계: PRD v0.2 작성

v0.2는 다음 목차로 가는 게 좋습니다.

```text
1. 목적
2. 문제 정의
3. 비목표
4. 주요 사용자
5. 핵심 사용자 흐름
6. Routing Decision Model
7. Intent Catalog / Example Model
8. 테스트셋 / 평가 기준
9. 보안 / 권한
10. 감사 로그 / 버전 관리
11. MVP 범위
12. MVP 제외 범위
13. 성공 기준
14. 미결정 사항
```

