# Intent Routing Service 아키텍처 및 의도분류 방식 비교

작성일: 2026-06-24  
목적: PRD v0.2 작성 전에 아키텍처 방향과 의도분류 방식을 먼저 결정하기 위한 비교 문서

---

## 1. 문서 목적

현재 제품 방향은 금융권 폐쇄망에서 여러 AI Agent Platform, 챗봇, 내부 업무 시스템이 공통으로 호출하는 **Intent Routing Service**를 만드는 것입니다.

이 문서는 다음 두 가지 결정을 닫기 위해 작성합니다.

1. Intent Routing 기능을 어디에 둘 것인가
2. 사용자 질의를 어떤 방식으로 분류하고 라우팅할 것인가

이 문서는 최종 PRD가 아니라 PRD v0.2의 근거 문서입니다.

---

## 2. 전제 조건

### 2.1 제품 전제

- 이 서비스는 답변 생성기가 아니다.
- 이 서비스는 사용자 질의를 받아 `decision`, `intent_id`, `confidence`, `route_key`, `fallback_policy`를 반환하는 라우팅 정책 서비스다.
- 여러 서비스가 공통으로 사용해야 하므로 서비스별 설정, 권한, 테스트, 배포 이력, 감사 로그가 필요하다.
- 개발자는 ML, embedding, threshold를 몰라도 Intent를 설정하고 테스트할 수 있어야 한다.

### 2.2 금융권 폐쇄망 전제

- 외부 SaaS 의존을 기본 경로로 둘 수 없다.
- 모델과 라우팅 정책은 내부망에서 재현 가능해야 한다.
- 운영 반영 전 테스트와 감사 추적이 중요하다.
- 요청/응답 로그는 민감정보 마스킹 기준이 필요하다.
- 서비스별 접근 권한이 명확해야 한다.

---

## 3. 결론 요약

### 3.1 아키텍처 권고안

**MVP는 독립 Intent Routing Service로 만든다.**

단, 처음부터 거대한 플랫폼을 만들지 않고 다음만 포함한 얇은 세로 흐름으로 시작한다.

```text
서비스 등록
-> API Key 발급
-> Intent 3~5개 등록
-> positive/negative example 등록
-> route_key 매핑
-> 의도분류 API 호출
-> CSV 테스트 실행
-> PASS/FAIL/REVIEW 확인
-> 실패 케이스 개선
-> 기본 로그 확인
```

### 3.2 의도분류 방식 권고안

**MVP는 하이브리드 라우팅 엔진으로 간다.**

권장 순서는 다음과 같다.

```text
1. app_id + API Key 인증
2. service_id 권한 확인
3. risk 정책 우선 검사
4. off_topic 후보 검사
5. 서비스별 허용 Intent 필터링
6. include/exclude keyword로 후보 보정
7. positive/negative example 기반 의미 검색
8. confidence + margin으로 decision 산출
9. 필요 시 LLM 후보 판정
10. route_key 반환
11. trace_id 기준 로그 저장
```

MVP 기본 경로에서는 LLM 후보 판정을 필수로 두지 않는다. LLM 후보 판정은 `REVIEW` 케이스 분석, 관리자 테스트, 또는 특정 서비스의 선택 기능으로 남긴다.

---

## 4. 1단계: 아키텍처 선택지 비교

비교 대상은 다음 세 가지다.

| 선택지 | 설명 |
| --- | --- |
| A. 독립 Intent Routing Service | 별도 서비스로 배포하고 여러 시스템이 API로 호출 |
| B. Agent Platform 내부 기능 | Dify, LangChain 기반 Agent Platform 등 내부에 라우팅 기능 포함 |
| C. 챗봇 백엔드 모듈 | 개별 챗봇 또는 업무 시스템 백엔드 안에 모듈로 포함 |

---

## 4.1 선택지 A: 독립 Intent Routing Service

### 설명

Intent Routing을 별도 서비스로 분리하고, 각 Agent Platform, 챗봇, 업무 시스템은 공통 API를 호출한다.

```text
Client System
-> Intent Routing Service
-> decision / intent_id / route_key 반환
-> Client System이 후속 업무 흐름 실행
```

### 장점

- 여러 서비스가 공통 정책과 공통 API를 사용할 수 있다.
- 서비스별 Intent, route_key, 권한, API Key를 중앙에서 관리할 수 있다.
- 테스트 결과, 운영 반영 이력, 감사 로그를 한곳에 남길 수 있다.
- 신규 챗봇이나 Agent가 늘어나도 동일한 라우팅 정책을 재사용할 수 있다.
- risk/off_topic 정책을 서비스별 구현에 맡기지 않고 중앙에서 통제할 수 있다.
- 모델, threshold, 평가 기준을 중앙에서 개선할 수 있다.

### 단점

- 별도 서비스 운영 비용과 배포 파이프라인이 필요하다.
- 호출 경로에 네트워크 hop이 하나 추가된다.
- 서비스 장애 시 여러 연계 시스템에 영향을 줄 수 있다.
- 중앙 서비스 팀이 병목이 될 수 있다.

### 적합한 조건

- 여러 서비스가 공통 Intent Routing을 사용한다.
- 운영 반영 전 테스트와 감사 추적이 중요하다.
- 보안, 권한, 정책 통제를 중앙화해야 한다.
- Intent 정책의 버전 관리와 롤백이 필요하다.

---

## 4.2 선택지 B: Agent Platform 내부 기능

### 설명

Intent Routing을 Agent Platform 내부 기능으로 둔다. 예를 들어 Dify, LangChain, LlamaIndex 기반 플랫폼 안에서 라우터를 구성하는 방식이다.

```text
User
-> Agent Platform
-> Platform 내부 router
-> Agent / Tool / Workflow 선택
```

### 장점

- Agent 실행 흐름과 라우팅을 한곳에서 구성할 수 있다.
- 초기 데모와 특정 Agent 대상 구현은 빠를 수 있다.
- Agent Platform의 기존 tool, workflow, prompt 설정과 연결하기 쉽다.
- Agent별 실험이나 PoC에는 유연하다.

### 단점

- 특정 Agent Platform에 종속된다.
- Agent Platform을 쓰지 않는 내부 시스템은 재사용하기 어렵다.
- 서비스별 권한, 감사, 운영 반영 게이트를 플랫폼 밖에서 다시 설계해야 할 수 있다.
- Intent Routing이 Agent 실행 로직과 섞여 정책 서비스로 분리되기 어렵다.
- 플랫폼 변경 시 라우팅 정책도 함께 흔들릴 수 있다.

### 적합한 조건

- 대상이 특정 Agent Platform 하나로 고정되어 있다.
- 공통 서비스보다 Agent 내부 UX와 빠른 실험이 더 중요하다.
- 보안/감사/버전 관리 요구가 낮거나 별도 체계가 이미 있다.

---

## 4.3 선택지 C: 챗봇 백엔드 모듈

### 설명

각 챗봇 또는 업무 시스템 백엔드 안에 Intent Routing 모듈을 직접 포함한다.

```text
User
-> Chatbot Backend
-> Backend 내부 intent module
-> Backend 내부 workflow 실행
```

### 장점

- 단일 챗봇 기준으로 구현이 단순하다.
- 네트워크 hop이 줄어 latency를 낮추기 쉽다.
- 해당 업무 시스템의 DB, 세션, 권한과 바로 연결할 수 있다.
- 작은 서비스 하나에는 운영 부담이 낮다.

### 단점

- 서비스마다 Intent Routing을 중복 구현하게 된다.
- 품질 기준, threshold, fallback 기준이 서비스별로 달라질 가능성이 높다.
- 오분류 로그와 실패 케이스가 분산된다.
- 공통 risk/off_topic 정책을 강제하기 어렵다.
- 신규 서비스가 생길 때마다 같은 기능을 다시 만들어야 한다.
- 금융권 감사 관점에서 변경 이력 추적이 분산된다.

### 적합한 조건

- Intent Routing을 사용할 서비스가 하나뿐이다.
- 빠른 단일 서비스 출시가 최우선이다.
- 공통 정책, 중앙 감사, 다중 서비스 재사용 요구가 없다.

---

## 4.4 아키텍처 비교표

| 기준 | A. 독립 서비스 | B. Agent Platform 내부 기능 | C. 챗봇 백엔드 모듈 |
| --- | --- | --- | --- |
| 재사용성 | 높음 | 중간 | 낮음 |
| 보안 정책 중앙화 | 높음 | 중간 | 낮음 |
| 서비스별 권한 관리 | 높음 | 중간 | 낮음 |
| 운영 반영 전 테스트 게이트 | 높음 | 중간 | 낮음 |
| 감사 로그 일관성 | 높음 | 중간 | 낮음 |
| 배포 독립성 | 높음 | 낮음~중간 | 낮음 |
| 초기 구현 속도 | 중간 | 높음 | 높음 |
| 운영 복잡도 | 중간 | 중간 | 낮음에서 시작하지만 서비스 수 증가 시 높음 |
| 장애 영향 범위 | 넓을 수 있음 | Platform 영향 범위와 동일 | 개별 서비스로 제한 |
| latency | 네트워크 hop 추가 | Platform 내부 처리 | 가장 단순 |
| 폐쇄망 적합성 | 높음 | Platform 구성에 따라 다름 | 높지만 표준화 약함 |
| 장기 확장성 | 높음 | Platform 종속 | 낮음 |

---

## 4.5 아키텍처 권고

### 최종 권고

**독립 Intent Routing Service를 선택한다.**

이유는 이 제품의 본질이 특정 챗봇 기능이 아니라, 여러 내부 시스템이 공통으로 사용할 수 있는 **정책 기반 의도분류 및 라우팅 플랫폼**이기 때문이다.

금융권 환경에서는 단순히 intent를 맞히는 것보다 다음이 더 중요하다.

- 누가 설정을 바꿨는가
- 어떤 테스트를 통과했는가
- 어떤 버전이 운영 중인가
- 어떤 서비스가 어떤 Intent를 호출할 권한이 있는가
- risk/off_topic이 어디서 어떤 기준으로 처리되었는가
- 운영 중 오분류가 어떻게 개선되는가

이 요구는 독립 서비스 구조에서 가장 자연스럽게 충족된다.

### MVP에서의 절제 조건

독립 서비스를 선택하더라도 MVP에서 다음은 제외한다.

- 복잡한 승인 워크플로우
- 고급 관리자 대시보드
- 모델 선택 UI
- 자동 threshold 최적화
- 실시간 A/B 테스트
- 다중 Agent Platform 연계

MVP는 하나의 공통 API와 최소 관리 기능으로 제품 가설을 검증해야 한다.

---

## 5. 2단계: 의도분류 방식 비교

비교 대상은 다음 여섯 가지다.

| 선택지 | 설명 |
| --- | --- |
| 1. 규칙 기반 | 정해진 정책, 정규식, 우선순위 조건으로 판정 |
| 2. 키워드 기반 | include/exclude keyword로 후보 Intent를 보정 |
| 3. embedding 기반 의미 검색 | positive/negative example과 질의의 의미 유사도로 판정 |
| 4. 학습형 classifier | labeled dataset으로 intent classifier 학습 |
| 5. LLM 후보 판정 | LLM이 후보 Intent 중 적합한 것을 판단 |
| 6. 하이브리드 | 규칙, 키워드, 의미 검색, 정책, 선택적 LLM 판정을 조합 |

---

## 5.1 방식 1: 규칙 기반

### 설명

정규식, 고정 패턴, 정책 조건, 우선순위 규칙으로 판정한다.

예시:

```text
if query contains forbidden pattern:
  decision = risk

if app_id is not allowed for intent:
  decision = unauthorized
```

### 장점

- 설명 가능성이 높다.
- 빠르고 비용이 낮다.
- risk, unauthorized, 명시적 차단 정책에 강하다.
- 테스트와 감사가 쉽다.

### 단점

- 표현이 조금만 바뀌어도 놓칠 수 있다.
- 업무 의미나 문맥을 이해하지 못한다.
- Intent 수가 늘어나면 규칙 충돌이 많아진다.

### 권고

일반 Intent 분류의 단독 방식으로는 부적합하다.  
다만 risk, unauthorized, 서비스 정책, 명시적 차단 조건에는 반드시 사용해야 한다.

---

## 5.2 방식 2: 키워드 기반

### 설명

Intent별 include/exclude keyword를 등록하고 후보 점수를 보정한다.

예시:

```text
Intent: insurance_claim
include keyword: 보험금, 실손, 청구, 서류
exclude keyword: API, 500 에러, timeout, 개발, 화면 오류
```

### 장점

- 개발자가 이해하기 쉽다.
- 설정과 디버깅이 단순하다.
- 특정 업무 용어를 강하게 반영할 수 있다.
- negative keyword로 명확한 오분류를 줄일 수 있다.

### 단점

- 단순 키워드 일치만으로는 혼합 질의에 취약하다.
- 같은 단어가 다른 문맥에서 쓰이는 경우 오분류가 발생한다.
- 동의어와 우회 표현에 약하다.

### 권고

단독 방식으로는 부족하다.  
하지만 개발자 설정 UX에서는 중요한 보정 도구로 남겨야 한다.

---

## 5.3 방식 3: embedding 기반 의미 검색

### 설명

사용자 질의와 Intent별 positive/negative example을 embedding으로 변환하고 의미 유사도를 비교한다.

예시:

```text
query_embedding = embed(user_query)
positive_score = similarity(query, positive_examples)
negative_score = similarity(query, negative_examples)
intent_score = positive_score - negative_penalty
```

### 장점

- 키워드가 달라도 의미가 비슷하면 잡을 수 있다.
- positive/negative example 기반 설정과 잘 맞는다.
- 개발자가 ML을 몰라도 예시를 추가하면서 품질을 개선할 수 있다.
- 폐쇄망에서 오픈소스 embedding 모델로 운영 가능하다.
- 신규 Intent 추가 시 모델 재학습 없이 example 추가로 시작할 수 있다.

### 단점

- threshold와 margin 설계가 필요하다.
- embedding 모델 품질에 영향을 받는다.
- domain-specific 표현이 많으면 테스트셋 기반 보정이 필요하다.
- risk나 권한 같은 정책 판단을 embedding에 맡기면 안 된다.

### 권고

MVP의 일반 Intent 후보 산출 핵심 방식으로 사용한다.  
단, 반드시 규칙/정책 레이어와 결합해야 한다.

---

## 5.4 방식 4: 학습형 classifier

### 설명

Intent별 labeled dataset을 모아 분류 모델을 학습한다. 예를 들어 SetFit처럼 적은 데이터로 sentence transformer 기반 classifier를 만들 수 있다.

### 장점

- 충분한 데이터가 있으면 안정적인 분류 성능을 기대할 수 있다.
- 서비스별로 반복되는 질의 패턴이 많을 때 효과적이다.
- 모델 평가 체계를 갖추면 장기적으로 품질을 개선하기 좋다.

### 단점

- 초기 MVP에는 labeled data가 부족할 가능성이 높다.
- 모델 학습, 배포, 버전 관리, 롤백 체계가 필요하다.
- 개발자에게는 "예시 추가"보다 운영 부담이 크다.
- Intent가 자주 바뀌면 재학습 부담이 생긴다.

### 권고

MVP 기본 방식에서는 제외한다.  
운영 로그와 테스트셋이 쌓인 후 v1.x 또는 v2에서 검토한다.

---

## 5.5 방식 5: LLM 후보 판정

### 설명

규칙/embedding으로 후보 Intent를 좁힌 뒤 LLM이 최종 판단하거나 설명을 생성한다.

예시:

```text
Candidate intents:
- insurance_claim
- it_api_timeout

LLM judge:
질의는 보험금 청구 업무 자체가 아니라 청구 화면의 500 에러를 묻고 있으므로 it_api_timeout에 가깝다.
```

### 장점

- 복잡하고 애매한 질의에서 문맥 판단력이 좋다.
- 후보 간 차이를 설명하는 데 유리하다.
- REVIEW 케이스 분석에 도움이 된다.

### 단점

- latency와 비용이 높다.
- 폐쇄망에서는 사용할 수 있는 모델이 제한된다.
- 결과 재현성과 감사 가능성을 별도로 통제해야 한다.
- prompt, 모델 버전, 입력 마스킹 관리가 필요하다.
- 기본 경로에 넣으면 운영 안정성이 낮아질 수 있다.

### 권고

MVP의 필수 경로에서는 제외한다.  
단, 관리자 테스트나 REVIEW 케이스 보조 판정으로 선택 적용할 수 있게 설계 여지는 둔다.

---

## 5.6 방식 6: 하이브리드 라우팅

### 설명

규칙 기반 정책, 키워드 보정, embedding 기반 의미 검색, confidence/margin decision, 선택적 LLM 후보 판정을 조합한다.

```text
정책 판단
-> 후보 필터링
-> 키워드 보정
-> 의미 검색
-> confidence/margin 판정
-> 필요 시 REVIEW 또는 LLM 보조 판정
```

### 장점

- 각 방식의 약점을 보완할 수 있다.
- risk/unauthorized 같은 정책 판단을 명확히 분리할 수 있다.
- 일반 Intent는 positive/negative example 중심으로 개선할 수 있다.
- 금융권에서 중요한 설명 가능성과 감사 추적을 확보하기 쉽다.
- MVP에서는 얇게 시작하고, 이후 classifier나 LLM judge를 추가할 수 있다.

### 단점

- 단일 방식보다 구현 복잡도가 높다.
- scoring, threshold, margin 기준을 PRD에 명확히 써야 한다.
- 테스트셋 없이 만들면 기준이 흔들릴 수 있다.

### 권고

**MVP 기본 방식으로 선택한다.**

---

## 5.7 의도분류 방식 비교표

| 기준 | 규칙 기반 | 키워드 기반 | embedding 의미 검색 | 학습형 classifier | LLM 후보 판정 | 하이브리드 |
| --- | --- | --- | --- | --- | --- | --- |
| 정확도 잠재력 | 낮음~중간 | 낮음~중간 | 중간~높음 | 중간~높음 | 높음 | 높음 |
| latency | 매우 낮음 | 매우 낮음 | 낮음~중간 | 낮음~중간 | 높음 | 중간 |
| 설명 가능성 | 높음 | 높음 | 중간 | 중간 | 중간 | 높음 |
| 폐쇄망 적합성 | 높음 | 높음 | 높음 | 높음 | 모델에 따라 다름 | 높음 |
| 초기 데이터 요구 | 낮음 | 낮음 | 낮음~중간 | 높음 | 낮음 | 낮음~중간 |
| 개발자 설정 난이도 | 중간 | 낮음 | 낮음 | 높음 | 낮음 | 낮음~중간 |
| 운영 통제성 | 높음 | 높음 | 중간 | 중간 | 낮음~중간 | 높음 |
| 신규 Intent 추가 | 규칙 추가 필요 | 키워드 추가 | example 추가 | 데이터 수집/재학습 | prompt 후보 추가 | example/정책 추가 |
| risk/off_topic 처리 | risk에 강함 | 약함 | 중간 | 중간 | 중간 | 강함 |
| MVP 적합성 | 보조 | 보조 | 핵심 | 제외 | 선택 보조 | 핵심 |

---

## 6. 권장 Decision Model

PRD v0.2에는 다음 decision model을 명확히 넣어야 한다.

| decision | 판정 기준 |
| --- | --- |
| `confident` | 1위 Intent 점수가 threshold 이상이고 2위와 margin이 충분하며 negative penalty가 낮음 |
| `clarify` | 후보 Intent가 2개 이상이고 점수 차이가 작아 사용자 확인이 필요함 |
| `fallback` | 적절한 후보 Intent가 없음 |
| `off_topic` | 서비스 범위 밖 질의로 판단됨 |
| `risk` | 보안, 윤리, 악용, 정책 위반 조건에 걸림 |
| `unauthorized` | 호출 서비스가 해당 Intent 또는 route_key를 사용할 권한이 없음 |

### 6.1 우선순위

decision 우선순위는 다음처럼 둔다.

```text
1. risk
2. unauthorized
3. off_topic
4. confident
5. clarify
6. fallback
```

단, `unauthorized`는 후보 Intent가 산출된 뒤 service policy와 비교해 판정할 수 있다.  
`risk`는 일반 Intent Routing보다 먼저 검사한다.

### 6.2 scoring 개념

MVP에서는 다음 용어만 내부 모델로 사용하고, 기본 개발자 화면에는 노출하지 않는다.

```text
confidence: 선택된 Intent의 최종 신뢰도
margin: 1위 Intent와 2위 Intent의 점수 차이
threshold: confident 판정을 위한 최소 점수
negative_penalty: negative example과의 유사도에 따른 감점
```

개발자 화면에서는 다음 언어를 사용한다.

```text
이 Intent에 해당하는 질문 예시
이 Intent로 가면 안 되는 헷갈리는 질문 예시
애매하면 사용자에게 확인
맞는 Intent가 없으면 fallback
```

---

## 7. MVP 엔진 흐름

```text
Request
  |
  v
Auth Layer
  - app_id 확인
  - API Key 확인
  - service_id 접근 권한 확인
  |
  v
Policy Layer
  - risk pattern/policy 검사
  - service별 허용 Intent 목록 로드
  - off_topic 후보 검사
  |
  v
Candidate Layer
  - include keyword boost
  - exclude keyword penalty
  - allowed intent filtering
  |
  v
Semantic Layer
  - positive example similarity
  - negative example similarity
  - confidence, margin 계산
  |
  v
Decision Layer
  - confident / clarify / fallback / off_topic / risk / unauthorized 산출
  |
  v
Response + Trace Log
```

---

## 8. MVP 범위 반영

### 8.1 MVP에 포함

- 독립 Intent Routing API
- service_id, app_id, API Key 기반 호출 인증
- 서비스별 Intent Catalog
- Intent별 positive/negative example
- Intent별 route_key 매핑
- include/exclude keyword 보정
- embedding 기반 의미 검색
- confidence/margin 기반 decision
- CSV 테스트 실행
- PASS/FAIL/REVIEW 결과
- trace_id 기반 기본 로그

### 8.2 MVP에서 제외

- 모델 선택 UI
- 자동 threshold 최적화
- 실시간 A/B 테스트
- 복잡한 승인 워크플로우
- 학습형 classifier 운영
- 기본 경로의 LLM judge 필수화
- 고급 대시보드
- 다중 외부 시스템 연계

---

## 9. PRD v0.2에 반영할 결정사항

PRD v0.2에는 다음을 결정사항으로 넣는다.

1. Intent Routing은 독립 서비스로 제공한다.
2. MVP에서는 Agent Platform 내부 기능이나 챗봇 백엔드 모듈로 구현하지 않는다.
3. Client system은 API를 통해 질의를 전달하고, 후속 업무 흐름 실행은 각 client system이 담당한다.
4. 라우팅 엔진은 하이브리드 구조를 사용한다.
5. 일반 Intent 판정은 positive/negative example 기반 의미 검색을 중심으로 한다.
6. risk와 unauthorized는 일반 Intent와 분리된 정책 레이어에서 우선 처리한다.
7. `clarify`와 `fallback`은 분리한다.
8. 운영 반영 전 CSV 테스트를 통과해야 한다.
9. MVP에서는 모델 파인튜닝과 LLM judge를 필수로 넣지 않는다.

---

## 10. 사용자 회신 반영 결정사항

2026-06-24 사용자 회신을 기준으로 다음 항목을 PRD v0.2 기본 결정사항으로 반영한다.

| 항목 | 결정 |
| --- | --- |
| 최초 연계 대상 | Dify Platform에서 HTTP Request node를 통해 Intent Routing Service API 호출 |
| latency 목표 | Intent Routing Service 내부 처리 기준 p95 5초 이하 |
| embedding 모델 | BGE-M3를 1순위 기본 모델로 선택. CPU-only 운영, 기본 최대 입력 길이 256 token |
| vector store | PostgreSQL + pgvector |
| pgvector 인덱스 전략 | MVP는 Exact Search로 시작 |
| 로그 저장/마스킹 | 요청 원문 저장. 단, 주민등록번호, 사업자등록번호, 휴대폰번호는 PII 마스킹 후 조회/노출 |
| 원문 조회 권한 | 시스템 오류 및 감사 목적으로 인가된 사용자만 조회 가능 |
| API Key 정책 | Dify 연계를 고려해 API Key 기반 인증을 기본으로 하되, 금융권 폐쇄망에 맞춰 네트워크 통제, scope, 회전, 감사 로그를 결합 |
| 운영 버전 모델 | `release_version` 중심으로 policy, catalog, model, vector index, test dataset을 묶어 운영 반영 |

---

## 10.1 Dify 연계 방식

MVP 최초 client는 Dify Platform으로 한다.

Dify workflow에서는 HTTP Request node를 사용해 Intent Routing Service를 호출한다. Dify HTTP Request node는 URL, header, query parameter, request body, authentication 설정을 지원하고, API Key 인증 방식으로 Basic, Bearer, Custom header를 지원한다.

### 권장 호출 형태

```http
POST /v1/intent-route
Authorization: Bearer <api_key>
X-App-Id: dify-platform
X-Service-Id: it-helpdesk
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

응답은 Dify workflow의 후속 `If-Else`, `Question Classifier`, `Tool`, `Answer` node에서 사용할 수 있도록 다음처럼 단순하고 안정적인 구조를 유지한다.

```json
{
  "trace_id": "irt-20260624-000001",
  "decision": "confident",
  "domain": "IT",
  "intent_id": "it_api_timeout",
  "confidence": 0.87,
  "route_key": "it.manual.lookup",
  "fallback_policy": null
}
```

### Timeout 기준

Dify HTTP Request node는 connect/read/write timeout을 설정할 수 있으므로, MVP에서는 client timeout을 5초보다 약간 크게 두되 서비스 목표는 p95 5초 이하로 정의한다.

latency 측정 기준은 Dify 전체 workflow 왕복 시간이 아니라 **Intent Routing Service 내부 처리 시간**이다. 즉 HTTP 또는 HTTPS 요청이 Intent Routing Service에 도착한 시점부터 response body를 반환하는 시점까지를 측정한다.

권장 내부 목표는 다음과 같다.

| 구분 | 목표 |
| --- | --- |
| p50 latency | 1초 이하 |
| p95 latency | 5초 이하 |
| timeout | client 설정 기준 6~8초 |
| fallback | timeout 또는 5xx 발생 시 Dify workflow에서 고정 fallback 응답 또는 상담원 연결 |

---

## 10.2 Embedding 모델 결정

### 선택 모델

**BGE-M3를 MVP 기본 embedding 모델로 선택한다.**

선택 이유는 다음이다.

- MIT license로 폐쇄망 반입 및 내부 운영 검토가 상대적으로 수월하다.
- 한국어를 포함한 100개 이상 언어를 지원한다.
- 1024차원 dense embedding을 제공하므로 pgvector에 저장하기 쉽다.
- 최대 8192 token 입력을 지원해 짧은 질의와 긴 업무 문장을 모두 다룰 수 있다.
- dense retrieval, sparse retrieval, multi-vector retrieval을 함께 지원하므로 MVP 이후 hybrid retrieval 확장 여지가 있다.
- sentence-transformers 또는 FlagEmbedding 기반으로 내부망 배포가 가능하다.

### MVP 사용 방식

MVP에서는 BGE-M3의 dense embedding만 사용한다.

```text
query
-> BGE-M3 dense embedding
-> pgvector cosine similarity search
-> positive/negative example score 계산
-> confidence + margin 산출
```

초기에는 sparse/multi-vector 기능을 쓰지 않는다. 기능을 모두 열면 정확도 튜닝보다 운영 복잡도가 먼저 커질 수 있기 때문이다.

### 운영 형태

MVP에서는 BGE-M3를 CPU-only로 운영한다. 기본 최대 입력 길이는 256 token으로 시작한다. 단, 최대 입력 길이는 시스템 관리자가 환경 설정으로 변경할 수 있어야 한다.

기본값을 256 token으로 두는 이유는 Intent Routing의 주 입력이 짧은 사용자 질의이기 때문이다. 입력 길이를 너무 크게 열어두면 embedding 처리 시간이 늘고, 긴 문장 안의 부가 설명이 의도 판단을 흐릴 수 있다. 긴 입력이 필요한 서비스는 시스템 관리자가 서비스별 설정으로 512, 1024 또는 그 이상을 허용한다.

batch size는 사용 목적별로 다르게 둔다.

| 구분 | 추천 |
| --- | --- |
| 실시간 API | `batch_size=1~8` |
| 동적 micro-batching | 최대 batch 16, 대기 10~30ms 이내 |
| CSV 테스트 | `batch_size=16~64` |
| Intent example 재색인 | `batch_size=16~64` |
| 1024 token 이상 긴 입력 | `batch_size=4~16` |
| 8192 token 실험 | `batch_size=1~4`부터 시작 |

실시간 API는 latency가 중요하므로 작은 batch를 사용한다. CSV 테스트와 example 재색인은 처리량이 중요하므로 더 큰 batch를 사용할 수 있다. 1024 token 이상 긴 입력은 메모리 사용량이 커지므로 batch size를 낮춘다.

### pgvector 저장 기준

BGE-M3 dense vector는 1024차원이므로 pgvector column은 다음 개념으로 정의한다.

```sql
embedding vector(1024)
```

유사도는 cosine similarity 기준을 기본으로 한다.

```sql
SELECT
  example_id,
  1 - (embedding <=> :query_embedding) AS similarity
FROM intent_examples
WHERE service_id = :service_id
ORDER BY embedding <=> :query_embedding
LIMIT 20;
```

MVP 초기에는 Exact Search로 시작한다. 초기 데이터 규모에서는 재현 가능하고 튜닝이 단순한 방식이 더 중요하기 때문이다. 데이터가 늘어나거나 vector search 구간이 p95 latency를 압박하면 HNSW index 전환을 검토한다.

HNSW 전환 시에는 아래와 같은 index를 사용할 수 있다. 이 SQL은 MVP 초기 적용 대상이 아니라 전환 검토용 예시다.

```sql
CREATE INDEX intent_examples_embedding_hnsw_idx
ON intent_examples
USING hnsw (embedding vector_cosine_ops);
```

---

## 10.3 로그 저장 및 PII 마스킹

### 결정

요청 원문은 저장한다.

다만 로그 조회, 운영 화면 노출, 외부 반출용 export에서는 다음 개인 식별번호를 마스킹한다.

| 대상 | 예시 | 마스킹 예시 |
| --- | --- | --- |
| 주민등록번호 | `900101-1234567` | `900101-1******` |
| 사업자등록번호 | `123-45-67890` | `123-45-*****` |
| 휴대폰번호 | `010-1234-5678` | `010-****-5678` |

### 저장 구조

MVP에서는 다음 두 값을 분리해 저장한다.

| 필드 | 설명 |
| --- | --- |
| `query_raw_encrypted` | 원문 질의. DB 암호화 또는 application-level encryption 적용 |
| `query_masked` | 운영 화면과 검색에 사용하는 마스킹 질의 |

기본 화면, 테스트 결과, 운영 로그에서는 `query_masked`만 노출한다.  
`query_raw_encrypted` 조회는 별도 권한과 감사 로그를 요구한다. 조회 목적은 시스템 오류 분석 또는 감사 대응으로 제한한다. 인가된 사용자만 원문 조회를 요청할 수 있으며, 조회 요청 사유를 남겨야 한다.

### 감사 로그

원문 조회가 발생하면 다음 정보를 남긴다.

```text
trace_id
viewed_by
view_reason
view_time
source_ip
service_id
```

---

## 10.4 API Key 정책 결정

### 기본 방향

MVP에서는 Dify HTTP Request node의 현실적인 연계 방식을 고려해 API Key 기반 인증을 사용한다.

다만 OWASP REST Security Cheat Sheet 기준으로 API Key만으로 민감하거나 중요한 자원을 보호하면 부족하므로, 금융권 폐쇄망 환경에서는 다음 통제를 함께 적용한다.

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

가능하면 API Gateway 또는 service mesh 계층에서 mTLS를 적용한다. Dify HTTP Request node 자체에서 client certificate 운용이 어렵다면, Dify가 위치한 내부망 구간과 API Gateway에서 인증서를 처리한다.

### 요청 header

```http
Authorization: Bearer <api_key>
X-App-Id: dify-platform
X-Service-Id: it-helpdesk
X-Key-Id: key_live_20260624_001
X-Request-Id: {{workflow_run_id}}
```

`X-Key-Id`는 key lookup과 회전 추적용이다. 실제 secret은 `Authorization` header에만 둔다.

### Key 발급 기준

| 항목 | 정책 |
| --- | --- |
| 단위 | `environment + app_id + service_id` 단위로 발급 |
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

### HMAC 요청 서명은 v1.1 후보

Dify 기본 HTTP Request 설정만으로는 정교한 HMAC signature 생성이 번거로울 수 있다. 따라서 MVP에서는 Bearer API Key + 네트워크 통제 + scope + 회전을 기본으로 한다.

다만 Dify Code node 또는 Gateway plugin을 사용할 수 있다면 v1.1에서 다음 서명을 추가한다.

```http
X-Timestamp: 2026-06-24T16:30:00+09:00
X-Nonce: 8f6c0f6d-...
X-Signature: base64(hmac-sha256(secret, method + path + timestamp + nonce + body_hash))
```

서명 방식은 replay 방지와 요청 무결성 검증에 유리하지만, MVP에서는 Dify 연계 복잡도를 먼저 낮춘다.

---

## 10.5 운영 버전 모델 상세

운영 버전 모델은 "지금 운영 중인 라우팅 결과를 나중에 정확히 재현할 수 있게 만드는 체계"다.

Intent Routing Service는 질의 하나의 결과도 여러 요소에 의해 결정된다.

```text
Intent 예시
keyword
threshold
risk policy
embedding model
pgvector index
test dataset
release 시점
```

따라서 단순히 `model_version`만 남기면 부족하다. 운영에는 여러 버전을 하나로 묶은 `release_version`이 올라가야 한다.

### 버전 종류

| 버전 | 의미 | 변경 예시 |
| --- | --- | --- |
| `policy_version` | decision 기준, threshold, margin, risk/off_topic/unauthorized 정책 | risk pattern 추가, threshold 변경 |
| `intent_catalog_version` | Intent 정의, route_key, positive/negative example, include/exclude keyword | 예시 추가, route_key 변경 |
| `model_version` | embedding 모델명, weight checksum, tokenizer, inference parameter | BGE-M3 weight 갱신, tokenizer 변경 |
| `vector_index_version` | 특정 catalog와 model로 생성한 pgvector embedding/index snapshot | example 재임베딩, HNSW index 재생성 |
| `test_dataset_version` | 운영 반영 전 검증에 사용한 CSV 테스트셋 snapshot | critical case 추가 |
| `release_version` | 운영에 올라가는 불변 묶음 | 정책+카탈로그+모델+인덱스+테스트 결과 묶음 |

### release_version 구성

`release_version`은 다음 정보를 반드시 포함한다.

```json
{
  "release_version": "rel-it-helpdesk-20260624-001",
  "service_id": "it-helpdesk",
  "environment": "prod",
  "policy_version": "pol-20260624-001",
  "intent_catalog_version": "cat-20260624-003",
  "model_version": "emb-bge-m3-sha256-7c9a...",
  "vector_index_version": "vec-cat-003-bge-m3-001",
  "test_dataset_version": "tds-20260624-002",
  "test_run_id": "tr-20260624-015",
  "pass_rate": 0.91,
  "critical_pass_rate": 1.0,
  "released_by": "user123",
  "released_at": "2026-06-24T16:30:00+09:00",
  "rollback_target": "rel-it-helpdesk-20260620-004"
}
```

### 운영 반영 흐름

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
   - off_topic case 100% PASS
   - positive/confusing/fallback 실패 건 확인 및 수정
   - REVIEW 비율 기준 초과 시 개선 권고

5. Release 생성
   - release_version 생성
   - 운영 active pointer 변경

6. Runtime 호출
   - 모든 응답 로그에 release_version 기록

7. Rollback
   - 이전 release_version으로 active pointer 복구
```

### Runtime log 필수 필드

라우팅 API 응답과 내부 로그에는 다음 버전 정보를 남긴다.

```text
trace_id
service_id
release_version
policy_version
intent_catalog_version
model_version
vector_index_version
decision
intent_id
confidence
route_key
```

이렇게 해야 운영 중 오분류가 발생했을 때 "그때 어떤 설정과 모델로 그런 결과가 나왔는지"를 재현할 수 있다.

### MVP 최소 구현

MVP에서 실제로 강제해야 하는 최소 버전은 다음 네 가지다.

```text
release_version
policy_version
intent_catalog_version
test_run_id
```

`model_version`과 `vector_index_version`도 로그 필드에는 포함하되, UI에서 상세 관리하는 기능은 Sprint 0 이후로 미룰 수 있다.

---

## 10.6 CSV 테스트 기준

CSV 테스트는 개발자가 모델 평가 지표를 직접 관리하게 만드는 기능이 아니다. 개발자는 간단한 테스트 케이스를 작성하고, 시스템이 내부적으로 expected decision, route_key, gate 조건을 계산한다.

### 개발자용 CSV 형식

MVP 개발자용 CSV는 다음 컬럼을 기본으로 한다.

```csv
case_id,query,expected_intent,case_type,memo
C001,보험금 청구 방법 알려줘,insurance_claim,positive,정상 보험금 청구 문의
C002,보험금 청구 화면에서 500 에러가 나요,it_error,confusing,보험금 청구 단어가 있지만 실제로는 IT 오류
C003,시스템 해킹 방법 알려줘,,risk,위험 질의
C004,오늘 날씨 어때,,off_topic,서비스 범위 밖
C005,대출 한도 조회해줘,,fallback,현재 서비스에 없는 intent
```

개발자는 다음 두 가지만 판단하면 된다.

```text
1. 이 질문은 어떤 종류인가?
   - positive
   - confusing
   - risk
   - off_topic
   - fallback

2. 업무 질문이면 어느 expected_intent로 가야 하는가?
```

`expected_decision`, `expected_route_key`, `priority`, `must_pass`는 개발자용 CSV에 넣지 않는다. 시스템이 `case_type`과 Intent Catalog를 기준으로 자동 추론한다.

### case_type별 내부 기대값

| `case_type` | 개발자 의미 | 시스템 내부 기대값 |
| --- | --- | --- |
| `positive` | 정상 질문 | `decision=confident`, `intent_id=expected_intent` |
| `confusing` | 단어는 헷갈리지만 정답 Intent가 명확한 질문 | `decision=confident`, `intent_id=expected_intent` |
| `risk` | 위험 질문 | `decision=risk` |
| `off_topic` | 서비스 범위 밖 질문 | `decision=off_topic` |
| `fallback` | 등록된 Intent에 없는 질문 | `decision=fallback` |

### 운영 반영 판단 기준

| 기준 | 쉬운 설명 | 운영 반영 판단 |
| --- | --- | --- |
| `risk` 케이스 | 위험 질문은 반드시 위험으로 잡아야 함 | 1건이라도 실패하면 차단 |
| `off_topic` 케이스 | 서비스 범위 밖 질문은 반드시 범위 밖으로 잡아야 함 | 1건이라도 실패하면 차단 |
| `positive` 케이스 | 정상 질문은 기대 Intent로 가야 함 | 실패 건 수정 필요 |
| `confusing` 케이스 | 헷갈리는 질문도 올바른 Intent로 가야 함 | 실패 건 수정 필요 |
| `fallback` 케이스 | 없는 업무를 억지로 분류하면 안 됨 | 실패 건 수정 필요 |
| `REVIEW` 비율 | 너무 많은 질문이 애매하면 설정이 부족함 | 기준 초과 시 개선 권고 |

### 결과 표시 원칙

개발자 화면에서는 PASS율이나 threshold보다 실패 원인과 다음 조치를 먼저 보여준다.

```text
테스트 결과: 운영 반영 불가

위험 질문: 3/3 통과
범위 밖 질문: 2/2 통과
정상 질문: 8/10 통과
헷갈리는 질문: 7/8 통과
없는 업무 질문: 2/2 통과
검토 필요: 2건

수정 필요:
- "보험금 청구 화면에서 500 에러가 나요"가 insurance_claim으로 분류됨
  -> it_error positive example 또는 insurance_claim negative example 추가 권장
```

### REVIEW 비율 기준

MVP에서는 REVIEW 비율의 정확한 차단 수치를 hard gate로 두지 않는다. 초기에는 15% 초과 시 개선 권고로 시작하고, 운영 데이터가 쌓이면 서비스별 기준을 조정한다.

---

## 10.7 회신 2 반영 결정사항

다음 항목은 2026-06-24 사용자 회신 2를 기준으로 확정한다.

| 항목 | 결정 |
| --- | --- |
| BGE-M3 운영 형태 | CPU-only |
| 기본 최대 입력 길이 | 256 token |
| 최대 입력 길이 변경 | 시스템 관리자가 변경 가능 |
| 실시간 API batch size | 1~8 |
| 동적 micro-batching | 최대 batch 16, 대기 10~30ms 이내 |
| CSV 테스트 batch size | 16~64 |
| Intent example 재색인 batch size | 16~64 |
| 1024 token 이상 긴 입력 batch size | 4~16 |
| 8192 token 실험 batch size | 1~4부터 시작 |
| latency 측정 기준 | Intent Routing Service 내부 처리 시간. HTTP/HTTPS 요청 수신부터 response 반환까지 |
| 원문 조회 권한 | 시스템 오류 및 감사 목적으로 인가된 사용자만 조회 가능 |
| pgvector 인덱스 전략 | MVP는 Exact Search로 시작 |
| CSV 테스트 기준 | 개발자용 CSV는 단순화하고, 시스템이 내부 gate 기준을 계산 |

---

## 11. 참고 근거

### Semantic Routing / Router

- [Semantic Router GitHub](https://github.com/aurelio-labs/semantic-router): embedding 기반 route decision layer의 대표적인 오픈소스 예시
- [vLLM Semantic Router GitHub](https://github.com/vllm-project/semantic-router): signal-driven routing, policy, authorization, safety signal을 조합하는 router 방향 참고
- [vLLM Semantic Router paper](https://arxiv.org/abs/2603.04444): heuristic signal, neural classifier, authorization, safety signal 등을 configurable decision rule로 조합하는 구조 참고
- [vLLM Production Stack semantic router integration](https://docs.vllm.ai/projects/production-stack/en/latest/use_cases/semantic-router-integration.html): routing을 별도 decision layer로 두고 downstream model/system을 선택하는 패턴 참고

### Intent Classification / Fallback / OOS

- [Rasa Fallback and Human Handoff](https://rasa.com/docs/rasa/fallback-handoff/): fallback, out-of-scope, handoff를 분리해 처리하는 제품 구조 참고
- [CLINC OOS Evaluation Dataset](https://github.com/clinc/oos-eval): in-scope intent와 out-of-scope query를 함께 평가해야 한다는 방향 참고
- [Improved Out-of-Scope Intent Classification with Dual Encoding and Threshold-Based Re-Classification](https://aclanthology.org/2024.lrec-main.763.pdf): OOS 판정에서 threshold와 재분류 구조를 활용하는 연구 방향 참고

### Embedding / Few-shot Classification

- [BGE-M3 Hugging Face model card](https://huggingface.co/BAAI/bge-m3): MIT license, 100개 이상 언어, 1024차원, 8192 token, dense/sparse/multi-vector 지원 근거
- [Sentence-BERT](https://arxiv.org/abs/1908.10084): sentence embedding과 cosine similarity 기반 의미 유사도 검색의 근거
- [Multilingual E5 Text Embeddings](https://arxiv.org/abs/2402.05672): 다국어 embedding 모델 후보군 검토 근거
- [BGE-M3](https://arxiv.org/abs/2402.03216): 다국어, dense/sparse/multi-vector retrieval을 함께 지원하는 embedding 모델 후보군 검토 근거
- [SetFit](https://arxiv.org/abs/2209.11055): labeled data가 쌓인 이후 few-shot classifier 확장 가능성 검토 근거

### Dify / Vector Store / API Security

- [Dify HTTP Request node](https://docs.dify.ai/en/use-dify/nodes/http-request): Dify workflow에서 외부 API 호출, header/body/authentication, timeout, retry/error handling 설정 가능 근거
- [pgvector GitHub](https://github.com/pgvector/pgvector): PostgreSQL 내 vector similarity search, cosine distance, HNSW index 지원 근거
- [OWASP REST Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html): HTTPS, access control, API Key 한계, rate limit, revoke, audit log 근거
- [OWASP API Security Top 10 - Broken Authentication](https://owasp.org/API-Security/editions/2023/en/0xa2-broken-authentication/): API 인증 취약점과 인증 통제 필요성 근거
- [NIST SP 800-57 Part 1 Rev. 5](https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final): cryptographic key management, key inventory, key management policy 근거
