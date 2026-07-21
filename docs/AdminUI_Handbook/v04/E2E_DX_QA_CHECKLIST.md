# Admin UI 전체 E2E DX QA 체크리스트

작성일: 2026-07-13

## 목적

이 문서는 QA 담당자가 시스템을 깊이 알지 못해도 Admin UI를 이용해 신규 Service 등록부터 runtime 호출 증거 확인까지 전체 흐름을 점검할 수 있도록 만든 체크리스트입니다.

테스트 목적은 단순 기능 성공 여부가 아니라, 현재 UI가 초기 기획처럼 개발자 편의성에 주안점을 두고 있는지 확인하고 개선 지점을 찾는 것입니다.

## 관련 기준 문서

- `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`
- `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`
- `docs/AdminUI_Handbook/v04/SETUP_GUIDE.md`
- `docs/adr/2026-07-08-authorization-first-admin-ui-onboarding.md`
- `docs/adr/2026-07-06-account-auth-service-rbac-to-fine-grained-authorization.md`
- `docs/adr/2026-07-09-admin-ui-c3-runtime-integration-and-api-key-scope.md`

## 테스트 범위

- C-1: `system_admin` 신규 Service 등록
- C-2: Service membership, 역할 부여, 역할 회수, 역할별 접근 확인
- C-3: API key 생성, runtime setup guidance 확인, Dify 또는 HTTP client runtime 호출, Runtime Logs와 Audit Logs 증거 확인
- 개발자 DX: 내부 ID 입력 최소화, 다음 액션 명확성, 오류 메시지 이해 가능성, 재시도 흐름
- 보안/권한: 서버 세션 기반 인증, Service scope 격리, raw secret/raw query 노출 방지, append-only audit evidence

## 테스트 계정

- [ ] `system_admin` 계정 준비
- [ ] `service_developer`로 부여할 일반 사용자 계정 준비
- [ ] `service_operator`로 부여할 일반 사용자 계정 준비
- [ ] `auditor`로 부여할 일반 사용자 계정 준비
- [ ] 아무 Service 권한이 없는 사용자 계정 준비
- [ ] 각 계정의 이메일, 사용자 ID, 표시 이름을 테스트 기록지에 적어둠

## 테스트 데이터

- [ ] 새 Service ID 준비: 예시 `qa-e2e-helpdesk`
- [ ] 새 Service 표시 이름 준비: 예시 `QA E2E Helpdesk`
- [ ] Release target Environment 준비: 예시 `dev`
- [ ] Intent 후보 2개 이상 준비
- [ ] 각 Intent별 approved example 후보 3개 이상 준비
- [ ] CSV test run용 정상/실패/모호 케이스 준비
- [ ] Dify 또는 HTTP client에서 사용할 runtime 호출 질의 준비

## 테스트 결과 기록 방식

각 항목은 다음 기준으로 기록합니다.

- 상태: `Pass`, `Fail`, `Blocked`, `N/A`
- 증거: 화면 캡처, trace ID, audit event ID, runtime log row, API 응답, 에러 메시지
- DX 메모: 사용자가 헷갈린 지점, 내부 용어가 과한 지점, 다음 행동이 불명확한 지점

## 0. 사전 준비

- [ ] QA 환경 URL에 접속할 수 있다.
- [ ] Admin UI 로그인 페이지가 열린다.
- [ ] Backend/API 서버가 정상 기동 중이다.
- [ ] 테스트 DB 또는 QA DB가 안전한 테스트 데이터로 준비되어 있다.
- [ ] 실제 운영 secret, 운영 API key, 운영 사용자 데이터가 테스트에 사용되지 않는다.
- [ ] 브라우저 개발자 도구 Network 탭에서 요청을 확인할 준비가 되어 있다.
- [ ] 테스트 중 `.env`, private key, token, password hash 같은 secret 파일을 열거나 캡처하지 않는다.

## 1. 로그인 및 기본 화면

### TC-001 로그인 성공

- [ ] `system_admin` 계정으로 로그인한다.
- [ ] 로그인 후 Dashboard 또는 기본 Admin 화면으로 이동한다.
- [ ] 새로고침 후에도 세션이 유지된다.
- [ ] 브라우저 Network 요청이 `irt_admin_session` cookie 기반으로 동작한다.
- [ ] 일반 Admin UI 요청에 `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`, `X-Service-Scope`, `Authorization: Bearer`가 포함되지 않는다.
- [ ] 검토: 초보 사용자가 현재 로그인 사용자와 권한을 화면에서 이해할 수 있다.

### TC-002 로그아웃

- [ ] 로그아웃 버튼을 누른다.
- [ ] 세션이 종료되고 로그인 페이지로 이동한다.
- [ ] 로그아웃 후 보호된 URL에 직접 접근하면 로그인 페이지 또는 인증 오류로 이동한다.
- [ ] 검토: 로그아웃 위치와 결과가 명확하다.

### TC-003 권한 없는 사용자 기본 진입

- [ ] Service 권한이 없는 사용자로 로그인한다.
- [ ] 접근 가능한 Service가 없다는 상태가 표시된다.
- [ ] 신규 Service 등록, API key 생성, Release 활성화 같은 민감 액션이 노출되지 않거나 비활성화된다.
- [ ] 검토: 권한이 없다는 이유와 다음 요청 대상이 이해 가능하다.

## 2. C-1 신규 Service 등록

### TC-004 Services 화면 진입

- [ ] `system_admin`으로 로그인한다.
- [ ] 좌측 메뉴 또는 네비게이션에서 `Services` 화면으로 이동한다.
- [ ] 현재 선택된 Service 정보 또는 Service 없음 상태가 표시된다.
- [ ] 검토: Service 등록이 전체 온보딩의 시작점임을 알 수 있다.

### TC-005 Service 생성 폼 기본값

- [ ] Service 생성 폼이 보인다.
- [ ] Max input tokens 기본값이 표시된다.
- [ ] 검토: Service ID, 표시 이름, 입력 토큰 한도를 한 화면에서 이해할 수 있다.

### TC-006 Service 생성 성공

- [ ] Service ID를 입력한다.
- [ ] Display name을 입력한다.
- [ ] Max input tokens를 입력한다.
- [ ] Service 등록 버튼을 누른다.
- [ ] 성공 메시지가 표시된다.
- [ ] 새 Service가 Service picker 또는 Accessible Services 목록에 나타난다.
- [ ] 새 Service가 현재 선택 Service로 자동 선택되거나 명확한 선택 액션이 제공된다.
- [ ] 검토: CLI나 DB 수동 작업 없이 UI만으로 Service 등록을 완료할 수 있다.

### TC-007 Service 생성 입력값 검증

- [ ] 빈 Service ID로 제출하면 오류가 표시된다.
- [ ] 허용되지 않는 문자 또는 대문자 Service ID를 입력하면 오류가 표시된다.
- [ ] 중복 Service ID로 생성하면 충돌 오류가 표시된다.
- [ ] Max input tokens에 허용 범위 밖 값을 입력하면 오류가 표시된다.
- [ ] 검토: 오류 메시지가 개발자가 바로 수정할 수 있을 만큼 구체적이다.

### TC-008 Service 생성 Audit 확인

- [ ] Audit Logs 화면으로 이동한다.
- [ ] `service.created` 또는 동등한 Service 생성 audit event가 존재한다.
- [ ] event에 actor, service_id, 생성 시각, before/after 상태가 표시된다.
- [ ] raw secret 또는 password/hash 정보가 audit 상태에 포함되지 않는다.
- [ ] 검토: 금융권 폐쇄망에서 증빙으로 사용할 수 있을 만큼 누가 무엇을 했는지 명확하다.

## 3. C-2 Service Membership 및 역할 부여

### TC-009 Membership 패널 진입

- [ ] Services 화면에서 방금 만든 Service를 선택한다.
- [ ] 선택된 Service의 membership 또는 role assignment 영역이 표시된다.
- [ ] 현재 멤버 목록이 로딩된다.
- [ ] 검토: 권한 부여가 Service 온보딩의 자연스러운 다음 단계로 보인다.

### TC-010 사용자 검색

- [ ] 부여 대상 개발자 이메일 또는 이름 일부를 입력한다.
- [ ] 검색 결과에 사용자 이메일, 표시 이름, 상태가 표시된다.
- [ ] 검색 결과에 password hash, session token, token hash가 표시되지 않는다.
- [ ] 검토: QA/운영자가 잘못된 사람을 고르지 않도록 식별 정보가 충분하다.

### TC-011 `service_developer` 역할 부여

- [ ] 대상 사용자를 선택한다.
- [ ] `service_developer` 역할을 선택한다.
- [ ] 역할 부여 버튼을 누른다.
- [ ] 성공 메시지가 표시된다.
- [ ] 멤버 목록에 대상 사용자의 `service_developer` 역할이 표시된다.
- [ ] 검토: 역할 부여 후 다음에 개발자가 무엇을 해야 하는지 알 수 있다.

### TC-012 추가 역할 부여

- [ ] 다른 사용자에게 `service_operator` 역할을 부여한다.
- [ ] 다른 사용자에게 `auditor` 역할을 부여한다.
- [ ] 필요하면 `service_owner` 역할도 부여 가능 여부를 확인한다.
- [ ] 각 역할이 멤버 목록에 구분되어 표시된다.
- [ ] 검토: 역할 이름만 보고 권한 범위를 추측해야 하는 불편이 없는지 확인한다.

### TC-013 중복 역할 부여

- [ ] 이미 가진 역할을 같은 사용자에게 다시 부여한다.
- [ ] 중복 성공 또는 이미 존재한다는 안내가 표시된다.
- [ ] 멤버 목록에 같은 역할이 중복 표시되지 않는다.
- [ ] Audit Logs에 중복 grant event가 불필요하게 추가되지 않는다.
- [ ] 검토: 실수로 버튼을 두 번 눌러도 데이터가 지저분해지지 않는다.

### TC-014 역할 회수

- [ ] 멤버 목록에서 특정 역할의 revoke 액션을 누른다.
- [ ] 확인 모달 또는 위험 작업 확인 UI가 표시된다.
- [ ] 확인 후 역할이 목록에서 제거된다.
- [ ] 대상 사용자의 `/me/services` 범위가 새로고침 후 변경된다.
- [ ] 검토: 위험 작업임을 충분히 알 수 있고, 되돌릴 방법이 명확하다.

### TC-015 Membership Audit 확인

- [ ] Audit Logs에서 `service_membership.role_granted` 이벤트를 확인한다.
- [ ] Audit Logs에서 `service_membership.role_revoked` 이벤트를 확인한다.
- [ ] event에 actor, target user, role, service_id가 표시된다.
- [ ] audit event가 수정/삭제 불가능한 read-only 화면으로 보인다.
- [ ] 검토: 권한 변경 이력 추적이 금융권 내부 감사 기준에 맞게 이해 가능하다.

## 4. 역할별 Service 접근 확인

### TC-016 개발자 계정 Service 접근

- [ ] `service_developer` 계정으로 로그인한다.
- [ ] Service picker에 부여받은 Service가 표시된다.
- [ ] 부여받지 않은 Service는 표시되지 않는다.
- [ ] 검토: 개발자가 본인 Service만 쉽게 찾을 수 있다.

### TC-017 개발자 계정 쓰기 권한

- [ ] Intent Catalog 화면에 접근한다.
- [ ] Intent 생성 또는 수정 액션이 가능하다.
- [ ] Example 추가 또는 approve 흐름이 가능한지 확인한다.
- [ ] API key 생성, Service membership 관리, 다른 Service 접근은 불가능하다.
- [ ] 검토: 개발자가 해야 할 작업은 가능하고, 보안상 위험한 작업은 막힌다.

### TC-018 운영자 계정 접근

- [ ] `service_operator` 계정으로 로그인한다.
- [ ] Runtime Metrics 또는 Runtime Logs 접근 가능 여부를 확인한다.
- [ ] Intent/Release/API key의 위험한 쓰기 액션이 제한되는지 확인한다.
- [ ] 검토: 운영자가 장애 확인에 필요한 정보에 접근할 수 있다.

### TC-019 Auditor 계정 접근

- [ ] `auditor` 계정으로 로그인한다.
- [ ] Runtime Logs와 Audit Logs 접근 가능 여부를 확인한다.
- [ ] 쓰기 액션, revoke, release activate 같은 변경 액션이 제한되는지 확인한다.
- [ ] 검토: 감사자가 증거는 볼 수 있지만 시스템 상태를 바꿀 수 없다.

## 5. Intent Catalog 작성

### TC-020 Intent Catalog 화면 진입

- [ ] `service_developer` 계정으로 로그인한다.
- [ ] 테스트 Service를 선택한다.
- [ ] Intent Catalog 화면으로 이동한다.
- [ ] 현재 Service scope가 화면 상단 또는 scope bar에 표시된다.
- [ ] 검토: 사용자가 어떤 Service를 편집 중인지 항상 알 수 있다.

### TC-021 Intent 생성

- [ ] 새 Intent ID를 입력한다.
- [ ] Intent 표시 이름 또는 설명을 입력한다.
- [ ] Route key 또는 route 관련 필드를 입력하거나 선택한다.
- [ ] Threshold preset 또는 필요한 분류 기준을 설정한다.
- [ ] 저장 후 Intent 목록에 새 Intent가 나타난다.
- [ ] 검토: ML/embedding 지식이 없어도 Intent를 작성할 수 있다.

### TC-022 Intent 입력값 검증

- [ ] 빈 Intent ID로 저장하면 오류가 표시된다.
- [ ] 중복 Intent ID로 저장하면 충돌 오류가 표시된다.
- [ ] 필수 route 정보가 없으면 저장이 제한된다.
- [ ] 검토: 오류 메시지가 내부 구현 용어보다 사용자가 수정할 필드를 중심으로 설명된다.

### TC-023 Intent 수정

- [ ] 기존 Intent를 선택한다.
- [ ] 설명, route, threshold 관련 정보를 수정한다.
- [ ] 저장 후 목록과 상세 정보에 변경 내용이 반영된다.
- [ ] 검토: 수정 후 재검증이나 다음 단계로 이동하는 흐름이 명확하다.

## 6. Example 추가 및 승인

### TC-024 Example 추가

- [ ] 특정 Intent에 사용자 질의 example을 추가한다.
- [ ] positive/negative 또는 expected intent 정보를 입력한다.
- [ ] 저장 후 example 목록에 추가된다.
- [ ] 검토: 개발자가 실제 사용자 표현을 쉽게 보강할 수 있다.

### TC-025 Example 승인

- [ ] pending example을 선택한다.
- [ ] approve 액션을 실행한다.
- [ ] 상태가 approved로 변경된다.
- [ ] 검토: 승인 전후 상태가 명확하고 실수 방지 장치가 있다.

### TC-026 Example 오류 처리

- [ ] 빈 질의 example 저장을 시도한다.
- [ ] 너무 긴 질의 example 저장을 시도한다.
- [ ] 중복 또는 부적절한 example 저장 시 오류 메시지를 확인한다.
- [ ] 검토: 오류가 개발자에게 학습 데이터 품질 개선 힌트를 준다.

## 7. Validation Bundle 및 CSV Test Run

### TC-027 Validation Bundle 생성

- [ ] Test Runs 화면으로 이동한다.
- [ ] 현재 Service scope가 유지되는지 확인한다.
- [ ] 정책 버전과 catalog version 후보를 선택한다.
- [ ] 후보가 내부 ID 수동 입력이 아니라 선택 목록으로 제공되는지 확인한다.
- [ ] 검토: 개발자가 내부 DB ID를 알아야 하는 불편이 없다.

### TC-028 CSV Test Run 생성

- [ ] CSV 입력 또는 업로드 영역에 테스트 케이스를 입력한다.
- [ ] 정상 케이스, 실패 예상 케이스, 모호 케이스를 포함한다.
- [ ] Test Run을 생성한다.
- [ ] 생성된 test_run_id 또는 결과 페이지로 이동한다.
- [ ] 검토: QA가 CSV 포맷을 쉽게 이해할 수 있다.

### TC-029 Test Run 결과 확인

- [ ] 전체 pass/fail 요약이 표시된다.
- [ ] 실패한 row가 원인과 함께 표시된다.
- [ ] expected와 actual 결과를 비교할 수 있다.
- [ ] trace ID 또는 row ID가 증거로 기록 가능하다.
- [ ] 검토: 실패 원인이 example 보강, Intent 수정, route 수정 중 어디에 가까운지 알 수 있다.

### TC-030 실패 케이스 개선 루프

- [ ] 실패 row를 기반으로 Intent 또는 Example 화면으로 돌아간다.
- [ ] 데이터를 보강한다.
- [ ] Test Run을 다시 실행한다.
- [ ] 이전 결과와 개선 결과를 비교한다.
- [ ] 검토: 개발자가 시행착오를 빠르게 반복할 수 있다.

## 8. Release 생성 및 활성화

### TC-031 Release 후보 선택

- [ ] Releases 화면으로 이동한다.
- [ ] 현재 Service scope가 유지된다.
- [ ] test run, policy version, catalog version 후보가 선택 목록으로 표시된다.
- [ ] 검토: release 생성에 필요한 후보를 수동 ID 입력 없이 고를 수 있다.

### TC-032 Release 생성

- [ ] 검증 완료된 후보를 선택한다.
- [ ] Release version 또는 표시 정보를 입력한다.
- [ ] Release 생성 시 passed test candidate에서 Environment를 지정한다.
- [ ] Release를 생성한다.
- [ ] 생성된 Release가 목록에 표시된다.
- [ ] 검토: Release가 어떤 검증 결과를 기반으로 만들어졌는지 알 수 있다.

### TC-033 Release 활성화

- [ ] Release activate 액션을 누른다.
- [ ] 확인 모달 또는 위험 작업 안내가 표시된다.
- [ ] 활성화 후 Release 상태가 active로 변경된다.
- [ ] 기존 active Release가 있다면 상태 변화가 명확히 표시된다.
- [ ] 검토: 운영 영향이 있는 작업이라는 점이 충분히 드러난다.

### TC-034 Release rollback

- [ ] rollback 가능한 이전 Release가 있는지 확인한다.
- [ ] rollback 액션을 실행한다.
- [ ] 확인 모달이 표시된다.
- [ ] rollback 후 active Release가 기대한 버전으로 바뀐다.
- [ ] 검토: 장애 대응 시 사용자가 안전하게 이전 버전으로 되돌릴 수 있다.

### TC-035 Release Audit 확인

- [ ] Audit Logs에서 release 생성 event를 확인한다.
- [ ] Audit Logs에서 release activate 또는 rollback event를 확인한다.
- [ ] actor, service_id, release_version이 표시된다.
- [ ] 검토: 배포 변경 증거가 추적 가능하다.

## 9. C-3 API Key 및 Runtime Setup Guidance

### TC-036 API Keys 화면 진입

- [ ] `system_admin` 계정으로 로그인한다.
- [ ] 테스트 Service를 선택한다.
- [ ] API Keys 화면으로 이동한다.
- [ ] key inventory가 selected Service 기준으로 표시된다.
- [ ] 검토: Service scope와 API key scope가 같은 화면 흐름에서 이해된다.

### TC-037 API Key 후보 선택

- [ ] Environment를 선택한다.
- [ ] App ID를 입력한다. 예시 `dify-platform`
- [ ] allowed intents를 후보 목록에서 선택한다.
- [ ] allowed route keys를 후보 목록에서 선택한다.
- [ ] 수동으로 알 수 없는 Intent ID 또는 route key를 입력할 수 없는지 확인한다.
- [ ] 검토: 잘못된 scope를 만드는 실수를 UI가 줄여준다.

### TC-038 API Key 생성

- [ ] API key 생성 버튼을 누른다.
- [ ] 확인이 필요한 경우 확인 모달을 완료한다.
- [ ] key_id, fingerprint, app_id, environment, scope 정보가 표시된다.
- [ ] raw API key secret이 생성 직후 한 번만 표시된다.
- [ ] 검토: secret 표시가 복사하기 쉽지만, 장기 노출되지 않는다는 안내가 명확하다.

### TC-039 API Key Secret 안전성

- [ ] 페이지를 새로고침한다.
- [ ] raw API key secret이 다시 표시되지 않는다.
- [ ] inventory에는 key_id와 fingerprint만 표시된다.
- [ ] revoke 응답 또는 key 목록에 `api_key` 원문이 표시되지 않는다.
- [ ] Audit Logs에 raw API key secret이 남지 않는다.
- [ ] 검토: 운영자가 secret을 재조회할 수 없다는 보안 제약을 이해할 수 있다.

- [ ] Authorization의 `Secret 보기/복사`는 `POST /admin/v1/services/{service_id}/api-keys/{key_id}:reveal`을 호출하고 `Bearer irt_<decrypted-secret>`만 클립보드에 복사한다.
- [ ] Audit Logs에 `api_key.secret_revealed` event가 남고 audit state에는 raw `api_key`가 포함되지 않는다.

### TC-040 Runtime Setup Guidance 확인

- [ ] Runtime setup guidance 영역을 연다.
- [ ] `/v1/intent-route` endpoint가 표시된다.
- [ ] header template에 `Authorization: Bearer {{intent_routing_api_key}}`, `X-Key-Id`, `X-App-Id`, `X-Service-Id`, `X-Request-Id`가 표시된다.
- [ ] body template에 `query`와 `user_context.workflow_run_id`가 표시된다.
- [ ] timeout, retry, fallback/handoff 안내가 표시된다.
- [ ] guidance에는 raw API key secret이 재노출되지 않는다.
- [ ] 검토: Dify 또는 HTTP client 담당자가 별도 문서 없이 설정을 따라 할 수 있다.

### TC-041 API Key Revoke

- [ ] 생성한 API key의 revoke 액션을 누른다.
- [ ] 확인 모달이 표시된다.
- [ ] revoke 후 status가 revoked로 변경된다.
- [ ] revoked key로 runtime 호출 시 인증 실패가 발생한다.
- [ ] Audit Logs에 `api_key.revoked` event가 남는다.
- [ ] 검토: key 폐기 절차가 실수 방지와 증거 기록을 모두 만족한다.

## 10. Dify 또는 HTTP Client Runtime Call

### TC-042 정상 runtime 호출

- [ ] Dify 또는 HTTP client에 runtime setup guidance를 기준으로 endpoint와 headers를 설정한다.
- [ ] raw API key secret은 Dify secret 변수 또는 안전한 client secret 저장소에만 입력한다.
- [ ] 정상 query를 보낸다.
- [ ] runtime 응답에 decision, route_key, trace_id, release_version이 포함되는지 확인한다.
- [ ] 검토: client 담당자가 Admin UI guidance만 보고 첫 호출을 성공시킬 수 있다.

### TC-043 잘못된 Service scope 호출

- [ ] 같은 API key로 잘못된 `X-Service-Id`를 사용해 호출한다.
- [ ] 인증 또는 scope 오류가 발생한다.
- [ ] 다른 Service의 정보가 응답에 노출되지 않는다.
- [ ] 검토: Service 간 격리가 깨지지 않는다.

### TC-044 잘못된 App ID 호출

- [ ] 같은 API key로 잘못된 `X-App-Id`를 사용해 호출한다.
- [ ] 인증 또는 scope 오류가 발생한다.
- [ ] 검토: app별 key scope가 적용된다.

### TC-045 허용되지 않은 Intent/Route 호출

- [ ] key scope 밖의 Intent 또는 route로 분류될 수 있는 query를 보낸다.
- [ ] route 실행이 차단되거나 `unauthorized` decision이 반환된다.
- [ ] 검토: key scope가 runtime에서도 강제된다.

### TC-046 장애/Timeout 처리

- [ ] 잘못된 endpoint 또는 timeout 조건을 시뮬레이션한다.
- [ ] Dify/client 쪽 fallback 또는 human handoff 분기가 동작한다.
- [ ] Runtime Logs 또는 client logs에 추적 가능한 request_id가 남는다.
- [ ] 검토: 운영 장애 상황에서 디버깅 단서가 충분하다.

## 11. Runtime Logs 확인

### TC-047 Runtime Logs 목록

- [ ] Runtime Logs 화면으로 이동한다.
- [ ] 테스트 Service scope가 유지된다.
- [ ] 방금 호출한 trace_id 또는 request_id가 목록에 표시된다.
- [ ] `query_masked`가 표시되고 raw query 원문은 기본 노출되지 않는다.
- [ ] 검토: 개인정보나 민감 질의가 기본 화면에 노출되지 않는다.

### TC-048 Runtime Log 상세

- [ ] 특정 runtime log row를 연다.
- [ ] decision, route_key, release_version, latency, error 정보가 표시된다.
- [ ] raw query 원문이 상세에도 기본 노출되지 않는다.
- [ ] raw query 조회 기능이 있다면 승인 workflow 또는 disabled 안내가 표시된다.
- [ ] 검토: 문제 원인을 찾는 데 필요한 정보와 민감정보 보호가 균형을 이룬다.

### TC-049 역할별 Runtime Logs 접근

- [ ] `service_operator` 계정으로 Runtime Logs에 접근한다.
- [ ] `auditor` 계정으로 Runtime Logs에 접근한다.
- [ ] `service_developer` 계정의 접근 가능 여부가 정책대로 제한되는지 확인한다.
- [ ] 권한 없는 사용자는 다른 Service log를 볼 수 없다.
- [ ] 검토: 운영/감사 역할은 필요한 증거를 볼 수 있고, 불필요한 노출은 막힌다.

## 12. Audit Logs 확인

### TC-050 Audit Logs 목록

- [ ] Audit Logs 화면으로 이동한다.
- [ ] Service 생성, 역할 부여, 역할 회수, Release 변경, API key 생성, API key revoke 이벤트가 표시된다.
- [ ] actor, event_type, service_id, target_type, target_id, created_at이 표시된다.
- [ ] 검토: 감사자가 사건 흐름을 시간순으로 재구성할 수 있다.

### TC-051 Audit Log 상세

- [ ] 특정 audit event 상세를 연다.
- [ ] before_state와 after_state가 필요한 범위로 표시된다.
- [ ] password, token, raw API key, raw query 같은 secret이 표시되지 않는다.
- [ ] 검토: 증거는 충분하지만 secret은 남지 않는다.

### TC-052 Audit Logs 불변성

- [ ] Audit Logs 화면에 수정 버튼이 없는지 확인한다.
- [ ] Audit Logs 화면에 삭제 버튼이 없는지 확인한다.
- [ ] Export 기능이 있다면 masking 또는 권한 안내가 명확한지 확인한다.
- [ ] 검토: append-only evidence 원칙이 UI에서도 드러난다.

## 13. Permission Management 권한 감사

### TC-057 Permission Management Admin 계정 현황

- [ ] `system_admin`으로 `/permission-management`에 진입한다.
- [ ] Admin 계정 탭에 admin user_id, email, display_name, status, 연결된 조직 사용자, global_roles가 보인다.
- [ ] `users` row만 있는 조직 사용자는 Admin Console 접근 가능자로 표시되지 않는다.
- [ ] 검토: 운영자가 누가 Admin Console 접근 권한을 갖는지 한 화면에서 이해할 수 있다.

### TC-058 Permission Management 권한 변경 이력

- [ ] `admin_user.global_role_granted` 이벤트가 권한 변경 이력 탭에 표시된다.
- [ ] `service_membership.role_granted` 이벤트가 권한 변경 이력 탭에 표시된다.
- [ ] password hash, session token, API secret, raw before/after state가 표시되지 않는다.
- [ ] 검토: 감사 담당자가 누가 언제 어떤 권한을 바꿨는지 확인할 수 있다.

## 14. 보안 및 권한 Negative Test

### TC-053 비로그인 접근

- [ ] 로그아웃 상태에서 `/services`, `/intents`, `/api-keys`, `/runtime-logs`, `/audit-logs`에 직접 접근한다.
- [ ] 로그인 페이지 또는 401 처리로 이동한다.
- [ ] 검토: URL 직접 접근으로 데이터가 노출되지 않는다.

### TC-054 Trusted Header 우회 시도

- [ ] 브라우저 또는 HTTP client에서 `X-Actor-Roles`, `X-Service-Scope` 같은 trusted header만 넣고 Admin API를 호출한다.
- [ ] 유효한 session cookie가 없으면 401이 발생한다.
- [ ] 유효한 session cookie가 있으면 session actor 기준으로 권한이 판단된다.
- [ ] 검토: 브라우저에서 헤더 조작으로 권한 상승이 불가능하다.

### TC-055 타 Service 직접 URL/API 접근

- [ ] 권한 없는 Service ID를 URL 또는 API path에 직접 입력한다.
- [ ] 403 또는 404가 발생한다.
- [ ] 다른 Service의 이름, 멤버, key, runtime log가 노출되지 않는다.
- [ ] 검토: 다중 Service 환경에서 데이터 경계가 유지된다.

### TC-056 Service membership 권한 경계

- [ ] 선택한 Service의 `service_owner` 계정으로 user lookup, membership list, grant/revoke를 시도한다.
- [ ] 같은 Service 범위에서는 성공하고, 권한 없는 다른 Service에서는 403 또는 404가 발생한다.
- [ ] `service_developer`, `service_operator`, `auditor` 계정으로 membership grant/revoke를 시도한다.
- [ ] `service_developer`, `service_operator`, `auditor`는 차단되고, 차단 메시지는 Service owner scope가 필요하다고 설명한다.
- [ ] 검토: `system_admin`과 인가된 `service_owner`만 membership을 관리할 수 있다.

### TC-059 Non-system-admin API Key 관리 시도

- [ ] 선택한 Service의 `service_owner` 계정으로 API key 생성 또는 revoke를 시도한다.
- [ ] 같은 Service 범위에서는 성공하고, 권한 없는 다른 Service에서는 403 또는 404가 발생한다.
- [ ] `service_developer`, `service_operator`, `auditor` 계정으로 API key 생성 또는 revoke를 시도한다.
- [ ] `service_developer`, `service_operator`, `auditor`는 차단된다.
- [ ] 검토: runtime key lifecycle은 `system_admin`과 인가된 `service_owner`로 통제된다.

### TC-060 Secret 노출 검색

- [ ] 주요 화면에서 raw API key secret이 재노출되지 않는지 확인한다.
- [ ] Runtime Logs에서 raw query가 기본 노출되지 않는지 확인한다.
- [ ] Audit Logs에서 password/token/api_key 원문이 없는지 확인한다.
- [ ] Network 응답에서도 불필요한 secret 필드가 없는지 확인한다.
- [ ] 검토: 화면과 API 응답 모두에서 secret 최소 노출 원칙이 지켜진다.

## 15. 개발자 DX 평가 체크리스트

### 온보딩 흐름

- [ ] 신규 Service 등록 후 다음 단계가 명확하다.
- [ ] 역할 부여 후 개발자가 어떤 메뉴로 가야 하는지 알 수 있다.
- [ ] Intent 작성, example 추가, validation, release, API key 생성이 하나의 흐름처럼 이어진다.
- [ ] 중간에 CLI, DB 직접 조작, 내부 ID 조회가 필요하지 않다.

### 화면 이해도

- [ ] 현재 선택 Service가 모든 주요 화면에서 보인다.
- [ ] Environment, status, role이 일관된 위치와 표현으로 표시된다.
- [ ] 버튼 이름이 사용자의 실제 행동을 설명한다.
- [ ] 내부 구현 용어가 과하게 노출되지 않는다.

### 오류와 복구

- [ ] 입력 오류는 어떤 필드를 어떻게 고쳐야 하는지 알려준다.
- [ ] 권한 오류는 필요한 역할과 요청 대상을 알려준다.
- [ ] Test Run 실패는 example/Intent 개선으로 이어질 단서를 준다.
- [ ] Runtime 실패는 trace_id/request_id로 추적 가능하다.

### 보안 친화성

- [ ] 위험 작업에는 확인 단계가 있다.
- [ ] raw API key secret은 한 번만 표시된다.
- [ ] raw query는 기본 masking된다.
- [ ] audit evidence가 사용자의 추가 수작업 없이 남는다.

### 반복 작업 편의성

- [ ] CSV Test Run 재실행이 쉽다.
- [ ] 실패 row를 기반으로 수정 화면으로 돌아가기 쉽다.
- [ ] Release 후보 선택이 명확하다.
- [ ] Runtime setup guidance를 복사해 client 설정에 바로 사용할 수 있다.

## 16. 최종 완료 판정

아래 항목을 모두 만족하면 UI E2E DX 리뷰 시나리오를 완료로 판정한다.

- [ ] C-1 신규 Service 등록을 UI만으로 완료했다.
- [ ] C-2 Service 역할 부여와 회수를 UI/API로 확인했다.
- [ ] 역할 부여 후 개발자 계정이 해당 Service를 볼 수 있음을 확인했다.
- [ ] 권한 없는 사용자가 다른 Service에 접근할 수 없음을 확인했다.
- [ ] Intent, Example, Validation Bundle, CSV Test Run 흐름을 완료했다.
- [ ] 실패 케이스를 개선하고 재검증하는 루프를 1회 이상 수행했다.
- [ ] Release 생성과 활성화를 완료했다.
- [ ] Service-scoped API key를 생성했다.
- [ ] Runtime setup guidance를 기준으로 Dify 또는 HTTP client 호출을 수행했다.
- [ ] Runtime Logs에서 masked query와 trace evidence를 확인했다.
- [ ] Audit Logs에서 주요 변경 event를 확인했다.
- [ ] raw API key, password, token, raw query가 불필요하게 노출되지 않음을 확인했다.
- [ ] QA 관점의 DX 개선 메모를 3개 이상 기록했다.

## QA 기록 템플릿

```markdown
## 테스트 기록

- 테스트 일시:
- QA 담당자:
- 테스트 환경 URL:
- Backend/API 버전 또는 commit:
- Frontend 버전 또는 commit:
- 사용 계정:
- 생성 Service ID:
- 생성 API key ID:
- 대표 trace_id:

| TC | 상태 | 증거 | DX/보안 메모 |
| --- | --- | --- | --- |
| TC-001 |  |  |  |
| TC-002 |  |  |  |
| TC-003 |  |  |  |

## 최종 판정

- [ ] 완료
- [ ] 조건부 완료
- [ ] 실패
- [ ] 차단

조건부 완료 또는 실패 사유:

후속 개선 과제:
```
