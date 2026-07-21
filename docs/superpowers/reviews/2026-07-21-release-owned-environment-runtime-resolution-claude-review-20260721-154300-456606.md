# Implementation Plan Review

Reviewed plan: `docs/superpowers/plans/2026-07-21-release-owned-environment-runtime-resolution.md`
Reviewed ADR: `docs/adr/2026-07-21-release-owned-environment-runtime-resolution.md`
Repository state at review time: branch `main`, working tree dirty (uncommitted `0011_api_key_optional_expiry.py`, in-flight `pages/ApiKeys/index.tsx` rewrite, catalog diff work).

---

## 1. Review Summary

### Overall Assessment

**Major revision should be considered**

### Summary

계획의 아키텍처 방향(Service = 논리적 인가 단위, environment는 release/API key 소유, runtime은 검증된 key metadata로 environment 해석, 운영 allowlist로 프로세스가 서빙할 환경 제한)은 사용자 요구사항과 ADR에 정확히 부합하며, 저장소 구조와도 잘 맞습니다. `AuthContext.environment` 추가, `_load_active_release(..., environment=auth.environment)` 전환, release 후보 environment 분리, RBAC 분화(owner=write, developer=read) 같은 핵심 판단은 실제 코드 위치와 일치합니다(§2 참고).

가장 중요한 위험은 **설계가 아니라 변경 범위 파악(blast radius)** 에 있습니다. `services.environment` / `services.default_threshold_preset` 제거는 계획의 File Map이 다루는 파일보다 훨씬 넓게 퍼져 있습니다. 확인된 것만:

- Admin API에 `service.environment`를 참조하는 지점이 **6곳** 있고, 그중 `list_intent_route_candidates`(admin.py:4947)는 계획에 전혀 언급되지 않았습니다. 그 상태로 모델 필드를 지우면 `AttributeError` → 500이 됩니다.
- 프론트엔드 `components/ServiceScopeBar.tsx:39-40`이 `selectedService.environment`를 렌더링합니다. File Map에 없고, `tsc --noEmit`(Task 11 Step 3)이 실패합니다.
- Service 생성 payload/모델에 `environment`/`default_threshold_preset`를 넣는 테스트가 **16개 이상 파일**, 그리고 `scripts/seed_pilot.py`에 존재합니다. 계획은 그중 2개 파일만 수정 대상으로 잡았습니다. `ServiceCreateRequest`가 `extra="forbid"`이므로 나머지는 422 또는 `TypeError`로 깨집니다.
- 기존 테스트 `tests/integration/test_admin_service_rbac_flow.py:173`은 `service_owner`/`service_developer`가 `/audit-logs`에 **200**을 받는다고 단언합니다. 계획 Task 8의 새 테스트는 같은 대상에 **403**을 단언합니다. 두 단언은 동시에 통과할 수 없습니다.

두 번째 위험은 **`dev`/`qa`/`prod` 전용 allowlist와 기존 `pilot` 환경 경로의 충돌**입니다. `.env.closed-network.example`은 `INTENT_ROUTING_ENVIRONMENT=pilot`이고(`tests/unit/test_closed_network_packaging_contract.py:42`가 단언), `docs/ops/pilot-e2e-smoke.md`는 `--environment ${INTENT_ROUTING_ENVIRONMENT}`를 seed/release/API key 생성 스크립트에 그대로 전달합니다. 계획대로면 이 경로는 422로 막힙니다.

세 번째는 **계획에 포함된 테스트 코드 스니펫이 실제 헬퍼와 맞지 않는다는 점**입니다. `_client_with_service_owner`, `_seed_gate_passed_test_run`, `_client_with_service_role`, `_seed_two_services_with_owner_and_target`, `_seed_successful_release`는 저장소에 존재하지 않고, 존재하는 `_seed_active_release(db_session, service_id)`는 `environment` 인자를 받지 않으며, `_record_for(...)`는 `service_id="svc-a"`를 하드코딩합니다(계획의 runtime 테스트는 동적 service_id 헤더를 보내므로 scope 검사에서 403이 납니다).

**Coding Agent가 우선 재확인해야 할 것**은 다음 순서입니다: (1) F-1~F-4 (범위 누락으로 인한 확실한 파손), (2) F-5 (pilot 환경 충돌), (3) F-6 (audit 로그 RBAC 기존 테스트 모순), (4) A-1 (테스트 헬퍼 전제), (5) F-7~F-9 (allowlist 실패 모드, 전역 API key 엔드포인트 우회, 에러 경로 로그 environment).

이 문서는 승인/반려가 아니라 독립 검토 결과이며, 각 항목은 저장소에서 직접 확인 후 채택 여부를 판단해야 합니다.

---

## 2. Validated Parts of the Plan

### V-1. Runtime environment를 `AuthContext`로 옮기는 판단

* Plan section: Task 2 Step 4-5
* Assessment: 현재 코드와 정확히 일치하며 근본 원인을 해결합니다.
* Evidence: `src/intent_routing/api/dependencies.py:147-153`이 `record.environment != environment`(프로세스 env)로 401을 발생시키고, `src/intent_routing/api/runtime.py:93,103-107`이 `Depends(get_runtime_environment)` 값을 release 조회에 사용합니다. ADR의 "Postman 호출이 실패한 원인"과 정확히 일치합니다.
* Why this appears appropriate: `ApiKeyRecord.environment`는 이미 `_record_from_model`(dependencies.py:77-90)에서 채워지므로, 추가 조회 없이 environment를 얻을 수 있습니다. 헤더 기반 대안보다 위조 위험이 없습니다.

### V-2. Release가 test run을 환경별로 재사용할 수 있게 하는 판단

* Plan section: Task 4 Step 1-3
* Assessment: 현재 차단 요인이 `admin.py:6019-6020`의 service-environment 동등 비교 하나뿐임이 확인됩니다.
* Evidence: `src/intent_routing/versions/releases.py:49-95`(`validate_release_inputs`)에는 "한 test run은 릴리스 하나" 같은 전역 제약이 없습니다. `alembic/versions/0001_initial_intent_routing.py:254-286`의 `releases` 테이블에도 `test_run_id` unique 제약이 없습니다. `release_version_id`(releases.py:38-46)는 `service_id + 날짜 + 순번`이라 같은 날 3개 환경 릴리스가 서로 다른 버전을 받습니다.
* Why this appears appropriate: 계획의 "3개 환경 릴리스가 모두 201, 버전 3개가 서로 다름" 단언은 현재 구현으로 충족 가능합니다.

### V-3. `list_release_candidates`의 기존 릴리스 조회가 이미 환경 범위임

* Plan section: Task 4 Step 3
* Assessment: 계획의 목표는 타당하지만, 구현은 계획이 제안한 것보다 더 작아도 됩니다(F-12 참고).
* Evidence: `admin.py:6093-6096`의 `existing_releases`는 이미 `repository.list_releases(service_id, target_environment)` 결과로 만들어지고, `repositories.py:2318-2322`가 environment로 필터링합니다.
* Why this appears appropriate: 실제로 제거해야 할 것은 `environment_matches_service` 조건/사유(admin.py:6092, 6105-6106, 6112)뿐입니다.

### V-4. Alembic 리비전 체인

* Plan section: Task 1 Step 3
* Assessment: `down_revision = "0011_api_key_optional_expiry"`는 현재 head와 일치합니다.
* Evidence: `alembic/versions/0011_api_key_optional_expiry.py:12-13` (`revision="0011_api_key_optional_expiry"`, `down_revision="0010_test_run_vector_metadata"`). 다만 이 파일은 아직 커밋되지 않은 untracked 파일입니다(A-4 참고).
* Why this appears appropriate: 파일명/리비전 ID 명명 규칙(`NNNN_snake_case`)도 기존 관례와 일치합니다.

### V-5. `service_owner`에게 멤버십 관리를 위임하는 백엔드 설계

* Plan section: Task 6 Step 2
* Assessment: 기존 헬퍼 패턴과 일관됩니다.
* Evidence: `admin.py:1566-1571`의 `_require_publish_decision_access`가 이미 `system_admin` bypass + `has_service_role(service_id, "service_owner")` 형태를 사용합니다. 계획이 제안한 `_require_service_membership_management_access`는 동일 패턴입니다.
* Why this appears appropriate: 새 추상화를 도입하지 않고 기존 관례를 재사용합니다.

### V-6. Admin UI가 세션 쿠키 + Umi `request`를 유지한다는 제약

* Plan section: Global Constraints
* Assessment: 프로젝트 문서 제약과 일치합니다.
* Evidence: `tests/unit/test_admin_runtime_setup_contract_docs.py:74-79`가 "Normal browser Admin UI requests use `irt_admin_session`", "must not send `X-Admin-Token`" 등을 계약 문서에서 단언합니다.
* Why this appears appropriate: 이 제약을 명시적으로 재확인한 것은 좋은 판단이며, 재검토가 불필요합니다.

### V-7. Admin Console 뷰포트 범위

* Plan section: 프론트엔드 Task 7/9 전반
* Assessment: `AGENTS.md`의 "모바일 UX를 설계/구현/검증하지 말 것" 지침을 위반하는 항목이 없습니다.
* Evidence: 계획의 UI 변경은 `Select` 추가, 컬럼 추가, 메뉴 필터링에 한정됩니다.
* Why this appears appropriate: 별도 재검토가 불필요합니다.

---

## 3. Review Findings

### F-1. `services.environment` 제거의 영향 범위가 File Map보다 훨씬 넓음

* Severity: **Blocker**
* Category: 계획의 완전성 / 회귀 위험
* Plan section: Task 1 (File Map, Step 4-6), Task 11 Step 1
* Evidence type: Confirmed fact
* Current plan: `models.py`에서 필드를 제거하고, `tests/integration/test_admin_runtime_setup_api.py`와 `tests/integration/test_release_flow.py` 두 파일의 Service 생성 payload만 수정합니다.
* Review finding: Service 생성 payload 또는 `models.Service(...)` 생성 시 `environment` / `default_threshold_preset`를 넘기는 지점이 최소 16개 테스트 파일과 1개 운영 스크립트에 존재합니다. `ServiceCreateRequest`는 `model_config = ConfigDict(extra="forbid")`(admin.py:132 부근, 계획 스니펫도 유지)이므로 API 경로는 **422**, SQLAlchemy 직접 생성 경로는 **TypeError**로 실패합니다.
* Evidence:
  - `grep -rc "default_threshold_preset" tests/*/*.py` → `test_admin_catalog_api.py`, `test_admin_api_key_inventory_flow.py`, `test_admin_workflow_candidates_api.py`, `test_admin_service_rbac_flow.py`, `test_catalog_version_management_api.py`, `test_ops_metrics_api.py`, `test_log_retention_flow.py`(3), `test_raw_text_rewrap_flow.py`, `test_permission_management_api.py`(5), `test_test_run_diagnostics_api.py`(4), `test_release_flow.py`(4), `test_runtime_api.py`, `test_trace_audit_logs.py`(2), `tests/unit/test_account_auth_schema_contract.py`, `tests/unit/test_permission_management_repository.py`(3) 등.
  - `scripts/seed_pilot.py:80-88`이 `POST /admin/v1/services`에 `"environment"`와 `"default_threshold_preset"`를 보냅니다. 이를 검증하는 테스트: `tests/unit/test_seed_pilot.py:255,297`, `tests/integration/test_pilot_seed_flow.py`, `tests/integration/test_pilot_rehearsal_flow.py`, `tests/integration/test_dify_smoke_flow.py` 등.
* Potential impact: Task 11 Step 1이 실행하는 6개 파일은 통과하더라도 전체 `pytest` 실행은 광범위하게 실패합니다. CI 기준으로는 구현이 "완료"로 판정될 수 없습니다.
* What the Coding Agent should verify: 실제 파손 파일 수와, `models.Service` 직접 생성 경로 vs API payload 경로의 비율.
* How to verify:
  ```bash
  grep -rln "default_threshold_preset" tests scripts src
  grep -rn "models.Service(" tests | head -40
  uv run pytest -q   # 변경 전 baseline과 변경 후 비교
  ```
* Decision criteria: 파손 파일이 5개를 넘고 그중 pilot/ops 스크립트 경로가 포함된다면 File Map과 Task 분해를 갱신하는 것이 타당합니다. 반대로 대부분이 공용 헬퍼 1~2개를 경유한다면(예: 각 파일의 `_create_service`) 헬퍼만 고치는 작은 Task 하나로 충분할 수 있습니다.
* Possible response:
  * Add an additional step (Task 1에 "Service 생성 fixture 전수 정리" 단계 추가)
  * Perform further investigation before deciding

### F-2. `list_intent_route_candidates`의 `service.environment` fallback이 계획에 없음

* Severity: **Blocker**
* Category: 요구사항 정합성 / 런타임 오류
* Plan section: Task 5 Step 3 (`_runtime_setup_environment`만 다룸)
* Evidence type: Confirmed fact
* Current plan: `_runtime_setup_environment(service, environment)`를 `_runtime_setup_environment(environment)`로 바꾸는 것만 명시합니다.
* Review finding: `admin.py:4947`은 `repository.get_active_release(service_id, environment or service.environment)`로 별도 경로를 갖고 있습니다. `Service.environment`가 삭제되면 이 줄은 `AttributeError`를 던집니다. 이 엔드포인트는 계획 Task 5 Step 4가 API Keys UI에서 `listIntentRouteCandidates(serviceId, { source: 'active_release', environment })`로 **직접 호출하도록 지정한 바로 그 엔드포인트**입니다.
* Evidence: `src/intent_routing/api/admin.py:4946-4947`. 계획 Task 5 Step 4의 UI 스니펫이 같은 엔드포인트를 호출합니다.
* Potential impact: API Keys 화면의 scope 후보 로딩이 500. 게다가 `environment`가 UI에서 항상 전달되면 우연히 동작하는 것처럼 보여, environment 미지정 호출 경로(다른 화면/스크립트)에서만 터지는 잠복 버그가 됩니다.
* What the Coding Agent should verify: `service.environment`를 참조하는 admin.py 전체 지점과, 각 지점의 새 기본값 정책(에러 vs 명시적 기본값).
* How to verify:
  ```bash
  grep -n "service\.environment" src/intent_routing/api/admin.py
  # 확인된 지점: 1756, 1774, 2059-2060, 4947, 6019, 6091-6092
  ```
* Decision criteria: `environment`를 필수 쿼리 파라미터로 승격할지, 아니면 명시적 기본값(`"dev"`)을 쓸지는 UI 호출 규약에 달려 있습니다. 계획이 이미 UI에서 항상 environment를 보내도록 했다면 "필수화 + 422"가 더 안전하고 회귀를 조기에 드러냅니다.
* Possible response:
  * Modify the current plan (Task 5에 이 엔드포인트를 명시적으로 포함)

### F-3. 프론트엔드 `ServiceScopeBar.tsx`가 File Map에 없음 — 타입 체크 실패 확실

* Severity: **Blocker**
* Category: 계획의 완전성 / 빌드 파손
* Plan section: File Map, Task 9, Task 11 Step 3
* Evidence type: Confirmed fact
* Current plan: `AccessibleService` 타입에서 `environment`를 제거하지만, 소비처로는 Services/Releases/ApiKeys 페이지만 나열합니다.
* Review finding: `frontend/intent-routing-console/src/components/ServiceScopeBar.tsx:39-40`이 `selectedService?.environment`와 `selectedService.environment`를 사용합니다. 이 컴포넌트는 모든 화면 상단의 공용 스코프 바입니다. 타입에서 필드를 지우면 `tsc --noEmit`(Task 11 Step 3)이 여기서 실패합니다.
* Evidence: `grep -rn "\.environment" frontend/intent-routing-console/src` 결과에서 `components/ServiceScopeBar.tsx:39,40`이 계획 미포함 파일로 나타납니다.
* Potential impact: Task 11 Step 3에서야 발견되어, 앞선 Task들의 "PASS" 판정이 실제로는 불완전했음이 드러납니다. 또한 스코프 바에서 environment 뱃지가 사라지는 UX 변화를 사용자와 합의한 바가 없습니다.
* What the Coding Agent should verify: 스코프 바에서 environment 뱃지를 (a) 제거할지, (b) "현재 선택된 release environment"로 의미를 바꿔 유지할지.
* How to verify:
  ```bash
  grep -rn "environment" frontend/intent-routing-console/src/components/ServiceScopeBar.tsx
  cd frontend/intent-routing-console && ./node_modules/.bin/tsc --noEmit
  ```
* Decision criteria: Service가 더 이상 environment를 소유하지 않으므로 (a) 단순 제거가 모델과 일관됩니다. 다만 운영자가 "지금 어떤 환경을 보고 있는지"를 상단에서 확인하던 UX를 잃습니다 — 이 정보는 이제 Releases/ApiKeys 페이지의 로컬 셀렉터로 이동하므로, 전역 바에서 제거하는 편이 오해를 줄입니다.
* Possible response:
  * Modify the current plan (File Map에 `ServiceScopeBar.tsx` 추가)

### F-4. `dev/qa/prod` 전용 allowlist가 기존 `pilot` 환경 배포 경로와 충돌

* Severity: **Blocker**
* Category: 배포/호환성 / 요구사항 제약 충돌
* Plan section: Global Constraints, Task 2 Step 2, Task 5 Step 3
* Evidence type: Confirmed fact
* Current plan: `SUPPORTED_RUNTIME_ENVIRONMENTS = frozenset({"dev","qa","prod"})`를 도입하고, allowlist 밖 값은 `ValueError`, API key 생성 시 422로 거부합니다.
* Review finding: 저장소에는 `pilot` environment로 동작하는 폐쇄망 배포 경로가 존재하며, 계약 테스트가 이를 고정하고 있습니다. 계획대로면 pilot 리허설/스모크 경로에서 릴리스·API key 생성이 422로 막힙니다.
* Evidence:
  - `.env.closed-network.example` → `INTENT_ROUTING_ENVIRONMENT=pilot`, `tests/unit/test_closed_network_packaging_contract.py:42,85`가 이를 단언.
  - `docs/ops/closed-network-deployment.md:3,73`이 pilot 배포 경로임을 명시.
  - `docs/ops/pilot-e2e-smoke.md:26,41`과 `docs/ops/ci-verification.md:66`이 `--environment ${INTENT_ROUTING_ENVIRONMENT}`를 `run_pilot_rehearsal.py` / `run_pilot_e2e_smoke.py`에 전달 → 그 값이 `scripts/seed_pilot.py:85,94`의 service/API key 생성 payload로 흘러갑니다.
  - 완화 요인: `docs/pilot/it-helpdesk-pilot-catalog.json:4`의 기본 environment는 `"dev"`이고 `tests/unit/test_pilot_fixtures.py:36`이 이를 단언합니다. 즉 **기본 경로는 dev이고, closed-network 문서 경로만 pilot**입니다.
* Potential impact: 폐쇄망 pilot 배포 문서를 그대로 따르면 API key 생성이 실패하고, 실패 원인이 ADR이 해결하려던 원래 증상(환경 불일치로 인한 401)과 유사한 형태로 재현됩니다.
* What the Coding Agent should verify: pilot 경로가 현재 유지 대상인지, 아니면 이미 사용 중단된 문서인지. 그리고 `pilot`을 (a) 지원 목록에 추가할지, (b) closed-network 문서를 `prod`로 이관할지, (c) 명시적으로 미지원 선언할지.
* How to verify:
  ```bash
  grep -rn "INTENT_ROUTING_ENVIRONMENT" docs/ops tests scripts .env.closed-network.example
  uv run pytest tests/unit/test_closed_network_packaging_contract.py tests/integration/test_pilot_rehearsal_flow.py -q
  ```
* Decision criteria: 사용자 요구사항은 "허용 환경은 dev/qa/prod"로 명확하므로 지원 목록에 `pilot`을 추가하는 것은 요구사항 위반입니다. 따라서 (b) 또는 (c)가 정합적이며, 어느 쪽이든 **closed-network 문서와 그 계약 테스트를 계획 범위에 넣어야** 합니다. 계획은 현재 이 파일들을 전혀 언급하지 않습니다.
* Possible response:
  * Add an additional step (Task 10에 closed-network/pilot 문서 및 계약 테스트 정리 추가)
  * Perform further investigation before deciding

### F-5. Audit 로그 RBAC 변경이 기존 통과 테스트와 정면 충돌하는데 계획이 이를 인지하지 않음

* Severity: **Major**
* Category: 회귀 / 계획의 완전성
* Plan section: Task 8 Step 1-2
* Evidence type: Confirmed fact
* Current plan: `SERVICE_AUDIT_LOG_READ_ROLES = frozenset({"auditor"})`로 축소하고, `service_owner`/`service_developer`가 `/audit-logs`에서 403을 받는 새 테스트를 추가합니다.
* Review finding: 기존 테스트 `test_application_admin_service_roles_can_read_assigned_service_logs`가 `service_owner`, `service_developer`, `service_operator`, `auditor` **네 역할 모두** `/admin/v1/services/{sid}/audit-logs`에서 200을 받는다고 단언합니다. 계획은 이 테스트의 재작성을 언급하지 않습니다(파일은 Task 8 수정 대상에 있으나, 이 특정 단언의 반전은 명시되지 않았습니다).
* Evidence: `tests/integration/test_admin_service_rbac_flow.py:173-240`, 특히 `assert audit_logs.status_code == 200, role`(224번째 줄 부근)이 루프 안에서 모든 역할에 적용됩니다. 현재 상수는 `admin.py:1404-1406`.
* Potential impact: 두 단언이 공존하면 Task 8 Step 4의 `pytest`가 반드시 실패하고, 어느 쪽이 의도인지 판단할 근거가 계획에 없습니다.
* What the Coding Agent should verify: 사용자 요구사항이 "service_developer는 audit 로그 불가"만 말하는지, `service_owner`도 금지인지. ADR은 owner/developer 둘 다 금지로 기술합니다(ADR "Authorization Matrix").
* How to verify:
  ```bash
  sed -n 173,240p tests/integration/test_admin_service_rbac_flow.py
  grep -rn "audit-logs" tests/integration/test_ops_metrics_api.py | head
  ```
* Decision criteria: ADR이 Accepted 상태이고 owner/developer 모두 금지라면 기존 테스트를 반전시키는 것이 맞습니다. 다만 `service_operator`와 `auditor`에 대한 결정은 요구사항에 없으므로, 계획이 제안한 `{"auditor"}`(=operator도 제거)는 요구사항을 넘어선 변경입니다(S-1 참고).
* Possible response:
  * Modify the current plan (기존 테스트 반전을 Task 8에 명시)
  * Add an additional step

### F-6. `get_allowed_runtime_environments()` 스니펫이 `config.py`에서 컴파일되지 않으며, 모듈 관례를 벗어남

* Severity: **Major**
* Category: 구현 정확성 / 코드베이스 일관성
* Plan section: Task 2 Step 2
* Evidence type: Confirmed fact
* Current plan: `raw_value = environ.get("ALLOWED_RUNTIME_ENVIRONMENTS", "dev,qa,prod")`를 `src/intent_routing/config.py`에 추가합니다.
* Review finding: `config.py`는 `from os import environ as process_environ`으로 임포트합니다. `environ`이라는 이름은 이 모듈에 존재하지 않으므로 스니펫 그대로면 `NameError`입니다. 또한 이 모듈의 기존 함수는 `load_raw_text_keyring_config(environ: Mapping[str,str] | None = None)`처럼 **환경 매핑을 주입 가능한 인자로 받는 관례**를 갖고 있어, 테스트가 monkeypatch 없이도 검증할 수 있게 되어 있습니다.
* Evidence: `src/intent_routing/config.py:6`(`from os import environ as process_environ`), `config.py:33-37`(`env = process_environ if environ is None else environ`).
* Potential impact: 사소한 컴파일 오류이지만, 관례를 벗어나면 이후 테스트 작성 방식도 갈라집니다.
* What the Coding Agent should verify: 새 함수도 `environ: Mapping[str,str] | None = None` 시그니처를 따르는 편이 나은지.
* How to verify: `sed -n 1,10p src/intent_routing/config.py` 및 `grep -n "process_environ" src/intent_routing/config.py`
* Decision criteria: 같은 모듈 안에서 두 가지 환경 접근 방식이 공존하는 것보다, 기존 주입 가능 시그니처를 따르는 편이 일관적입니다. 반대로 runtime hot path에서 매 요청 호출된다면 인자 없는 단순 함수 + 캐시가 나을 수 있습니다(F-7과 함께 판단).
* Possible response:
  * Modify the current plan

### F-7. allowlist 파싱 실패가 요청 시점 500으로 나타남 (기동 시 검증 부재)

* Severity: **Major**
* Category: 운영 영향 / 실패 모드
* Plan section: Task 2 Step 2, Step 4
* Evidence type: Reasoned inference (근거: 계획이 제시한 호출 위치)
* Current plan: `require_api_key` 안에서 `get_allowed_runtime_environments()`를 호출하고, 잘못된 값이면 `ValueError`를 발생시킵니다.
* Review finding: `ALLOWED_RUNTIME_ENVIRONMENTS=dev,staging`처럼 오타가 있으면 **모든 런타임 요청이 500 INTERNAL_ERROR**가 됩니다(FastAPI 의존성에서 raw `ValueError`는 500으로 변환). 게다가 매 요청마다 파싱하므로 오류 로그가 요청 수만큼 발생합니다. 기존 코드의 실패 모드(`_raise_authentication_failed` → 401 + `ErrorEnvelope`)와 형태가 다릅니다.
* Evidence: `src/intent_routing/api/dependencies.py:53-62`(에러 봉투 규약), `src/intent_routing/api/runtime.py:143-202`(RuntimeApiError 계층). 계획은 이 계층 어디에도 allowlist 오류를 매핑하지 않습니다.
* Potential impact: 설정 오타가 배포 후 첫 트래픽에서야 드러나고, 증상이 인증 오류가 아니라 전면 장애로 나타납니다.
* What the Coding Agent should verify: 앱 기동 시점(예: `main.py`의 `create_app`)에 allowlist를 한 번 검증·캐시하는 경로가 있는지.
* How to verify:
  ```bash
  grep -n "def create_app" -A 40 src/intent_routing/main.py
  grep -rn "lru_cache\|@cache" src/intent_routing | head
  ```
* Decision criteria: 기동 시 검증은 "잘못된 설정으로 뜨지 않는다"는 명확한 실패 모드를 주고, 요청 경로 비용도 없앱니다. 반대로 테스트에서 `monkeypatch.setenv` 후 즉시 반영되길 원한다면(계획의 Task 2 Step 3 테스트가 그렇습니다) 캐시는 방해가 됩니다 — 이 경우 `create_app` 시점 검증 + 요청 시점 재조회를 분리하거나, 테스트에서 캐시를 클리어해야 합니다.
* Possible response:
  * Add an additional step (기동 시 검증)
  * Modify the current plan

### F-8. 전역 `POST /admin/v1/api-keys`가 environment 검증을 우회함

* Severity: **Major**
* Category: 보안 / 데이터 정합성
* Plan section: Task 5 Step 3
* Evidence type: Confirmed fact
* Current plan: `_runtime_setup_environment`에서만 `SUPPORTED_RUNTIME_ENVIRONMENTS` 검증을 수행합니다.
* Review finding: `create_api_key`(전역 엔드포인트, `admin.py:4067-4095`)는 `_runtime_setup_environment`를 거치지 않고 `request.environment`를 그대로 `_create_api_key_for_service`에 넘깁니다. 이 경로로는 계획 이후에도 `environment="test"` 같은 키를 생성할 수 있고, 그 키는 런타임에서 allowlist 밖이라 401을 받습니다 — ADR이 서술한 원래 장애 증상과 동일한 형태입니다.
* Evidence: `src/intent_routing/api/admin.py:4074-4089`(검증 없음) vs `admin.py:4135-4136`(list 경로는 `_runtime_setup_environment` 호출). 이 전역 엔드포인트는 `scripts/seed_pilot.py:90-99`가 사용합니다.
* Potential impact: "환경 불일치로 인한 조용한 401"이라는 원래 문제가 부분적으로 남습니다. 감사 관점에서도 유효하지 않은 environment 값이 `api_keys` 테이블에 축적됩니다.
* What the Coding Agent should verify: `ApiKeyCreateRequest.environment`에 Pydantic 수준 검증(`Literal["dev","qa","prod"]` 또는 `field_validator`)을 넣는 것이 두 경로를 한 번에 덮는지.
* How to verify:
  ```bash
  sed -n 540,600p src/intent_routing/api/admin.py    # ApiKeyCreateRequest / ServiceApiKeyCreateRequest 정의
  grep -rn "admin/v1/api-keys\"" scripts tests | head
  ```
* Decision criteria: 요청 스키마 수준 검증은 두 엔드포인트를 모두 덮고 422 응답도 자동으로 맞춰지지만, 기존 계약 문서의 오류 표(`docs/api/admin-runtime-setup-contracts.md:420`)와 문구를 함께 갱신해야 합니다. 헬퍼 수준 검증만 유지하면 전역 엔드포인트에 명시적 호출을 추가해야 합니다.
* Possible response:
  * Modify the current plan
  * Add an additional step

### F-9. 런타임 에러 경로의 로그 environment가 채워질 수 없는 구간이 있음

* Severity: **Major**
* Category: 요구사항 정합성(운영 로그 환경 분리) / 관측성
* Plan section: Task 3 Step 2 ("success and error paths")
* Evidence type: Confirmed fact + Reasoned inference
* Current plan: `log_success`와 error 로깅 payload에 `environment`를 추가하고 `auth.environment`를 전달합니다.
* Review finding: 에러 경로는 두 종류입니다. (a) `runtime.py:463-512`의 `_log_and_raise`는 `auth`가 있으므로 environment 전달이 가능합니다. (b) `logging/trace.py:94-147`의 `log_runtime_preflight_error`는 **인증 실패/요청 검증 실패 등 AuthContext가 없는 시점**에 호출되며 `request.headers`에서만 값을 얻습니다. 요구사항상 environment를 헤더에서 받을 수 없으므로, 이 경로의 로그는 `environment = NULL`이 됩니다. 계획은 이 구분을 다루지 않습니다.
* Evidence: `src/intent_routing/logging/trace.py:119-120,135-136`(`request.headers.get("X-App-Id")`, `X-Service-Id`만 사용). `trace.py:64-74`(`should_log_runtime_error`)가 미들웨어/예외 핸들러 경로임을 시사합니다.
* Potential impact: Admin UI에서 `environment=qa` 필터를 걸면 인증·검증 실패 로그가 전부 사라집니다. "runtime logs는 environment 분리" 요구사항이 부분적으로만 충족되고, 오히려 장애 조사 시 누락을 유발합니다.
* What the Coding Agent should verify: preflight 로그에서 environment를 어디까지 채울 수 있는지(예: 인증은 성공했으나 이후 검증에서 실패한 케이스는 key 조회가 가능할 수 있음)와, UI 필터가 `NULL`을 어떻게 취급할지.
* How to verify:
  ```bash
  grep -rn "log_runtime_preflight_error" src tests
  uv run pytest tests/integration/test_trace_audit_logs.py -q
  ```
* Decision criteria: 최소한 (1) environment 필터가 `NULL` 행을 포함할지 제외할지 명시적으로 결정하고, (2) UI에 "환경 미상" 표시 규약을 두는 것이 필요합니다. 계획의 `'없음'` 렌더링(Task 3 Step 5)은 표시만 다루고 필터 의미론은 다루지 않습니다.
* Possible response:
  * Modify the current plan
  * Add an additional step

### F-10. `service_developer`가 governed publish 경로로 릴리스를 활성화할 수 있는 우회로가 남음

* Severity: **Major**
* Category: 보안(인가) / 요구사항 정합성
* Plan section: Task 8 Step 2-3
* Evidence type: Confirmed fact
* Current plan: `_require_release_management_access`를 `service_owner` 전용으로 좁히고, 읽기 전용 헬퍼를 분리합니다.
* Review finding: 릴리스 write 경로는 `create_release` / `activate_release` / rollback 외에도 governed publish 워크플로가 존재합니다. `_require_publish_request_access`(admin.py:1555-1563)와 `_require_publish_activation_access`(admin.py:1574-1582)는 여전히 `service_developer`를 허용합니다. 특히 publish **activation**은 실질적으로 릴리스 활성화입니다. 계획은 이 두 헬퍼를 언급하지 않습니다.
* Evidence: `src/intent_routing/api/admin.py:1555-1582`, 그리고 `admin.py:5960-5999`의 publish 처리부가 `release_service.release_after_state(release)`로 감사 로그를 남기는 것으로 보아 실제 릴리스 상태를 변경합니다.
* Potential impact: "service_developer는 release를 쓸 수 없다"는 요구사항이 주 경로에서만 지켜지고 governed 경로에서 뚫립니다. RBAC 변경의 핵심 목적이 부분적으로 무산됩니다.
* What the Coding Agent should verify: publish request/decision/activation 3단계 각각의 의도된 역할. `_require_publish_decision_access`는 이미 owner 전용이므로, developer가 request는 하되 activation은 못 하게 하는 것이 원래 설계 의도였는지.
* How to verify:
  ```bash
  grep -n "_require_publish_" src/intent_routing/api/admin.py
  grep -rn "publish" docs/superpowers/plans/2026-07-08-phase2-governed-backend-completion.md | head -20
  uv run pytest tests/integration -k publish -q
  ```
* Decision criteria: governed publish가 "승인 기반 릴리스"라는 별도 통제 아래 있고 decision 단계가 owner 전용이라면, developer의 request 권한 유지는 방어 가능합니다. 그러나 **activation**까지 developer가 가능하다면 요구사항과 충돌하므로 좁혀야 합니다.
* Possible response:
  * Perform further investigation before deciding
  * Add an additional step

### F-11. 내비게이션을 `displayRoles` 기준으로 바꾸면 `auditor`가 Audit Logs 화면에 도달할 수 없음

* Severity: **Major**
* Category: 일관성 / 회귀
* Plan section: Task 7 Step 2-3, Task 8 Step 2
* Evidence type: Confirmed fact
* Current plan: `/audit-logs`의 `allowedRoles`를 `['system_admin']`으로 두고, 백엔드는 `SERVICE_AUDIT_LOG_READ_ROLES = {"auditor"}`로 둡니다.
* Review finding: 두 결정이 서로 모순됩니다. 백엔드는 `auditor`에게 감사 로그 읽기를 허용하는데, 내비게이션은 `auditor`에게 메뉴를 숨깁니다. 결과적으로 `auditor` 역할은 UI에서 자기 권한을 사용할 수 없습니다.
* Evidence: 계획 Task 7 Step 2의 라우트 스펙 vs Task 8 Step 2의 상수. 현재 `PATTERN_KIT.md:209-210`은 auditor를 "audit log inspection" 역할로 문서화하고 있습니다.
* Potential impact: 역할 매트릭스가 문서·백엔드·UI 세 곳에서 어긋나며, 계획 Task 10 Step 2가 작성할 문서도 어느 쪽을 기술해야 할지 모호해집니다.
* What the Coding Agent should verify: 사용자 요구사항은 `system_admin`/`service_owner`/`service_developer` 3역할만 규정합니다. `auditor`/`service_operator`에 대한 변경 권한이 이번 요구사항에 포함되는지.
* How to verify:
  ```bash
  grep -n "auditor" src/intent_routing/api/admin.py | head -20
  grep -rn "auditor" frontend/intent-routing-console/src | head
  ```
* Decision criteria: 요구사항에 없는 역할은 **현상 유지**가 안전합니다. 즉 `/audit-logs`의 `allowedRoles`를 `['system_admin','auditor']`로 두면 백엔드와 정합합니다. 반대로 auditor를 실제로 폐기하기로 했다면 그 결정을 ADR에 먼저 기록하는 편이 낫습니다.
* Possible response:
  * Modify the current plan

### F-12. `list_release_candidates`의 튜플 키 변경은 불필요할 수 있음

* Severity: **Minor**
* Category: 변경 범위 / 단순성
* Plan section: Task 4 Step 3
* Evidence type: Confirmed fact
* Current plan: `existing_releases`를 `(test_run_id, environment)` 튜플 키 딕셔너리로 바꿉니다.
* Review finding: `repository.list_releases(service_id, target_environment)`가 이미 environment로 필터링하므로(`repositories.py:2318-2322`), 결과 집합은 단일 환경입니다. 따라서 기존 `{release.test_run_id: release}` 키만으로도 "해당 환경에 이미 릴리스됨" 판정은 정확합니다. 실제로 제거해야 하는 것은 `environment_matches_service` 조건과 그 block reason뿐입니다.
* Evidence: `src/intent_routing/db/repositories.py:2313-2325`, `src/intent_routing/api/admin.py:6091-6116`.
* Potential impact: 없음(동작은 같음). 다만 불필요한 diff가 리뷰 부담을 늘립니다.
* What the Coding Agent should verify: `list_releases`가 `environment=None`으로 호출되는 경로가 이 함수 안에 있는지(현재는 항상 `target_environment`가 결정됨).
* How to verify: `sed -n 6079,6120p src/intent_routing/api/admin.py`
* Decision criteria: environment가 `None`일 수 있는 경로를 새로 만든다면 튜플 키가 안전합니다. 그렇지 않다면 최소 변경이 낫습니다.
* Possible response:
  * Modify the current plan
  * Keep the current plan (방어적 코드로 유지하는 것도 무해)

### F-13. `_require_release_read_access` 신설이 기존 `_require_release_review_access`와 중복

* Severity: **Minor**
* Category: 코드베이스 일관성 / 중복
* Plan section: Task 8 Step 3
* Evidence type: Confirmed fact
* Current plan: 새 헬퍼 `_require_release_read_access`를 도입합니다.
* Review finding: `admin.py:1544-1552`에 `_require_release_review_access`가 이미 존재하며, 허용 역할은 `{"service_developer","service_owner","auditor"}` + `system_admin`입니다. 계획이 원하는 읽기 권한 집합과 `auditor` 하나 차이입니다. 현재 `get_release_diff`(admin.py:6155)가 이를 사용합니다.
* Evidence: `src/intent_routing/api/admin.py:1544-1552`, `admin.py:6155`.
* Potential impact: 거의 동일한 두 헬퍼가 공존하면 이후 어느 것을 써야 하는지 혼동이 생깁니다.
* What the Coding Agent should verify: `auditor`가 릴리스 목록을 읽을 수 있어야 하는지(F-11과 동일한 판단 축).
* How to verify: `grep -n "_require_release_review_access" src/intent_routing/api/admin.py tests -r`
* Decision criteria: `auditor` 포함이 허용 가능하다면 기존 헬퍼 재사용이 명백히 낫습니다. auditor를 반드시 배제해야 한다면 새 헬퍼가 정당하지만, 기존 헬퍼의 용도(diff 조회)와의 관계를 주석이나 이름으로 구분해야 합니다.
* Possible response:
  * Modify the current plan

### F-14. Task 4 Step 4는 존재하지 않는 검증을 수정하라고 지시함

* Severity: **Minor**
* Category: 전제와 근거
* Plan section: Task 4 Step 4
* Evidence type: Confirmed fact
* Current plan: "`releases.py`에서 한 test run이 전역적으로 하나의 릴리스만 갖는다고 가정하는 검증을 찾아 변경한다."
* Review finding: `validate_release_inputs`(releases.py:49-95)에는 그런 검증이 없습니다. DB에도 `releases.test_run_id` unique 제약이 없습니다(0001 마이그레이션 확인). 따라서 이 단계는 no-op일 가능성이 높습니다.
* Evidence: `src/intent_routing/versions/releases.py:49-95`, `alembic/versions/0001_initial_intent_routing.py:254-286`.
* Potential impact: 없음. 다만 "찾아서 고쳐라"는 지시가 남아 있으면 구현자가 없는 것을 찾느라 시간을 쓰거나, 없다는 사실을 파손으로 오인할 수 있습니다.
* What the Coding Agent should verify: 위 두 위치.
* How to verify:
  ```bash
  grep -n "test_run" src/intent_routing/versions/releases.py
  grep -n "UniqueConstraint\|unique" alembic/versions/0001_initial_intent_routing.py | head
  ```
* Decision criteria: 확인 결과 검증이 없다면 이 단계를 "확인 후 변경 불필요를 기록"으로 축소하는 편이 명확합니다.
* Possible response:
  * Remove the planned step
  * Modify the current plan

### F-15. `require_api_key`에 남는 `get_runtime_environment` 의존성의 처리 방침이 불명확

* Severity: **Minor**
* Category: 정리 / 테스트 신뢰성
* Plan section: Task 2 Step 4-5, Step 3의 테스트 스니펫
* Evidence type: Confirmed fact
* Current plan: `runtime.py`의 `environment: Depends(get_runtime_environment)` 파라미터는 제거하지만, `dependencies.py`의 `require_api_key`에서 같은 의존성을 어떻게 할지는 명시하지 않습니다. 동시에 Task 2 Step 3의 테스트는 여전히 `app.dependency_overrides[get_runtime_environment] = lambda: "prod"`를 설정합니다.
* Review finding: allowlist 검사로 교체되면 `require_api_key`의 `environment` 파라미터는 사용되지 않습니다. 남겨두면 죽은 의존성이 되고, 테스트의 override는 아무 효과 없이 "환경을 제어하고 있다"는 착각을 줍니다.
* Evidence: `src/intent_routing/api/dependencies.py:127-135`(파라미터 선언), `dependencies.py:93-94`(`get_runtime_environment`), `dependencies.py:151`(유일한 사용처).
* Potential impact: 테스트가 실제로는 아무것도 고정하지 않으면서 통과해, 나중에 회귀를 놓칠 수 있습니다.
* What the Coding Agent should verify: `get_runtime_environment`의 다른 사용처(`runtime.py:14` import 포함)와 완전 제거 가능 여부.
* How to verify: `grep -rn "get_runtime_environment" src tests`
* Decision criteria: 완전 제거하면 `INTENT_ROUTING_ENVIRONMENT`의 런타임 라우팅 역할이 코드에서 사라져 문서(Task 10 Step 3)와 일치합니다. 다른 목적(로그 태깅, 헬스체크)으로 쓰인다면 남기되 `require_api_key`에서만 떼어내야 합니다.
* Possible response:
  * Modify the current plan

### F-16. Task 11 스모크 시나리오에 릴리스 활성화 단계가 없음

* Severity: **Major**
* Category: 검증 가능성
* Plan section: Task 11 Step 4
* Evidence type: Confirmed fact
* Current plan: Service 생성 → 역할 부여 → intent/catalog → test run → dev/qa/prod 릴리스 생성 → qa API key 생성 → `/v1/intent-route` 호출 → `release_version`이 qa active 릴리스인지 확인.
* Review finding: `create_release`는 `active=False`로 릴리스를 만듭니다(`releases.py:170`). 별도의 `POST .../releases/{version}:activate`(admin.py:6208-6218)를 호출하지 않으면 `get_active_release`가 `None`을 반환하고 런타임 호출은 실패합니다. 스모크 절차에 활성화 단계가 빠져 있어, 실행자가 "구현 실패"로 오판할 수 있습니다.
* Evidence: `src/intent_routing/versions/releases.py:154-174`(`active=False`), `src/intent_routing/api/admin.py:6208-6218`(`activate_release`), `repositories.py:2351-2358`(`get_active_release`가 `active` 기준 조회).
* Potential impact: 최종 수용 검증이 재현 불가능해집니다.
* What the Coding Agent should verify: 활성화가 별도 액션인지, 아니면 UI가 생성 직후 자동 활성화하는지.
* How to verify:
  ```bash
  grep -n "activate" frontend/intent-routing-console/src/pages/Releases/index.tsx | head
  sed -n 6208,6260p src/intent_routing/api/admin.py
  ```
* Decision criteria: 활성화가 별도 액션이라면 스모크 절차에 "5-1. qa 릴리스 활성화"를 넣어야 합니다. 자동 활성화라면 그 사실을 절차에 명시하면 충분합니다.
* Possible response:
  * Add an additional step

### F-17. `.env.example` 계약 테스트가 정확 일치 단언이라 allowlist 변수 추가 시 깨짐

* Severity: **Major**
* Category: 계획의 완전성 / 설정
* Plan section: Task 2 (File Map에 `tests/unit/test_env_contract.py` 포함), Task 10 Step 3
* Evidence type: Confirmed fact
* Current plan: `test_env_contract.py`에 allowlist 단위 테스트를 추가하고, README/runbook의 `export INTENT_ROUTING_ENVIRONMENT=dev`를 `export ALLOWED_RUNTIME_ENVIRONMENTS=dev,qa,prod`로 바꿉니다.
* Review finding: 같은 파일의 `test_env_example_uses_runtime_local_defaults`는 `assert values == EXPECTED_LOCAL_ENV`로 **정확 일치**를 요구합니다. `.env.example`에 새 변수를 추가하면 `EXPECTED_LOCAL_ENV`도 함께 갱신해야 합니다. 계획은 `.env.example`, `compose.yaml`, CI 워크플로, 로컬 dev 스택 스크립트를 언급하지 않습니다.
* Evidence:
  - `tests/unit/test_env_contract.py:12-28,46-49`(정확 일치 단언, `INTENT_ROUTING_ENVIRONMENT: "dev"` 포함).
  - `tests/unit/test_ci_workflow_contract.py:47`이 `"INTENT_ROUTING_ENVIRONMENT: dev"`를 CI 워크플로에서 단언.
  - `tests/unit/test_local_dev_stack_script.py`, `tests/unit/test_macos_local_dev_stack_script.py`가 존재하며, Task 11 Step 4는 `scripts/run_local_dev_stack_macos.sh`를 사용합니다.
  - `tests/unit/test_operator_docs_contract.py:13`이 `"export INTENT_ROUTING_ENVIRONMENT=dev"`를 문서에서 단언 — Task 10 Step 3의 문서 변경과 직접 충돌합니다(이 파일은 계획에 포함되어 있으므로 인지는 되어 있음).
* Potential impact: Task 2/Task 10의 "Expected: PASS"가 성립하지 않습니다.
* What the Coding Agent should verify: `ALLOWED_RUNTIME_ENVIRONMENTS`를 `.env.example`에 넣을지(넣으면 계약 테스트 갱신 필요), 아니면 기본값에만 의존할지(넣지 않으면 운영자 발견 가능성이 낮아짐).
* How to verify:
  ```bash
  uv run pytest tests/unit/test_env_contract.py tests/unit/test_ci_workflow_contract.py \
    tests/unit/test_local_dev_stack_script.py tests/unit/test_macos_local_dev_stack_script.py \
    tests/unit/test_operator_docs_contract.py -q
  grep -rn "INTENT_ROUTING_ENVIRONMENT" scripts .github 2>/dev/null
  ```
* Decision criteria: 기본값이 `dev,qa,prod`이고 대부분의 배포에서 그대로 쓴다면 `.env.example`에 추가하지 않는 선택도 방어 가능합니다. 그러나 이 변수가 "한 프로세스가 prod를 서빙하는지"를 결정하는 보안 성격의 가드레일이므로, 명시적으로 노출하는 편이 감사 가능성 측면에서 낫습니다.
* Possible response:
  * Add an additional step
  * Perform further investigation before deciding

### F-18. 런타임 로그 export/metrics 경로가 environment를 반영하지 않음

* Severity: **Minor**
* Category: 계획의 완전성 / 관측성
* Plan section: Task 3 File Map("environment-aware runtime logs/metrics") vs Step 3-4(로그만 다룸)
* Evidence type: Confirmed fact
* Current plan: `list_masked_runtime_logs`에 environment 필터를 추가합니다.
* Review finding: 같은 컬럼 세트를 쓰는 `list_masked_runtime_logs_for_export`(repositories.py:2727-2745)와 `runtime_metrics`(repositories.py:2626-2638 → `ops/metrics.py`)는 계획 단계에 없습니다. File Map은 metrics를 포함한다고 적었지만 Step에는 없습니다.
* Evidence: `src/intent_routing/db/repositories.py:2705-2745, 2626-2638`.
* Potential impact: 마스킹 CSV export는 environment 컬럼을 갖게 되지만 필터는 없고, 메트릭은 여러 환경이 합산되어 dev 트래픽이 prod 지표를 오염시킵니다.
* What the Coding Agent should verify: 메트릭 화면이 실제로 환경 분리를 요구하는지(요구사항은 "runtime logs는 environment 분리"만 명시).
* How to verify:
  ```bash
  grep -n "runtime_metrics_for_service" -A 30 src/intent_routing/ops/metrics.py | head -40
  grep -rn "runtime-metrics" frontend/intent-routing-console/src | head
  ```
* Decision criteria: 요구사항 문언은 로그만 다루므로 메트릭은 후속으로 미뤄도 정당합니다. 다만 File Map의 "metrics" 표현은 실제 범위와 맞추어 수정하는 편이 혼동을 줄입니다.
* Possible response:
  * Modify the current plan (범위 문구 정리)
  * Add an additional step (메트릭까지 포함하기로 결정한 경우)

### F-19. 내비게이션 필터를 `displayRoles`로 바꾸면 서비스 선택 상태에 메뉴가 종속됨

* Severity: **Question**
* Category: UX / 인가 표시
* Plan section: Task 7 Step 2-3
* Evidence type: Confirmed fact + Needs verification
* Current plan: `getAdminShellRouteSpecs(displayRoles)`로 바꾸고, `AdminShell`이 세션의 display roles를 넘깁니다.
* Review finding: `getDisplayRoles`(adminSession.ts:85-92)는 **선택된 서비스**의 역할 + 전역 역할만 반환합니다. 따라서 서비스가 아직 선택되지 않았거나, 사용자가 소유하지 않은 서비스를 선택한 순간 `/api-keys` 메뉴가 사라졌다 나타났다 합니다. 현재 구현은 `session.globalRoles`만 사용하므로(AdminShell.tsx:120) 이 동작 변화가 새로 생깁니다.
* Evidence: `frontend/intent-routing-console/src/models/adminSession.ts:85-92`, `components/AdminShell.tsx:120`, `models/adminSession.test.ts:281`(역할이 빈 배열이 되는 케이스가 이미 테스트됨).
* Potential impact: 서비스 전환 시 메뉴가 흔들리는 UX. 다만 "선택된 서비스 기준으로 권한을 보여준다"는 해석이 오히려 정확할 수도 있습니다.
* What the Coding Agent should verify: 서비스 미선택 초기 상태에서 어떤 메뉴가 보여야 하는지, 그리고 `service_owner`가 전역 역할 없이 서비스 역할만 가진 계정으로 로그인했을 때 초기 렌더가 어떻게 되는지.
* How to verify:
  ```bash
  sed -n 100,140p frontend/intent-routing-console/src/components/AdminShell.tsx
  sed -n 260,300p frontend/intent-routing-console/src/models/adminSession.test.ts
  ```
* Decision criteria: 메뉴가 깜빡이는 것이 문제라면 "전역 역할 ∪ 모든 접근 가능 서비스의 역할 합집합"으로 필터링하고, 페이지 내부에서 선택 서비스 기준 권한을 재검사하는 편이 안정적입니다. 반대로 "선택된 서비스에서 할 수 있는 일만 보여준다"가 제품 의도라면 계획대로가 맞습니다.
* Possible response:
  * Perform further investigation before deciding

---

## 4. Potentially Missing Work

### M-1. `scripts/seed_pilot.py` 및 pilot/ops 스크립트 갱신

* Related requirement: Service 등록에서 environment/preset 제거
* Why it may be needed: 이 스크립트는 `POST /admin/v1/services`에 제거될 필드를 보내며, 여러 통합 테스트가 이를 경유합니다.
* Evidence: `scripts/seed_pilot.py:80-99`, `tests/unit/test_seed_pilot.py:255,297`, `tests/integration/test_pilot_seed_flow.py`, `tests/integration/test_pilot_rehearsal_flow.py`.
* What should be checked: 스크립트의 `--environment` 인자가 앞으로 무엇을 의미하는지(릴리스/키 environment만 의미하도록 축소되는지).
* Apply when: 전체 `pytest`를 완료 기준으로 삼는 경우(현재 Task 11이 그렇게 보이지 않지만 CI는 그럴 가능성이 높음).
* Do not apply when: pilot 경로를 이번 변경에서 명시적으로 동결/제외하기로 결정한 경우 — 다만 그 결정은 문서화가 필요합니다.
* Suggested verification: `uv run pytest tests/unit/test_seed_pilot.py tests/integration/test_pilot_seed_flow.py -q`

### M-2. `.env.example` / compose / CI / 로컬 dev 스택의 환경변수 정합

* Related requirement: `ALLOWED_RUNTIME_ENVIRONMENTS`로 서빙 환경 제한
* Why it may be needed: Task 11 Step 4가 `ALLOWED_RUNTIME_ENVIRONMENTS=dev,qa,prod ./scripts/run_local_dev_stack_macos.sh`로 기동하라고 하지만, 스크립트가 환경변수를 전달하는지 확인되지 않았습니다.
* Evidence: `tests/unit/test_macos_local_dev_stack_script.py`, `tests/unit/test_local_dev_stack_script.py`가 스크립트 내용을 계약으로 고정합니다. `tests/unit/test_env_contract.py:46`이 `.env.example` 정확 일치를 요구합니다.
* What should be checked: 스크립트가 `.env`를 로드하는지, 인라인 환경변수를 uvicorn 프로세스까지 전달하는지.
* Apply when: allowlist를 실제 운영 가드레일로 사용할 경우.
* Do not apply when: 기본값(`dev,qa,prod`)만으로 충분하고 변수 노출을 원하지 않는 경우.
* Suggested verification: `grep -n "uvicorn\|export\|env" scripts/run_local_dev_stack_macos.sh | head -30`

### M-3. 기존 API key / 릴리스의 environment 값 정리 절차

* Related requirement: 허용 환경은 dev/qa/prod
* Why it may be needed: 계획은 "로컬 데이터를 지우고 재등록"이라고 했지만, ADR 맥락에 등장하는 `test` environment 키나 폐쇄망의 `pilot` 키가 남아 있으면 런타임에서 401만 받고 원인 파악이 어렵습니다.
* Evidence: `src/intent_routing/api/dependencies.py:53-62`는 실패 사유를 구분하지 않고 동일한 `AUTHENTICATION_FAILED`를 반환합니다.
* What should be checked: allowlist 밖 키를 조회/식별할 수 있는 관리 화면 또는 쿼리가 있는지(`GET /admin/v1/api-keys?environment=`는 존재).
* Apply when: 로컬 외 환경(폐쇄망 pilot 등)에 이미 키가 존재하는 경우.
* Do not apply when: 모든 데이터가 실제로 폐기 가능한 로컬 데이터뿐인 경우.
* Suggested verification: 운영 DB에서 `select environment, count(*) from api_keys group by 1;`

### M-4. allowlist 거부에 대한 운영 관측 수단

* Related requirement: 하나의 백엔드가 허용 환경만 서빙
* Why it may be needed: allowlist 밖 키가 401을 받을 때, 로그가 없으면 "키가 틀렸는지, 환경이 막혔는지" 구분할 수 없습니다. 이는 ADR이 해결하려던 원래 증상과 같은 유형의 진단 난이도입니다.
* Evidence: `dependencies.py:147-153`의 현재 구조는 모든 실패를 한 분기로 합칩니다. 인증 실패 로그는 `log_runtime_preflight_error` 경로로 남지만 environment는 비어 있습니다(F-9).
* What should be checked: 인증 실패 시 서버 로그(structured log)가 남는지, 남는다면 사유 코드를 구분할 수 있는지.
* Apply when: 다중 환경을 한 프로세스로 서빙하기로 확정한 경우(=이번 요구사항).
* Do not apply when: 감사/로그 정책상 실패 사유 노출이 제한되는 경우 — 그때도 최소한 서버 사이드 카운터는 검토할 가치가 있습니다.
* Suggested verification: `grep -rn "logger\|logging" src/intent_routing/api/dependencies.py`

### M-5. Runtime Logs 화면의 environment 필터 UI

* Related requirement: runtime logs는 environment 분리
* Why it may be needed: Task 3 Step 5는 테이블 **컬럼**만 추가하고, Step 4에서 만든 `?environment=` 쿼리 파라미터를 화면에서 사용하는 단계가 없습니다. File Map에는 "environment column/filter"라고 적혀 있어 Step과 불일치합니다.
* Evidence: 계획 Task 3 Step 5 vs File Map 항목. `frontend/intent-routing-console/src/pages/RuntimeLogs/index.tsx`에는 현재 environment 관련 코드가 없습니다.
* What should be checked: 요구사항의 "분리"가 표시 분리인지 필터 분리인지.
* Apply when: 운영자가 환경별로 로그를 조회해야 하는 경우(요구사항 문언상 그렇게 읽힘).
* Do not apply when: 컬럼 표시만으로 충분하다고 사용자와 합의된 경우.
* Suggested verification: `grep -n "params\|filter" frontend/intent-routing-console/src/pages/RuntimeLogs/index.tsx | head`

### M-6. `docs/adr/2026-07-09-admin-ui-c3-runtime-integration-and-api-key-scope.md`의 갱신

* Related requirement: API key는 service+environment+app_id에 연결
* Why it may be needed: 이 ADR은 계약 문서 테스트가 참조하는 문서이며(`tests/unit/test_admin_runtime_setup_contract_docs.py:4`), 이미 working tree에서 수정 중입니다. 새 ADR(2026-07-21)이 그 결정을 뒤집는 부분이 있다면 상호 참조가 필요합니다.
* Evidence: `docs/api/admin-runtime-setup-contracts.md:299`("must belong to the same `{service_id}` and `environment`"), `:420`("Invalid `environment` | 422 | Must match Service/environment policy").
* What should be checked: 두 ADR이 모순 없이 읽히는지, "Service environment 정책"이라는 표현이 남아 있는지.
* Apply when: 계약 문서에 Service environment 기반 문구가 남아 있는 경우(현재 `:420`이 그렇습니다).
* Do not apply when: Task 10 Step 1의 오류 표 수정으로 이미 커버되는 경우.
* Suggested verification: `uv run pytest tests/unit/test_admin_runtime_setup_contract_docs.py -q`

---

## 5. Unverified Assumptions

### A-1. 계획의 테스트 코드 스니펫이 기존 헬퍼와 호환된다는 전제

* Assumption in the plan: `_client_with_service_owner`, `_seed_gate_passed_test_run`, `_seed_two_services_with_owner_and_target`, `_client_for_admin_user`, `_client_with_service_role`, `_seed_successful_release`, `_seed_active_release(..., environment=...)` 등을 호출하는 테스트를 추가할 수 있다.
* Available evidence: **이 헬퍼들은 존재하지 않습니다.** 실제 헬퍼는 다음과 같습니다.
  - `tests/integration/test_admin_runtime_setup_api.py`: `_client`, `_system_admin_client`, `_application_admin_client`, `_create_service(client, service_id)`, `_seed_active_release(db_session, service_id)` — **environment 인자 없음**.
  - `tests/integration/test_release_flow.py`: `_client`, `_admin_headers`, `_service_payload`, `_create_service(client, service_id)`, `_create_service_and_policy`, `_operator_headers`, `_auditor_headers` — 세션 쿠키가 아니라 **trusted header 방식**으로 보입니다.
  - `tests/integration/test_admin_service_rbac_flow.py`: `_create_service(repository, service_id, now=now)`, `_create_login_eligible_user_session(...)`, `_client(db_session)`, `_purge_rows(...)`.
  - `tests/integration/test_runtime_api.py`: `_record_for(secret, *, allowed_route_keys, environment, expires_at, key_hash, revoked_at, status)` — `service_id`가 `"svc-a"`로 **하드코딩**되어 있고 `service_id` 인자가 없습니다. 계획의 runtime 테스트는 동적 `service_id`를 헤더로 보내므로 `check_scope`에서 403이 납니다. `_seed_successful_release`는 없고 `_seed_runtime_state`가 있습니다.
* Why the assumption matters: 계획의 각 Task는 "실패하는 테스트를 먼저 작성"으로 시작합니다. 스니펫이 그대로 붙지 않으면 TDD 흐름의 첫 단계부터 재작성이 필요하고, 예상 소요와 검증 신뢰도가 달라집니다.
* Verification target: 위 4개 테스트 파일의 헬퍼 시그니처.
* Verification method:
  ```bash
  grep -n "^def _" tests/integration/test_release_flow.py tests/integration/test_admin_runtime_setup_api.py \
    tests/integration/test_admin_service_rbac_flow.py tests/integration/test_runtime_api.py
  sed -n 58,105p tests/integration/test_runtime_api.py
  ```
* Impact if false: 계획의 테스트 스니펫은 "의도 명세"로만 취급하고, 실제 헬퍼를 확장하는 작업(특히 `_record_for`에 `service_id` 파라미터 추가, `_seed_active_release`에 `environment` 추가)을 각 Task의 명시적 단계로 넣어야 합니다.

### A-2. `0011_api_key_optional_expiry`가 먼저 확정된다는 전제

* Assumption in the plan: `0012`의 `down_revision`을 `"0011_api_key_optional_expiry"`로 둡니다.
* Available evidence: `git status`상 `alembic/versions/0011_api_key_optional_expiry.py`는 **untracked**입니다. 관련 코드(`models.py`의 `expires_at: datetime | None`, `dependencies.py:118-120`의 None 처리)도 uncommitted 상태입니다.
* Why the assumption matters: 0011이 머지되지 않거나 리비전 ID가 바뀌면 0012의 체인이 깨집니다.
* Verification target: 0011의 머지 여부와 최종 리비전 ID.
* Verification method: `git log --oneline -- alembic/versions/0011_api_key_optional_expiry.py`, `uv run alembic heads`
* Impact if false: 마이그레이션 적용 실패 → Task 1의 모든 스키마 테스트가 실패합니다.

### A-3. Task 1의 스키마 테스트가 `information_schema` 조회로 검증 가능하다는 전제

* Assumption in the plan: `db_session` fixture가 Alembic head까지 마이그레이션된 실제 PostgreSQL을 가리킨다.
* Available evidence: `tests/unit/test_env_contract.py`가 `TEST_DATABASE_URL`을 다루고, 계약 문서 테스트가 "Alembic revision mismatch"를 언급합니다. 다만 conftest의 마이그레이션 적용 방식은 이번 검토에서 직접 확인하지 않았습니다.
* Why the assumption matters: Task 1 Step 2의 "Expected: 실패"와 Step 7의 "Expected: PASS"가 마이그레이션 자동 적용 여부에 달려 있습니다.
* Verification target: `tests/conftest.py` 또는 `tests/integration/conftest.py`의 DB 준비 로직.
* Verification method: `grep -rn "alembic\|upgrade\|create_all" tests/conftest.py tests/integration/conftest.py`
* Impact if false: 로컬에서 수동 `alembic upgrade head`가 필요하며, 그 절차를 Task 1에 명시해야 합니다.

### A-4. `runtime_logs.environment`를 nullable로 두어도 요구사항을 만족한다는 전제

* Assumption in the plan: `sa.Column("environment", sa.Text(), nullable=True)`.
* Available evidence: 기존 행에는 값이 없고 백필도 하지 않습니다. F-9에서 확인했듯 preflight 에러 경로는 앞으로도 NULL을 씁니다.
* Why the assumption matters: "runtime logs는 environment 분리"라는 요구사항이 NULL 행에 대해 어떻게 해석되는지가 정의되지 않았습니다.
* Verification target: 새 인덱스 `ix_runtime_logs_service_environment_created`가 NULL 행에서 유용한지, UI 필터가 NULL을 포함하는지.
* Verification method: 구현 후 `select environment, count(*) from runtime_logs group by 1;`
* Impact if false: 필터를 걸면 에러 로그가 사라지는 관측성 공백이 남습니다.

### A-5. `AccessibleServiceResponse`에서 `environment` 제거가 다른 소비자에게 영향 없다는 전제

* Assumption in the plan: File Map에 나열된 3개 페이지만 수정하면 됩니다.
* Available evidence: `ServiceScopeBar.tsx:39-40`이 반례입니다(F-3). 백엔드 쪽 `_accessible_service_response`(admin.py:1774)와 `_service_response`(admin.py:1756)의 다른 호출자도 확인이 필요합니다.
* Why the assumption matters: 타입 제거는 컴파일 타임에 잡히지만, 계획의 Task 순서상 Task 11에서야 발견됩니다.
* Verification target: `grep -rn "\.environment" frontend/intent-routing-console/src`와 `grep -n "_service_response\|_accessible_service_response" src/intent_routing/api/admin.py`
* Verification method: 위 명령 + `tsc --noEmit`을 Task 1 직후에 한 번 실행
* Impact if false: 후반 Task에서 되돌아가야 하는 재작업이 발생합니다.

---

## 6. Alternative Approaches Worth Comparing

### O-1. allowlist를 "요청 시점 환경변수 파싱"으로 둘 것인가, "기동 시 검증된 설정 객체"로 둘 것인가

* Existing approach: `require_api_key` 안에서 매 요청 `get_allowed_runtime_environments()`를 호출하고 잘못된 값이면 `ValueError`.
* Alternative approach: `create_app`(또는 설정 로더) 시점에 한 번 파싱·검증하여 frozenset을 앱 상태/모듈 상수로 보관하고, 요청 경로는 조회만 수행.
* Why the alternative may be relevant: `config.py`의 기존 패턴(`load_raw_text_keyring_config`가 명시적 예외 타입 `RawTextKeyringConfigError`/`MissingRawTextKekError`를 정의)이 이미 "설정 오류는 명시적 예외 타입으로"라는 관례를 갖고 있습니다.
* Advantages of the existing approach: 테스트에서 `monkeypatch.setenv` 후 즉시 반영되어 통합 테스트 작성이 쉽습니다. 계획의 Task 2 Step 3 테스트가 이 방식을 전제합니다.
* Risks of the existing approach: 설정 오타가 전 요청 500으로 나타남(F-7). 매 요청 문자열 파싱 비용(작지만 hot path).
* Advantages of the alternative: 잘못된 설정으로 프로세스가 기동하지 않아 실패가 조기·명확. 요청 경로 비용 없음. 기존 config 관례와 일관.
* Risks of the alternative: 테스트에서 환경변수를 바꾸려면 앱 재생성 또는 캐시 클리어가 필요해 테스트 코드가 조금 복잡해집니다.
* Prefer the existing approach when: allowlist를 테스트마다 다르게 바꿔가며 검증하는 시나리오가 많고, 운영 설정 오류 가능성이 낮다고 판단할 때.
* Prefer the alternative when: 이 변수가 "prod 트래픽을 이 프로세스가 받아도 되는가"를 결정하는 보안 가드레일로 간주될 때.
* Evidence needed to decide: `src/intent_routing/main.py`의 `create_app` 구조, 기존 통합 테스트가 앱을 어떻게 생성하는지(`create_app()` 호출 빈도), `config.py`의 예외 타입 관례.

### O-2. `service_developer`의 release **읽기** 권한을 신규 헬퍼로 분리할 것인가, 기존 `_require_release_review_access`를 재사용할 것인가

* Existing approach: 신규 `_require_release_read_access` 도입(owner/developer + system_admin).
* Alternative approach: 기존 `_require_release_review_access`(owner/developer/auditor + system_admin)를 `list_releases`/`list_release_candidates`/active 조회에 그대로 적용.
* Why the alternative may be relevant: 기존 헬퍼가 이미 같은 의미를 가지며 `get_release_diff`에서 쓰이고 있습니다(admin.py:1544-1552, 6155).
* Advantages of the existing approach: `auditor`를 릴리스 목록에서 배제할 수 있어 최소 권한 원칙에 더 부합.
* Risks of the existing approach: 거의 동일한 헬퍼 2개 공존 → 이후 신규 엔드포인트에서 잘못된 쪽을 고르기 쉬움. `get_release_diff`(review)와 `list_releases`(read)의 권한이 미묘하게 달라지는 이유를 문서화해야 함.
* Advantages of the alternative: 변경 범위 최소, 기존 테스트 영향 최소.
* Risks of the alternative: `auditor`가 릴리스 목록을 읽게 되는데, 이번 요구사항은 auditor를 규정하지 않았습니다(범위 확장 없이 현상 유지라는 해석도 가능).
* Prefer the existing approach when: auditor 배제가 명시적 보안 요구인 경우.
* Prefer the alternative when: 이번 변경을 요구사항에 나온 3역할로 한정하고 싶은 경우(S-1의 판단과 함께 결정).
* Evidence needed to decide: `auditor` 역할이 실제 운영에서 부여되고 있는지(`tests/integration/test_admin_service_rbac_flow.py:173-240`에서 auditor가 활성 역할로 다뤄짐), 그리고 사용자에게 auditor 정책 변경 권한이 위임되었는지.

---

## 7. Excessive or Unrelated Scope

### S-1. `service_operator` / `auditor`의 권한 축소가 요구사항 범위를 넘어섬

* Planned work: Task 8 Step 2에서 `SERVICE_AUDIT_LOG_READ_ROLES`를 `{"service_owner","service_developer","service_operator","auditor"}` → `{"auditor"}`로 축소(= `service_operator`도 제거). Task 7에서 `/audit-logs` 메뉴를 `system_admin` 전용으로 제한(= `auditor`도 제외).
* Why it may be excessive or unrelated: 사용자 요구사항은 `system_admin` / `service_owner` / `service_developer` 세 역할만 규정합니다. `service_operator`와 `auditor`에 대한 언급은 없습니다. ADR도 이 둘을 "retained governed/security roles"로 남긴다고 적고 있습니다(계획 Task 10 Step 2의 문구도 그렇습니다).
* Evidence: 사용자 요구사항 원문, ADR "Authorization Matrix"(owner/developer만 기술), 계획 Task 10 Step 2("`service_operator` and `auditor`: retained ... until a later decision"). 그러나 Task 7/8의 구현은 auditor를 UI에서 사실상 배제합니다 — 계획 내부에서도 문서와 구현이 어긋납니다.
* Risk of keeping it: 기존 `auditor`/`service_operator` 계정을 쓰는 감사·운영 흐름이 조용히 깨집니다. 관련 통합 테스트(`test_admin_service_rbac_flow.py:173-240`, `test_ops_metrics_api.py`)와 폐쇄망 증거 수집 스크립트가 영향받을 수 있습니다.
* Conditions that would justify keeping it: 사용자가 "요구사항에 없는 역할은 최소 권한으로 정리하라"고 확인해준 경우, 또는 해당 역할이 실제로 부여된 계정이 없다고 확인된 경우.
* Suggested decision check:
  ```bash
  grep -rn "service_operator\|auditor" src/intent_routing/api/admin.py | head -20
  uv run pytest tests/integration/test_admin_service_rbac_flow.py tests/integration/test_ops_metrics_api.py -q
  ```
  그리고 사용자에게 "auditor/service_operator 권한도 이번에 변경할지"를 확인.

### S-2. Task 10의 문서 변경 폭이 검증 가능한 범위보다 넓음

* Planned work: `README.md`, `docs/ops/intent-routing-local-runbook.md`, `docs/api/openapi-runtime-examples.md`, `PATTERN_KIT.md`, `E2E_DX_QA_CHECKLIST.md`, `admin-runtime-setup-contracts.md` 6개 문서 갱신.
* Why it may be excessive or unrelated: 이 중 계약 테스트가 존재하는 것은 `admin-runtime-setup-contracts.md`, `PATTERN_KIT.md`/`E2E_DX_QA_CHECKLIST.md`(handbook contract), `intent-routing-local-runbook.md`(operator docs contract)입니다. `openapi-runtime-examples.md`는 이번 변경에서 무엇이 바뀌어야 하는지 계획이 설명하지 않습니다.
* Evidence: `tests/unit/test_admin_runtime_setup_contract_docs.py`, `tests/unit/test_admin_ui_handbook_docs_contract.py`, `tests/unit/test_operator_docs_contract.py:13`.
* Risk of keeping it: 무해하지만, 검증 없는 문서 수정은 diff를 키우고 리뷰 초점을 흐립니다. 반대로 **누락된 문서**(closed-network 배포, pilot 스모크 — F-4 참고)가 더 중요합니다.
* Conditions that would justify keeping it: `openapi-runtime-examples.md`에 Service environment 기반 서술이 실제로 있는 경우.
* Suggested decision check: `grep -n "environment" docs/api/openapi-runtime-examples.md`

---

## 8. Verification Gaps

### T-1. "하나의 백엔드가 dev/qa/prod를 동시에 서빙한다"는 핵심 명제의 자동 검증 부재

* Behavior to verify: 동일 앱 인스턴스가 environment가 다른 두 API key 요청을 받아 각각 다른 active release로 라우팅한다.
* Current verification gap: Task 2 Step 3의 테스트는 **key 하나(qa)** 만 검증합니다. Task 11 Step 4의 수동 스모크도 qa 키 하나만 호출합니다. "동시 서빙"은 어디서도 검증되지 않습니다.
* Why the current validation may be insufficient: 단일 환경 테스트는 "프로세스 환경변수를 qa로 바꿨을 때"와 구분되지 않습니다. ADR이 해결하려는 문제의 본질은 다중 환경 공존입니다.
* Suggested verification: 하나의 `TestClient` 인스턴스에서 dev 키와 prod 키로 연속 호출하여 서로 다른 `release_version`이 반환되는지 확인하는 통합 테스트. `_record_for`에 `service_id` 파라미터를 추가하고 key_id별로 다른 레코드를 반환하는 lookup을 사용하면 됩니다(A-1 참고).
* Expected observable result: 같은 앱, 같은 service_id에 대해 dev 키 응답의 `release_version`과 prod 키 응답의 `release_version`이 서로 다르고, 각각 해당 환경의 active release와 일치.

### T-2. allowlist 거부 경로의 검증 부재

* Behavior to verify: `ALLOWED_RUNTIME_ENVIRONMENTS=dev`인 프로세스가 prod 키 요청을 401로 거부한다.
* Current verification gap: Task 2 Step 1의 단위 테스트는 **파서**만 검증합니다. Step 3의 통합 테스트는 허용된 환경만 다룹니다. Step 6의 "기존 401 테스트를 allowlist 거부로 재작성"은 지시만 있고 구체적 단언이 없습니다.
* Why the current validation may be insufficient: allowlist는 이번 변경에서 유일한 보안 가드레일입니다. 그것이 실제로 막는다는 증거가 없으면 요구사항("runtime backend may serve only allowed environments")이 미검증 상태로 남습니다.
* Suggested verification: `ALLOWED_RUNTIME_ENVIRONMENTS=dev,qa` 설정에서 `environment="prod"` 키로 `/v1/intent-route` 호출 → 401 + `error.code == "AUTHENTICATION_FAILED"`.
* Expected observable result: 401 응답, 그리고 (M-4를 채택한 경우) 서버 로그에 환경 거부 사유가 남음.

### T-3. Service 필드 제거의 전역 회귀 검증 부재

* Behavior to verify: environment/preset 제거 후 기존 기능 전체가 회귀 없이 동작한다.
* Current verification gap: Task 11 Step 1은 6개 파일만 실행합니다. F-1에서 확인한 16개 이상의 영향 파일 중 다수가 빠져 있습니다.
* Why the current validation may be insufficient: "PASS"가 나와도 실제로는 전체 스위트가 깨진 상태일 수 있습니다.
* Suggested verification: Task 11에 `uv run pytest -q` 전체 실행을 넣고, 변경 전 baseline 실패 수와 비교.
* Expected observable result: 전체 스위트가 변경 전과 동일하거나 더 나은 결과(신규 실패 0).

### T-4. 프론트엔드 전체 타입/테스트 검증 시점이 너무 늦음

* Behavior to verify: 타입 제거가 모든 소비처에 반영되었다.
* Current verification gap: `tsc --noEmit`이 Task 11 Step 3에서 처음 실행됩니다. 그 사이 Task 1(타입 제거)부터 Task 9까지 8개 Task가 진행됩니다.
* Why the current validation may be insufficient: F-3의 `ServiceScopeBar.tsx`처럼 계획에 없는 파일은 마지막에야 드러납니다.
* Suggested verification: `api.d.ts`를 수정하는 Task 직후 `tsc --noEmit`을 실행하는 단계를 추가. 또한 `vitest run`(전체)을 Task 9 마지막에 한 번.
* Expected observable result: 타입 오류 0, 프론트엔드 테스트 전체 통과.

### T-5. 릴리스 환경 선택 UI의 상태 초기화 동작이 계약 테스트로만 검증됨

* Behavior to verify: environment를 바꿨을 때 후보/폼/목록이 초기화되어 다른 환경 데이터가 섞이지 않는다.
* Current verification gap: Task 9 Step 4/5의 검증은 `expect(source).toContain("value: 'qa'")` 같은 **소스 문자열 검사**입니다. 상태 초기화 로직이 실제로 동작하는지는 검증하지 않습니다.
* Why the current validation may be insufficient: 소스 문자열 계약 테스트는 이 저장소의 기존 관례이므로 그 자체가 문제는 아니지만, "환경 전환 시 이전 환경의 scope 후보로 키를 만들어버리는" 버그는 잡지 못합니다. 이는 잘못된 환경의 권한을 가진 키가 발급되는 보안 성격의 실수입니다.
* Suggested verification: 최소한 수동 검증 절차(Task 11)에 "dev → qa 전환 후 scope 후보 목록이 비워지고 재조회되는지" 확인을 추가하거나, 상태 초기화 로직을 순수 함수로 분리해 단위 테스트.
* Expected observable result: 환경 전환 직후 후보 목록이 비고, 새 환경의 active release 기준 후보만 표시됨.

---

## 9. Questions for the Coding Agent

1. Question: `service_owner`와 `service_developer` 외에 `service_operator`, `auditor`의 권한도 이번 변경에서 축소해야 하는가?
   * Why it matters: 계획 Task 8은 `SERVICE_AUDIT_LOG_READ_ROLES`를 `{"auditor"}`로 줄이고 Task 7은 `/audit-logs` 메뉴를 `system_admin` 전용으로 만들어, auditor의 UI 접근이 사라집니다. 사용자 요구사항에는 이 두 역할이 없습니다(S-1, F-11).
   * Where to verify: `src/intent_routing/api/admin.py:1397-1406, 1544-1606`, `tests/integration/test_admin_service_rbac_flow.py:173-240`, `docs/AdminUI_Handbook/v04/PATTERN_KIT.md:201-210`.

2. Question: 폐쇄망 `pilot` environment 배포 경로는 유지 대상인가?
   * Why it matters: `dev/qa/prod` 전용 제약이 `.env.closed-network.example`(`INTENT_ROUTING_ENVIRONMENT=pilot`)과 pilot 스모크 문서 경로를 무효화합니다. 유지한다면 문서·계약 테스트를 이번 계획 범위에 넣어야 하고, 폐기한다면 그 결정을 기록해야 합니다(F-4).
   * Where to verify: `tests/unit/test_closed_network_packaging_contract.py:38-46`, `docs/ops/closed-network-deployment.md:3,73`, `docs/ops/pilot-e2e-smoke.md:26,41`.

3. Question: governed publish 워크플로(`_require_publish_request_access`, `_require_publish_activation_access`)에서 `service_developer`의 권한은 어떻게 되어야 하는가?
   * Why it matters: 계획이 `create_release`/`activate_release`만 owner 전용으로 좁히면, developer가 publish activation 경로로 릴리스를 활성화할 수 있어 "developer는 release를 쓸 수 없다"는 요구사항이 우회됩니다(F-10).
   * Where to verify: `src/intent_routing/api/admin.py:1555-1582`, `admin.py:5960-5999`, `docs/superpowers/plans/2026-07-08-phase2-governed-backend-completion.md`.

4. Question: 인증 이전 단계(preflight)에서 발생하는 런타임 에러 로그의 `environment`는 무엇으로 채우며, UI 환경 필터는 NULL을 포함하는가?
   * Why it matters: "runtime logs는 environment 분리" 요구사항의 실제 만족 여부가 여기서 갈립니다. 필터가 NULL을 제외하면 인증 실패 로그가 조회에서 사라집니다(F-9, A-4).
   * Where to verify: `src/intent_routing/logging/trace.py:94-147`, `src/intent_routing/db/repositories.py:2705-2745`, `frontend/intent-routing-console/src/pages/RuntimeLogs/index.tsx`.

5. Question: 전체 `pytest`/`vitest` 통과가 이번 작업의 완료 기준인가, 아니면 계획이 나열한 파일 집합만인가?
   * Why it matters: F-1/T-3에서 확인했듯 Service 필드 제거는 계획 밖 파일을 광범위하게 깹니다. 완료 기준이 전체 스위트라면 Task 분해와 소요 산정이 크게 달라집니다.
   * Where to verify: CI 워크플로 정의(`grep -rn "pytest" .github/workflows`), `tests/unit/test_ci_workflow_contract.py`.

6. Question: `ALLOWED_RUNTIME_ENVIRONMENTS`를 `.env.example`에 노출할 것인가?
   * Why it matters: `tests/unit/test_env_contract.py:46`이 `.env.example` 정확 일치를 단언하므로, 추가하면 `EXPECTED_LOCAL_ENV`도 함께 바꿔야 합니다. 계획에는 이 단계가 없습니다(F-17, M-2).
   * Where to verify: `tests/unit/test_env_contract.py:12-49`, `.env.example`, `scripts/run_local_dev_stack_macos.sh`.

---

## 10. Recommended Review Order

1. **Blocker 확인 (F-1, F-2, F-3, F-4)** — 이 네 가지는 "계획대로 구현하면 반드시 깨진다"에 해당하므로, 다른 판단보다 먼저 실제 파일에서 확인하세요. 특히 F-1은 Task 분해 자체를 바꿀 수 있습니다.
2. **테스트 헬퍼 전제 검증 (A-1)** — 계획의 모든 Task가 "실패하는 테스트 먼저"로 시작하므로, 스니펫이 실제 헬퍼와 맞지 않으면 각 Task의 첫 단계를 재작성해야 합니다.
3. **요구사항과 범위 대조 (S-1, Q1, Q2, Q3)** — auditor/service_operator, pilot 환경, governed publish는 모두 "요구사항에 없는데 계획이 건드리거나, 요구사항이 있는데 계획이 놓친" 영역입니다. 여기서 범위를 확정한 뒤 Task 7/8/10을 조정하세요.
4. **누락 작업 판단 (M-1 ~ M-6)** — 특히 M-1(seed 스크립트)과 M-2(환경변수 계약)는 F-1/F-17과 연결됩니다.
5. **대안 비교 (O-1, O-2)** — allowlist 검증 시점과 release read 헬퍼 재사용 여부. 둘 다 F-6/F-7/F-13의 결론에 영향을 줍니다.
6. **검증 보완 (T-1 ~ T-5, F-16)** — 특히 T-1(다중 환경 동시 서빙)과 T-2(allowlist 거부)는 이번 변경의 핵심 명제이므로 자동 검증이 없으면 완료 판정이 어렵습니다. F-16(릴리스 활성화 단계)도 여기서 함께 반영하세요.
7. **Minor 반영 여부 결정 (F-12, F-13, F-14, F-15, F-18)** — 동작에 영향이 없거나 작으므로 마지막에 판단하세요.

---

## 11. Coding Agent Decision Record Template

아래 템플릿을 **각 Finding(F-1 ~ F-19)에 대해 복사하여** 사용하세요. 필요하다면 M / A / O / S / T 항목에도 같은 형식을 적용할 수 있습니다.

### Decision for F-{번호}

* Decision: Accepted | Partially accepted | Rejected | Deferred
* Verification performed:
  (실행한 명령과 확인한 파일·라인)
* Evidence found:
  (확인 결과. 검토 문서의 주장이 맞았는지, 틀렸다면 실제 상태는 무엇인지)
* Comparison with the original plan:
  (기존 계획의 판단 근거 vs 검토 의견의 근거)
* Reason for the decision:
* Changes to the plan:
  (수정한 Task/Step, 또는 "변경 없음")
* Remaining uncertainty:

---

## 부록: 이번 검토에서 실제로 확인한 범위

확인함: `src/intent_routing/api/dependencies.py`(전체), `src/intent_routing/api/runtime.py`(주요 구간), `src/intent_routing/api/admin.py`(RBAC 헬퍼 1390-1620, API key 4030-4160, intent-route candidates 4900-4975, release 5990-6210), `src/intent_routing/versions/releases.py`(1-200), `src/intent_routing/logging/trace.py`(60-220), `src/intent_routing/db/models.py`(Service/ApiKey/Release/RuntimeLog), `src/intent_routing/db/repositories.py`(environment 관련 + masked log 구간), `src/intent_routing/config.py`(전체), `alembic/versions/0001,0010,0011`, 프론트엔드 `models/adminSession.ts`, `components/adminShellNavigation.ts`(+테스트), `components/ServiceScopeBar.tsx`, `pages/Services|Releases|ApiKeys`의 environment 참조, `types/api.d.ts`(Service 관련), 테스트 헬퍼 시그니처(`test_release_flow`, `test_admin_runtime_setup_api`, `test_admin_service_rbac_flow`, `test_runtime_api`), 계약 테스트(`test_env_contract`, `test_admin_runtime_setup_contract_docs`, `test_admin_ui_handbook_docs_contract`, `test_closed_network_packaging_contract`, `test_operator_docs_contract`, `test_ci_workflow_contract`), ops 문서 및 `scripts/seed_pilot.py`.

확인하지 않음(따라서 단정하지 않음): 테스트 conftest의 DB 마이그레이션 적용 방식(A-3), `src/intent_routing/main.py`의 앱 생성/예외 핸들러 구조(F-7, F-9의 일부), `src/intent_routing/ops/metrics.py` 내부(F-18), governed publish 엔드포인트의 전체 동작(F-10), `docs/api/openapi-runtime-examples.md` 내용(S-2), 프론트엔드 각 페이지의 런타임 동작(정적 읽기만 수행).
