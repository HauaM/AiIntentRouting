
# 1. 우리 프로젝트 내부 기준 자료

| 자료                                | 구분     | 사용 목적                                                                                                                                                                                         |
| --------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **AiIntentRoutingEngine_v0.1.md** | 내부 PRD | 현재 논의의 기준 문서입니다. 금융권 폐쇄망 환경에서 여러 AI Agent, 챗봇, 내부 업무 시스템이 공통으로 사용할 Intent Routing Service를 정의하고 있고, 보안, 권한, CSV 테스트, positive/negative example, route_key, decision, 감사 로그, MVP 범위 등을 포함합니다.  |

이 문서가 가장 중요한 1차 자료입니다. 외부 자료들은 이 PRD를 대체하기 위한 것이 아니라, **PRD의 아키텍처 판단과 MVP 범위 조정을 위한 근거**로 사용했습니다.

---

# 2. Semantic Routing / Intent Routing 관련 참고 자료

| 자료                                         | 구분      | 참고한 이유                                                                                                                                                                    | 우리 PRD 반영 포인트                                                      |
| ------------------------------------------ | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| **Semantic Router**                        | 오픈소스    | LLM에게 매번 판단시키지 않고, semantic vector space를 활용해 route/tool-use 결정을 빠르게 수행하는 구조를 참고했습니다. ([GitHub][1])                                                                       | positive example 기반 route 선택, route별 threshold, 빠른 intent 후보 생성 구조 |
| **Semantic Router Threshold Optimization** | 문서      | route score threshold가 route 선택 여부를 결정한다는 점을 확인했습니다. ([docs.aurelio.ai][2])                                                                                               | `보수적/일반/적극적 분류` 프리셋을 내부적으로 threshold/margin 정책으로 연결                |
| **vLLM Semantic Router 문서**                | 오픈소스 문서 | 요청을 분석해 적절한 모델로 routing하는 production stack 구조를 참고했습니다. ([vLLM][3])                                                                                                        | 단일 모델 고정이 아니라, 요청 특성에 따라 분류 방식/모델 선택 가능하게 설계                       |
| **vLLM Semantic Router 논문**                | 논문      | keyword pattern, language detection, context length, role-based authorization, embedding similarity 등 여러 signal을 조합해 routing policy를 만든다는 점이 우리 구조와 잘 맞았습니다. ([arXiv][4]) | 단일 분류기가 아니라 **signal 기반 decision composer** 구조로 설계                 |

**정리 의견:**
우리 서비스는 “LLM에게 이 Intent가 뭔지 물어보는 API”가 아니라, **서비스 정책 + rule + keyword + semantic similarity + fallback + risk 판단을 조합하는 라우팅 엔진**으로 가야 합니다.

---

# 3. Intent Classification / Fallback 관련 참고 자료

| 자료                                  | 구분      | 참고한 이유                                                                                | 우리 PRD 반영 포인트                                        |
| ----------------------------------- | ------- | ------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| **Rasa Intents and Entities**       | 오픈소스 문서 | intent별 사용자 발화 예시를 관리하는 구조를 참고했습니다. ([Rasa][5])                                       | positive example 중심 Intent 설정                        |
| **Rasa Training Data Format**       | 오픈소스 문서 | NLU training data를 YAML 등으로 관리하는 구조를 참고했습니다. ([Rasa][6])                              | Intent Catalog / Example 데이터 구조 설계                   |
| **Rasa FallbackClassifier**         | 오픈소스 문서 | confidence가 낮거나 상위 intent 간 점수 차이가 작을 때 fallback intent를 예측하는 구조를 참고했습니다. ([Rasa][7]) | `confidence`, `margin`, `clarify`, `fallback`의 구분 기준 |
| **Rasa Fallback and Human Handoff** | 오픈소스 문서 | fallback 시 기본 응답 또는 handoff 흐름으로 보내는 구조를 참고했습니다. ([Rasa][8])                          | `fallback_policy`, 상담원 연결, 명확화 질문 흐름                 |

**정리 의견:**
우리 PRD의 `clarify`와 `fallback`은 반드시 분리해야 합니다.

* `clarify`: 후보 Intent가 여러 개라 사용자 확인이 필요함
* `fallback`: 적절한 후보 자체가 없음

---

# 4. Out-of-Scope / Off-topic 관련 참고 자료

| 자료                                                                                         | 구분 | 참고한 이유                                                                  | 우리 PRD 반영 포인트                                         |
| ------------------------------------------------------------------------------------------ | -- | ----------------------------------------------------------------------- | ----------------------------------------------------- |
| **An Evaluation Dataset for Intent Classification and Out-of-Scope Prediction / CLINC150** | 논문 | 실제 대화 시스템은 모든 질문이 지원 Intent 안에 들어온다고 가정하면 안 된다는 점을 확인했습니다. ([arXiv][9]) | `off_topic` decision, 무관질의 테스트셋, mixed_keyword 케이스 필요 |

**정리 의견:**
금융권 챗봇에서 특히 위험한 케이스는 이런 것입니다.

```text
예금 오늘 날씨 어때
보험금 청구 메뉴 개발 중 API Timeout 원인이 뭐야
대출 금리 말고 점심 메뉴 추천해줘
```

금융 단어가 포함되어도 실제 의도는 무관질의이거나 IT문의일 수 있습니다. 그래서 `off_topic`은 일반 Intent 중 하나가 아니라 **별도 검증 대상**으로 봐야 합니다.

---

# 5. Embedding / Semantic Similarity 관련 참고 자료

| 자료                                                                    | 구분    | 참고한 이유                                                                                         | 우리 PRD 반영 포인트                          |
| --------------------------------------------------------------------- | ----- | ---------------------------------------------------------------------------------------------- | -------------------------------------- |
| **Sentence-BERT / SBERT**                                             | 논문    | 문장 임베딩을 만들어 cosine similarity로 빠르게 비교할 수 있다는 점을 참고했습니다. ([arXiv][10])                          | positive/negative example 기반 의미 유사도 검색 |
| **E5: Text Embeddings by Weakly-Supervised Contrastive Pre-training** | 논문    | retrieval, clustering, classification 등에 쓸 수 있는 범용 text embedding 모델 계열로 참고했습니다. ([arXiv][11]) | 초기 MVP에서 파인튜닝 없이 embedding 기반 후보 생성    |
| **BGE-M3**                                                            | 논문/모델 | 다국어, dense retrieval, sparse retrieval, 긴 문서 입력 등 범용성이 높아 후보로 참고했습니다. ([arXiv][12])            | 폐쇄망 환경에서 범용 embedding 후보군 검토           |
| **Multilingual E5**                                                   | 논문    | multilingual E5 모델이 inference 효율성과 embedding 품질 간 균형을 제공한다는 점을 참고했습니다. ([arXiv][13])           | 한국어/다국어 질의 대응 후보                       |
| **multilingual-e5-small-ko**                                          | 모델 카드 | 한국어 검색에 맞춘 경량 retriever로 소개되어 있어 PoC 후보로 참고했습니다. ([Hugging Face][14])                          | 폐쇄망/경량 MVP에서 실험 후보                     |
| **KURE-v1**                                                           | 모델 카드 | 공개 한국어 retrieval embedding 모델 중 강한 성능을 보인다고 소개되어 있어 후보로 참고했습니다. ([Hugging Face][15])           | 한국어 금융 질의 검색 성능 검토 후보                  |

**정리 의견:**
MVP에서 모델 파인튜닝은 제외하는 게 맞습니다. 대신 **사전학습 embedding 모델 + positive/negative example 기반 semantic routing**으로 시작하는 것이 적절합니다.

---

# 6. Few-shot / 향후 학습 확장 관련 참고 자료

| 자료                                                      | 구분      | 참고한 이유                                                                                                | 우리 PRD 반영 포인트                              |
| ------------------------------------------------------- | ------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| **SetFit: Efficient Few-Shot Learning Without Prompts** | 논문/오픈소스 | 적은 labeled example으로도 Sentence Transformer 기반 few-shot classification이 가능하다는 점을 참고했습니다. ([arXiv][16]) | MVP에서는 제외하되, 나중에 쌓인 example을 학습 데이터로 활용 가능 |
| **Hugging Face SetFit**                                 | 오픈소스    | 적은 라벨 데이터로도 text classification을 할 수 있는 구현체로 참고했습니다. ([GitHub][17])                                   | v1 이후 fine-tuning / few-shot classifier 후보 |

**정리 의견:**
지금은 학습 기능을 만들면 안 됩니다. 하지만 positive/negative example 데이터는 나중에 학습 데이터가 될 수 있으므로, 처음부터 `source`, `created_by`, `approved`, `service_id`, `intent_id`, `test_case_id` 같은 메타데이터를 남기는 구조가 좋습니다.

---

# 7. Router / Agent Framework 관련 참고 자료

| 자료                                 | 구분       | 참고한 이유                                                                               | 우리 PRD 반영 포인트                                           |
| ---------------------------------- | -------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------- |
| **LangChain Router Pattern**       | 프레임워크 문서 | routing step이 입력을 분류해 specialized agent로 보낸다는 구조를 참고했습니다. ([LangChain Docs][18])     | route_key 기반 후속 Agent/Flow 선택                           |
| **LangChain Multi-agent Router**   | 프레임워크 문서 | router가 query를 적절한 agent로 보내는 패턴을 참고했습니다. ([LangChain Docs][19])                     | Dify/Agent Platform 연계 구조                               |
| **LlamaIndex Router Query Engine** | 프레임워크 문서 | 여러 query engine 중 적절한 엔진을 selector로 선택하는 구조를 참고했습니다. ([Developer Documentation][20]) | `route_key`를 단순 문자열이 아니라 후속 처리 경로 계약으로 관리               |
| **LlamaIndex Routers**             | 프레임워크 문서 | router의 핵심이 selector 정의라는 점을 참고했습니다. ([Developer Documentation][21])                 | Intent Routing Service의 핵심도 selector/decision model로 정의 |

**정리 의견:**
우리 서비스는 Agent 자체를 실행하는 서비스가 아닙니다. 대신 `route_key`를 통해 **어떤 Agent Flow, Dify Flow, 업무 흐름으로 보낼지 결정하는 앞단 라우터**입니다.

---

# 8. Guardrails / Risk 관련 참고 자료

| 자료                                | 구분       | 참고한 이유                                                                   | 우리 PRD 반영 포인트                                    |
| --------------------------------- | -------- | ------------------------------------------------------------------------ | ------------------------------------------------ |
| **NeMo Guardrails 논문**            | 논문       | LLM 기반 시스템에 programmable guardrails를 추가하는 구조를 참고했습니다. ([arXiv][22])      | `risk`는 일반 Intent와 분리된 policy layer로 설계          |
| **NVIDIA NeMo Guardrails GitHub** | 오픈소스     | 특정 주제 차단, 사전 정의된 대화 흐름, 구조화된 제어 등을 참고했습니다. ([GitHub][23])                | 위험질의 차단형 템플릿, 정책 기반 라우팅                          |
| **Guardrails AI**                 | 오픈소스/플랫폼 | Input/Output Guard를 통해 특정 위험을 감지·완화하는 구조를 참고했습니다. ([GitHub][24])         | risk/off_topic 검사 레이어                            |
| **LlamaFirewall**                 | 논문       | AI Agent 보안 위험에 대해 실시간 guardrail monitor가 필요하다는 점을 참고했습니다. ([arXiv][25]) | Agent 연계 전 안전 필터, prompt injection/risk 분류 확장 후보 |

**정리 의견:**
`risk`는 업무 Intent 중 하나로 취급하면 안 됩니다. `risk`는 일반 라우팅보다 먼저 동작하는 **안전 정책 레이어**로 보는 것이 맞습니다.

---

# 9. 테스트 / 평가 / 회귀 검증 관련 참고 자료

| 자료                  | 구분      | 참고한 이유                                                                     | 우리 PRD 반영 포인트                                                |
| ------------------- | ------- | -------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **promptfoo**       | 오픈소스    | LLM 앱을 평가하고 red-teaming하는 CLI/라이브러리로 참고했습니다. ([GitHub][26])                | CSV 테스트를 운영 반영 전 eval gate로 정의                               |
| **promptfoo Intro** | 문서      | reliable prompts, models, RAGs 평가 구조를 참고했습니다. ([Promptfoo][27])            | PASS/FAIL/REVIEW 기반 테스트 루프                                   |
| **DeepEval**        | 오픈소스    | Pytest처럼 LLM 앱을 테스트할 수 있는 평가 프레임워크로 참고했습니다. ([GitHub][28])                 | 테스트 케이스 기반 회귀 평가 구조                                          |
| **OpenAI Evals**    | 공식 문서   | 모델 출력이 지정한 스타일/내용 기준을 만족하는지 평가한다는 개념을 참고했습니다. ([OpenAI 개발자][29])           | expected_decision, expected_intent, expected_route_key 기반 평가 |
| **Ragas**           | 오픈소스 문서 | “감으로 확인”이 아니라 systematic evaluation loop가 필요하다는 관점으로 참고했습니다. ([Ragas][30]) | 테스트셋 기반 품질 개선 루프                                             |

**정리 의견:**
CSV 테스트는 단순 업로드 기능이 아닙니다. 우리 프로젝트에서는 **운영 반영 게이트**로 정의해야 합니다.

```text
설정 변경
→ CSV 테스트 실행
→ PASS/FAIL/REVIEW 확인
→ 기준 미달 시 운영 반영 차단
→ 실패 케이스 개선
→ 재테스트
→ 운영 반영
```

---

# 10. 보안 / 권한 / 정책 관리 관련 참고 자료

| 자료                                        | 구분       | 참고한 이유                                                                                                       | 우리 PRD 반영 포인트                                              |
| ----------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------- |
| **OWASP API Security Top 10 2023 - BOLA** | 보안 표준    | 사용자가 object ID를 조작해 권한 없는 객체에 접근하는 위험을 참고했습니다. ([OWASP Foundation][31])                                      | 개발자가 다른 서비스의 Intent/로그/테스트 결과를 볼 수 없도록 service_id 단위 권한 검사 |
| **OWASP API Security Project**            | 보안 표준    | API에서 object-level authorization이 넓은 공격면이라는 점을 참고했습니다. ([OWASP Foundation][32])                              | API Key 검증만으로 부족, 리소스 단위 권한 검증 필요                          |
| **Open Policy Agent / OPA**               | 오픈소스     | 정책을 코드로 관리하고, microservices/API gateway/Kubernetes 등에서 정책 결정을 위임할 수 있다는 점을 참고했습니다. ([Open Policy Agent][33]) | 권한 정책/운영 반영 정책을 별도 policy layer로 분리하는 후보                   |
| **Keycloak**                              | 오픈소스 IAM | 인증, 사용자 관리, 서비스 보안 기능을 제공하는 IAM으로 참고했습니다. ([Keycloak][34])                                                   | 관리자/개발자 콘솔 로그인, SSO/OIDC 연계 후보                             |
| **NIST SP 800-204A**                      | 보안 가이드   | service mesh가 microservice 기반 앱의 robust security infrastructure를 제공한다는 점을 참고했습니다. ([NIST CSRC][35])          | 추후 mTLS, service-to-service 보안, gateway/service mesh 검토 후보 |

**정리 의견:**
우리 서비스의 보안은 2단계로 봐야 합니다.

```text
1. 호출 시스템 인증
   - app_id
   - API Key
   - 운영/개발 Key 분리
   - 필요 시 IP 제한 / mTLS

2. 관리 사용자 권한
   - SSO/OIDC
   - 관리자/개발자 역할 분리
   - service_id 단위 접근 제어
   - 변경 이력 / 감사 로그
```

---

# 11. 관측성 / 감사 로그 관련 참고 자료

| 자료                       | 구분      | 참고한 이유                                                                                   | 우리 PRD 반영 포인트                  |
| ------------------------ | ------- | ---------------------------------------------------------------------------------------- | ------------------------------ |
| **OpenTelemetry Traces** | 오픈소스 표준 | request 단위 operation을 span/trace로 추적하는 개념을 참고했습니다. ([OpenTelemetry][36])                 | `trace_id` 중심 API 호출 추적        |
| **OpenTelemetry Logs**   | 오픈소스 표준 | LogRecord에 TraceId와 SpanId를 포함해 logs와 traces를 연결할 수 있다는 점을 참고했습니다. ([OpenTelemetry][37]) | API 호출, 분류, 테스트, 운영 반영 로그 연결   |
| **Jaeger**               | 오픈소스    | microservice 환경에서 요청 흐름을 추적하고 병목/오류를 찾는 distributed tracing 플랫폼으로 참고했습니다. ([Jaeger][38]) | 장애 분석, latency, trace_id 기반 조회 |

**정리 의견:**
PRD의 `trace_id`는 단순 응답 필드가 아니라, 다음을 연결하는 기준이어야 합니다.

```text
API 호출
→ 인증/권한 검사
→ 후보 Intent 산출
→ decision 산출
→ route_key 반환
→ 테스트 결과
→ 운영 로그
```

---

# 12. 모델 / 데이터 / 설정 버전 관리 관련 참고 자료

| 자료                  | 구분   | 참고한 이유                                                                                         | 우리 PRD 반영 포인트                                   |
| ------------------- | ---- | ---------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| **MLflow**          | 오픈소스 | 모델, LLM 앱, AI agent를 debug/evaluate/deploy/monitor하는 플랫폼으로 참고했습니다. ([MLflow AI Platform][39])  | model_id, model_version, 모델 변경 전후 테스트 결과 비교     |
| **MLflow Docs**     | 문서   | model lifecycle management, registry management 등 모델 관리 개념을 참고했습니다. ([MLflow AI Platform][40]) | 모델/분류방식 변경 이력 설계                                |
| **DVC**             | 오픈소스 | Git-like 방식으로 데이터, 모델, 실험을 관리하는 도구로 참고했습니다. ([DVC][41])                                        | test_dataset_version, example 데이터 버전 관리         |
| **DVC Get Started** | 문서   | Git 기반 데이터/모델 버전 관리 흐름을 참고했습니다. ([Data Version Control · DVC][42])                             | 운영 반영 시 test dataset version과 policy version 연결 |

**정리 의견:**
MVP에서 MLflow/DVC를 바로 도입하자는 의미는 아닙니다. 다만 PRD에는 최소한 아래 버전 개념이 있어야 합니다.

```text
policy_version
intent_catalog_version
test_dataset_version
model_version
release_version
```

---

# 13. 현재까지 자료 기반으로 잡은 핵심 판단

## 13.1 만들 가치가 있는가?

있습니다.

기존 PRD가 말한 것처럼, 각 AI 서비스가 의도분류를 따로 구현하면 Intent 기준, 예외 규칙, 테스트 데이터, 오분류 로그가 흩어집니다. 이 문제를 중앙에서 관리하려는 방향은 타당합니다. 

---

## 13.2 바로 전체 개발에 들어가도 되는가?

아직은 아닙니다.

현재 PRD의 MVP는 서비스 등록, API Key, RBAC, Intent Catalog, 프리셋, 모델 선택, CSV 테스트, 실패 개선, 운영 반영, 감사 로그, 외부 시스템 연계까지 포함합니다. 

이 범위는 MVP라기보다 v1.0에 가깝습니다.

---

## 13.3 MVP는 어디까지 줄여야 하는가?

자료를 기준으로 보면, MVP는 아래 흐름만 검증해도 충분합니다.

```text
서비스 등록
→ API Key 발급
→ Intent 3~5개 등록
→ positive/negative example 등록
→ route_key 매핑
→ 의도분류 API 호출
→ CSV 테스트 실행
→ PASS/FAIL/REVIEW 확인
→ 실패 케이스를 example로 추가
→ 재테스트
→ 기본 로그 확인
```

이 흐름이 제품의 핵심입니다.

---

## 13.4 최종 아키텍처 방향은?

최종 방향은 **하이브리드 Intent Routing Engine**이 맞습니다.

```text
API 인증/권한
→ 서비스별 허용 Intent 필터
→ risk/off_topic 정책 검사
→ keyword/rule 후보 보정
→ embedding 기반 semantic search
→ confidence + margin 기반 decision
→ 필요 시 LLM 후보 판정
→ route_key 반환
→ trace_id 로그 저장
```

이 방향이 좋은 이유는, Semantic Router와 vLLM Semantic Router는 라우팅을 단일 LLM 호출이 아니라 여러 signal 기반 결정으로 보는 쪽에 가깝고, Rasa는 fallback/ambiguity 기준을 참고할 수 있으며, 평가 프레임워크들은 테스트 기반 운영 반영의 필요성을 뒷받침하기 때문입니다. ([GitHub][1])

---

# 14. 최종 참고자료 목록만 따로 압축

## 내부 자료

* AiIntentRoutingEngine_v0.1.md 

## 오픈소스 / 공식 문서

* Semantic Router ([GitHub][1])
* Semantic Router Threshold Optimization ([docs.aurelio.ai][2])
* vLLM Semantic Router Docs ([vLLM][3])
* Rasa Intents and Entities ([Rasa][5])
* Rasa Training Data Format ([Rasa][6])
* Rasa FallbackClassifier ([Rasa][7])
* LangChain Router Pattern ([LangChain Docs][18])
* LlamaIndex Router Query Engine ([Developer Documentation][20])
* NeMo Guardrails ([GitHub][23])
* Guardrails AI ([GitHub][24])
* promptfoo ([GitHub][26])
* DeepEval ([GitHub][28])
* OpenAI Evals ([OpenAI 개발자][29])
* Ragas ([Ragas][30])
* OWASP API Security Top 10 ([OWASP Foundation][31])
* OPA ([Open Policy Agent][33])
* Keycloak ([Keycloak][34])
* OpenTelemetry ([OpenTelemetry][36])
* Jaeger ([Jaeger][38])
* MLflow ([MLflow AI Platform][39])
* DVC ([DVC][41])

## 논문 / 모델

* vLLM Semantic Router 논문 ([arXiv][4])
* CLINC150 / Out-of-Scope Intent Classification ([arXiv][9])
* Sentence-BERT ([arXiv][10])
* E5 Text Embeddings ([arXiv][11])
* BGE-M3 ([arXiv][12])
* Multilingual E5 ([arXiv][13])
* multilingual-e5-small-ko ([Hugging Face][14])
* KURE-v1 ([Hugging Face][15])
* SetFit ([arXiv][16])
* NeMo Guardrails 논문 ([arXiv][22])
* LlamaFirewall ([arXiv][25])

---

제 의견은 이렇습니다.
이 자료들은 “무엇을 다 넣자”는 근거가 아니라, 오히려 **무엇을 MVP에서 줄이고, 무엇을 핵심으로 남길지 판단하기 위한 근거**로 써야 합니다. 지금 단계에서 핵심 참고축은 **Semantic Router, Rasa, SBERT/E5 계열, promptfoo/OpenAI Evals, OWASP/OPA, OpenTelemetry** 정도면 충분합니다.

[1]: https://github.com/aurelio-labs/semantic-router?utm_source=chatgpt.com "aurelio-labs/semantic-router: Superfast AI decision making ..."
[2]: https://docs.aurelio.ai/semantic-router/user-guide/features/threshold-optimization?utm_source=chatgpt.com "Threshold optimization - Semantic Router - Aurelio AI"
[3]: https://docs.vllm.ai/projects/production-stack/en/latest/use_cases/semantic-router-integration.html?utm_source=chatgpt.com "Intelligent Semantic Routing — production-stack"
[4]: https://arxiv.org/abs/2603.04444?utm_source=chatgpt.com "vLLM Semantic Router: Signal Driven Decision Routing for Mixture-of-Modality Models"
[5]: https://rasa.com/docs/reference/primitives/intents-and-entities/?utm_source=chatgpt.com "Intents and Entities | Rasa Documentation"
[6]: https://rasa.com/docs/reference/primitives/training-data-format/?utm_source=chatgpt.com "Training Data Format | Rasa Documentation"
[7]: https://rasa.com/docs/rasa/next/components/?utm_source=chatgpt.com "Components - Rasa"
[8]: https://rasa.com/docs/rasa/fallback-handoff/?utm_source=chatgpt.com "Fallback and Human Handoff - Rasa"
[9]: https://arxiv.org/abs/1909.02027?utm_source=chatgpt.com "An Evaluation Dataset for Intent Classification and Out-of-Scope Prediction"
[10]: https://arxiv.org/abs/1908.10084?utm_source=chatgpt.com "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks"
[11]: https://arxiv.org/abs/2212.03533?utm_source=chatgpt.com "Text Embeddings by Weakly-Supervised Contrastive Pre-training"
[12]: https://arxiv.org/abs/2402.03216?utm_source=chatgpt.com "BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation"
[13]: https://arxiv.org/abs/2402.05672?utm_source=chatgpt.com "Multilingual E5 Text Embeddings: A Technical Report"
[14]: https://huggingface.co/dragonkue/multilingual-e5-small-ko?utm_source=chatgpt.com "dragonkue/multilingual-e5-small-ko"
[15]: https://huggingface.co/nlpai-lab/KURE-v1?utm_source=chatgpt.com "nlpai-lab/KURE-v1"
[16]: https://arxiv.org/abs/2209.11055?utm_source=chatgpt.com "Efficient Few-Shot Learning Without Prompts"
[17]: https://github.com/huggingface/setfit?utm_source=chatgpt.com "huggingface/setfit: Efficient few-shot learning with ..."
[18]: https://docs.langchain.com/oss/python/langchain/multi-agent/router-knowledge-base?utm_source=chatgpt.com "Build a multi-source knowledge base with routing"
[19]: https://docs.langchain.com/oss/python/langchain/multi-agent?utm_source=chatgpt.com "Multi-agent - Docs by LangChain"
[20]: https://developers.llamaindex.ai/python/examples/workflow/router_query_engine/?utm_source=chatgpt.com "Router Query Engine | Developer Documentation - LlamaParse"
[21]: https://developers.llamaindex.ai/python/framework/module_guides/querying/router/?utm_source=chatgpt.com "Routers | Developer Documentation - LlamaParse"
[22]: https://arxiv.org/abs/2310.10501?utm_source=chatgpt.com "NeMo Guardrails: A Toolkit for Controllable and Safe LLM Applications with Programmable Rails"
[23]: https://github.com/NVIDIA-NeMo/Guardrails?utm_source=chatgpt.com "NVIDIA NeMo Guardrails library"
[24]: https://github.com/guardrails-ai/guardrails?utm_source=chatgpt.com "Adding guardrails to large language models."
[25]: https://arxiv.org/abs/2505.03574?utm_source=chatgpt.com "LlamaFirewall: An open source guardrail system for building secure AI agents"
[26]: https://github.com/promptfoo/promptfoo?utm_source=chatgpt.com "Promptfoo: LLM evals & red teaming"
[27]: https://www.promptfoo.dev/docs/intro/?utm_source=chatgpt.com "Intro"
[28]: https://github.com/confident-ai/deepeval?utm_source=chatgpt.com "confident-ai/deepeval: The LLM Evaluation Framework"
[29]: https://developers.openai.com/api/docs/guides/evals?utm_source=chatgpt.com "Working with evals | OpenAI API"
[30]: https://docs.ragas.io/en/stable/?utm_source=chatgpt.com "Ragas"
[31]: https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/?utm_source=chatgpt.com "API1:2023 Broken Object Level Authorization"
[32]: https://owasp.org/www-project-api-security/?utm_source=chatgpt.com "OWASP API Security Project"
[33]: https://openpolicyagent.org/docs?utm_source=chatgpt.com "Open Policy Agent (OPA)"
[34]: https://www.keycloak.org/?utm_source=chatgpt.com "Keycloak"
[35]: https://csrc.nist.gov/pubs/sp/800/204/a/final?utm_source=chatgpt.com "SP 800-204A, Building Secure Microservices-based ..."
[36]: https://opentelemetry.io/docs/concepts/signals/traces/?utm_source=chatgpt.com "Traces"
[37]: https://opentelemetry.io/docs/specs/otel/logs/?utm_source=chatgpt.com "OpenTelemetry Logging"
[38]: https://www.jaegertracing.io/?utm_source=chatgpt.com "Jaeger Tracing"
[39]: https://mlflow.org/?utm_source=chatgpt.com "MLflow - Open Source AI Platform for Agents, LLMs & Models"
[40]: https://mlflow.org/docs/latest/?utm_source=chatgpt.com "MLflow Documentation | MLflow AI Platform"
[41]: https://dvc.org/?utm_source=chatgpt.com "DVC: Home"
[42]: https://doc.dvc.org/start?utm_source=chatgpt.com "Get Started with DVC | Data Version Control · DVC"
