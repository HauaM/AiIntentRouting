# Handoff: Intent Routing Service — Admin Console v03 (v1+ Design Proposal)

> **중요**: 이 문서는 **v1 이후 Admin Console의 설계 제안서**입니다.
> 현재 프로젝트는 **API-only MVP / Sprint 9 Go reassessment 완료 단계**이며,
> Sprint 9 공식 판정은 **Go**, Admin UI implementation은 **excluded**입니다.
> 각 기능의 구현 가능 여부는 아래 **API 지원 매트릭스**를 기준으로 판단하세요.

---

## Overview

Intent Routing Service는 금융권 폐쇄망 환경에서 Dify/챗봇/내부 시스템이 공통으로 사용하는 Intent Routing API의 운영·감사·배포 콘솔입니다. 사용자 질문에 직접 답하지 않고 `intent`, `route_key`, `decision`(confident/clarify/fallback/off_topic/risk)을 판정하는 FastAPI 백엔드(`/admin/v1/...`)에 붙는 **내부 백오피스**입니다.

대상 역할: `system_admin` / `service_developer` / `service_operator` / `auditor`

---

## About the Design Files

`intent_routing_console_review.html` 은 **디자인 검토용 HTML 레퍼런스**입니다.

- 프로덕션 산출물이 아닙니다. 레이아웃·컴포넌트 선택·색상·업무 흐름 합의용으로만 사용하세요.
- 파일 상단에 검토용 고지 배너가 포함되어 있습니다.
- 폐쇄망 배포 시 외부 CDN 참조(Pretendard 등)가 없어야 합니다 — `SETUP_GUIDE.md` §8 참조.
- 구현 목표: **Ant Design Pro v6 (React + Umi 4 + ProComponents)** 환경에서 재현.

구현 전 반드시 **API contract를 백엔드 팀과 확정**하세요. 특히 Phase 2 기능들은 아직 백엔드 설계가 확정되지 않았습니다.

---

## 구현 단계 (Phase) 분리

### Phase 0 — Read-first Console *(가장 먼저 구현 권장)*
운영자가 현황 파악과 문제 추적을 할 수 있는 최소 콘솔. **위험한 쓰기 작업 제외.**

| 화면 | 핵심 기능 | 현재 API 지원 |
|---|---|---|
| Dashboard | 요청수·decision 분포·latency 메트릭 | ✅ `/runtime-metrics` |
| Runtime Logs | masked query·decision·trace 조회 | ✅ `/runtime-logs` |
| Audit Logs | 이벤트 이력 조회 (읽기 전용) | ✅ `/audit-logs` |
| Intent Catalog | intent 목록 조회, 선택 행 기반 상세 표시 | ✅ `/intents` GET |

### Phase 1 — Current API Write Console
현재 백엔드가 이미 제공하는 쓰기 기능만 연결. **모든 destructive action에 `Modal.confirm` + audit visibility 적용.**

| 화면 | 핵심 기능 | 현재 API 지원 |
|---|---|---|
| Intent Catalog | intent 생성/수정 | ✅ POST/PATCH `/intents` |
| Examples | example 등록 / approve | ✅ POST example + PATCH `:approve` |
| Policy Versions | policy version 생성 | ✅ POST `/policy-versions` |
| Catalog Versions | catalog version 생성 | ✅ POST `/catalog-versions` |
| CSV Test Runs | test run 생성·결과 조회 | ✅ POST `/test-runs` |
| Releases | release 생성·activate·rollback | ✅ system_admin 전용 |
| API Keys | key 생성·revoke | ✅ `/admin/v1/api-keys` |

### Phase 2 — Governed Workflow Console *(Future backend required)*
아직 백엔드 계약이 필요한 고급 승인 플로우.

| 기능 | 상태 |
|---|---|
| Publish 요청/pending/승인/반려 | 🔮 Future backend required |
| raw query 2인 승인 대기열 | 🔮 Future backend required |
| 시한부 raw query 열람 토큰 | 🔮 Future backend required |
| Release diff 및 승인 체계 | 🔮 Future backend required |
| CSV export | 🔮 Future backend required |
| 서버 페이지네이션 / 복합 필터 | 🔮 Future backend required |
| Live polling (Runtime Logs) | 🔮 Future backend required |
| Example 반려 (사유 입력) | 🔮 Future backend required |

---

## Current API / Future Backend Required 매트릭스

| 기능 | 현재 API 지원 | Phase | 비고 |
|---|---|---|---|
| runtime-metrics 조회 | ✅ | 0 | `/runtime-metrics` |
| runtime-logs 조회 | ✅ | 0 | masked query 서버 처리 |
| audit-logs 조회 | ✅ | 0 | 읽기 전용 |
| intent 목록 조회 | ✅ | 0 | 응답 배열에서 선택 행 상세 표시 |
| intent 개별 GET | 🔮 | 2 | 현재 `GET /intents/{intent_id}` 없음 |
| intent 생성/수정 | ✅ | 1 | |
| example 등록 | ✅ | 1 | |
| example approve | ✅ | 1 | `PATCH ...:approve`, 현재 system_admin/service_developer |
| policy-version 생성 | ✅ | 1 | |
| catalog-version 생성 | ✅ | 1 | |
| test-run 생성/조회 | ✅ | 1 | |
| release 생성 | ✅ | 1 | 현재 system_admin 전용 |
| release activate | ✅ | 1 | 현재 system_admin 전용, `:activate` · Modal.confirm 필수 |
| release rollback | ✅ | 1 | 현재 system_admin 전용, `:rollback` · Modal.confirm 필수 |
| API key 생성/revoke | ✅ | 1 | revoke · Modal.confirm 필수 |
| raw query audited decrypt | ✅ | 1 | 현재 system_admin/auditor 직접 감사 조회 API 있음. UI 기본 노출 금지 |
| publish pending 상태 | 🔮 | 2 | 백엔드 상태 모델 미확정 |
| example 반려 | 🔮 | 2 | |
| 2인 승인 대기열 | 🔮 | 2 | |
| 시한부 raw query token | 🔮 | 2 | |
| release diff 뷰 | 🔮 | 2 | |
| CSV export | 🔮 | 2 | |
| 서버 페이지네이션 | 🔮 | 2 | 현재는 클라이언트 페이지네이션 |
| 복합 필터 | 🔮 | 2 | |
| live polling | 🔮 | 2 | |

---

## Fidelity

**Design Proposal — 확정 전 검토용.**
색상·컴포넌트 선택·레이아웃 방향은 합의된 상태이지만, 각 화면의 API 계약(요청/응답 스키마, 페이지네이션 방식, 권한 헤더)은 구현 전 백엔드 팀과 별도로 확정해야 합니다.

---

## Screens / Views

### 1. Dashboard *(Phase 0)*
- **목적**: 운영 현황 한눈에 파악 (24h 요청량·decision 분포·latency·top route_key·error)
- **API**: `GET /admin/v1/services/{service_id}/runtime-metrics?window_hours=24`
- **레이아웃**: ProLayout 풀셸 (사이드바 178px + 헤더 44px + 본문 `#F4F6F8`)
- **상단 우측 필터**: service 선택 + 기간 선택(1h/24h/7d → `window_hours`). env 전역 필터는 🔮 Future backend required.
- **컴포넌트**: Statistic 타일 4개 / Decision 분포 스택바 / Latency 차트(`@ant-design/charts`) / Top route_key 테이블(최대 10행)
- **권한**: 현재 API 기준 system_admin 또는 scoped service_operator 조회. auditor/developer 대시보드 접근은 Phase 2 권한 확장 후보.

### 2. Intent Catalog — 목록 *(Phase 0 조회 / Phase 1 편집)*
- **목적**: intent 조회 및 CRUD 진입점
- **API**: `GET /admin/v1/services/{service_id}/intents`
- **응답 형태**: `IntentResponse[]` 배열. 서버 페이지네이션 없음. Phase 0/1에서는 클라이언트 검색·페이지네이션 사용.
- **ProTable 컬럼**: intent_id(mono) / 이름·설명 / route_key(Tag) / kw(inc/exc count) / ex(examples count) / status Tag / 작업
- **status Tag 색상**: Active=green(`#2F8F5B`) / Draft=orange(`#D4920B`) / Deprecated=gray
- **Phase 1 추가**: `+ Intent 추가` 버튼, 편집 링크 (service_developer 권한)
- **권한**: 현재 API 기준 system_admin 또는 scoped service_developer 조회·편집. service_operator/auditor catalog read는 Phase 2 권한 확장 후보.

### 3. Intent Catalog — 상세/편집 *(Phase 1)*
- **목적**: intent 속성 편집
- **API**: 상세 표시는 목록 응답의 선택 행 데이터를 사용. 수정은 `PATCH /admin/v1/services/{service_id}/intents/{intent_id}`.
- **API gap**: `GET /admin/v1/services/{service_id}/intents/{intent_id}` 개별 조회는 현재 없음(🔮 Future backend required).
- **헤더 액션**: `임시저장` (PATCH draft) / `검토 요청` → Phase 2(🔮 pending 상태 미지원)
- **ProForm 필드**: intent_id(disabled) / domain / display_name / description / route_key(Select) / status / include keywords(mode=tags) / exclude keywords(mode=tags)
- **Future 필드**: threshold_preset, risk_policy_override는 intent API 필드가 아니므로 Policy Version 화면 또는 Phase 2에서 별도 설계.
- **우측 메타 카드**: created_by, updated_by, created_at, updated_at 등 현재 응답 필드 우선. 버전·embedding 상태·연결 release는 🔮 Future/derived data.
- **권한**: 현재 API 기준 system_admin 또는 scoped service_developer 편집

### 4. Examples & Approval *(Phase 1 approve / Phase 2 반려)*
- **목적**: example 등록 및 approve
- **API**:
  - `GET /admin/v1/services/{service_id}/intents/{intent_id}/examples`
  - `POST /admin/v1/services/{service_id}/intents/{intent_id}/examples`
  - `PATCH /admin/v1/services/{service_id}/examples/{example_id}:approve`
- **Steps**: 등록 → 임베딩 생성 → 검토 → 승인
- **ProTable 컬럼**: 체크박스 / example 텍스트 / type(positive/negative Tag) / intent / embedding 상태 / 작업
- **일괄 approve**: 현재 bulk endpoint 없음. 선택 항목별 `PATCH ...:approve`를 순차 실행하거나 bulk endpoint를 Phase 2로 설계.
- **반려**: 🔮 Future backend required (사유 입력 엔드포인트 미확정)
- **권한**: 현재 API 기준 system_admin 또는 scoped service_developer 등록·approve. auditor approve는 Governed Workflow(Phase 2) 후보.

### 5. Releases *(Phase 1)*
- **목적**: release 생성·activate·rollback
- **API**:
  - `GET/POST /admin/v1/services/{service_id}/releases`
  - `POST /admin/v1/services/{service_id}/releases/{release_version}:activate`
  - `POST /admin/v1/services/{service_id}/releases/{release_version}:rollback`
- **화면 구성**: 활성 release 배너 + 생성 Steps(구성 선택→검증→활성화) + 이력 ProTable
- **Activate**: `Modal.confirm` 필수 (현 활성 대체 영향 명시)
- **Rollback**: `Modal.confirm` 필수 (이전 버전 명시)
- **Release diff**: 🔮 Future backend required
- **권한**: 현재 API 기준 create/activate/rollback은 system_admin 전용. service_developer의 release 생성 요청, auditor 승인/activate는 Phase 2 후보.

### 6. Runtime Logs *(Phase 0)*
- **목적**: API 호출 로그 조회 (query 기본 마스킹)
- **API**: `GET /admin/v1/services/{service_id}/runtime-logs?limit=100`
- **상세 API**: `GET /admin/v1/services/{service_id}/runtime-logs/{trace_id}`
- **필터**: 현재 서버 필터는 `limit` 중심. 기간/decision/service/trace 검색은 Phase 0 클라이언트 필터 또는 🔮 Future server filter.
- **ProTable 컬럼**: time / trace_id(mono) / `query_masked` / route_key / decision Tag / latency(ms)
- **decision Tag 색상**: confident=green / clarify=orange / fallback=blue-gray / off_topic=gray / risk=red
- **risk 행**: background `#FDF6F5`
- **행 클릭**: Drawer로 trace 상세
- **raw query 원문**: 현재 `POST ...:decrypt-raw-query` audited direct API는 있음(system_admin/auditor). UI 기본 노출 금지. 2인 승인 + 시한부 토큰 플로우는 🔮 Future backend required.
- **live polling**: 🔮 Future backend required
- **권한**: 현재 API 기준 system_admin / scoped service_operator / scoped auditor 조회

### 7. Audit Logs *(Phase 0)*
- **목적**: 중요 작업 이벤트 기록 조회 (읽기 전용 원칙)
- **API**: `GET /admin/v1/services/{service_id}/audit-logs`
- **중요**: 수정/삭제 버튼 없음. ProTable `toolBarRender={() => false}`.
- **ProTable 컬럼**: time / actor(이름·역할) / action(mono 코드) / target / result Tag
- **상단 배너**: raw query 조회 승인 대기 — 🔮 Future backend required
- **하단 고지**: append-only · 보존 7년 · CSV export(🔮)
- **현재 event_type 예**: `release.activated` / `api_key.revoked` / `catalog_version.created` / `example.approved` / `raw_query.viewed`
- **권한**: 현재 API 기준 system_admin/auditor 읽기. Audit Logs 화면 자체의 승인/거부 편집은 Phase 2 후보.

---

## Authentication Model

현재 Admin API 인증 헤더:

```
X-Admin-Token: <admin_token>
X-Actor-Id: <actor_user_id>
X-Actor-Roles: system_admin,service_developer   (쉼표 구분 복수 가능)
X-Service-Scope: <service_id>
```

> **주의**: 이전 문서의 `Authorization: Bearer` + `access_token` 패턴은 현재 Admin API와 맞지 않습니다. 위 헤더를 사용하세요.

역할별 접근:

| 역할 | access.ts 키 | 주요 권한 |
|---|---|---|
| `system_admin` | `isAdmin` | Services, API Keys, activate/rollback |
| `service_developer` | `isDeveloper` | 담당 service catalog CRUD, examples, test runs, release 목록 조회 |
| `service_operator` | `isOperator` | Runtime Logs / Runtime Metrics 조회 |
| `auditor` | `isAuditor` | Audit Logs 조회, Runtime Logs 조회, raw query audited decrypt |

---

## Interactions & Behavior

### Destructive Action 원칙 (Phase 1~2 공통)
- **release activate/rollback**: `Modal.confirm` + 영향 범위(현 활성 release 명시) 필수
- **API key revoke**: `Modal.confirm` + 키 ID·연결 서비스 명시 필수
- **example 일괄 approve**: `Modal.confirm` + 대상 수·임베딩 영향 명시

### 네비게이션
- ProLayout `fixedHeader: true`, `fixSiderbar: true`
- 사이드바: 178px(확장) ↔ 50px(아이콘 레일)
- 전역 `service_id` Context → `/services/{service_id}/...` 경로와 `X-Service-Scope` 헤더에 반영
- env Context는 현재 service/environment 선택 UI로 표현하고, 서버 전역 `env` 쿼리는 Phase 2에서 확정

### 에러/로딩
- 테이블 로딩: ProTable 내장 skeleton
- 빈 결과: `Empty` (필터 적용 시 "조건을 변경해보세요")
- API 오류: `message.error()` 토스트

---

## Design Tokens

```typescript
export const theme = {
  token: {
    colorPrimary:    '#1D5A96',
    colorLink:       '#1D5A96',
    colorSuccess:    '#2F8F5B',
    colorWarning:    '#D4920B',
    colorError:      '#C0392B',
    colorTextBase:   '#1C2733',
    colorBgContainer:'#FFFFFF',
    colorBgLayout:   '#F4F6F8',
    borderRadius:    6,
    fontFamily:      "'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontFamilyCode:  "'JetBrains Mono', ui-monospace, monospace",
  },
  components: {
    Layout:  { siderBg: '#0D2438' },
    Menu:    { darkItemBg: '#0D2438', darkItemSelectedBg: 'rgba(58,127,192,0.22)', darkItemSelectedColor: '#FFFFFF', darkItemColor: '#AEBCCD' },
    Table:   { headerBg: '#F7F9FB', headerColor: '#64748B', rowHoverBg: '#F0F5FA' },
  },
};

export const decisionColors = {
  confident: { bg: '#E8F5EE', color: '#1F7A4D' },
  clarify:   { bg: '#FBF2E0', color: '#B97A09' },
  fallback:  { bg: '#EEF1F4', color: '#5A7A99' },
  off_topic: { bg: '#EEF1F4', color: '#64748B' },
  risk:      { bg: '#FBEAEA', color: '#C0392B' },
};
```

---

## Assets

- **폰트**: `@orioncactus/pretendard` npm 로컬 설치. **CDN 사용 금지(폐쇄망).**
- **아이콘**: `@ant-design/icons` 번들 포함. 외부 CDN 참조 없음.
- **차트**: `@ant-design/charts` 로컬 설치. ECharts 런타임 CDN 로드 설정 제거 확인.

---

## Files

| 파일 | 설명 |
|---|---|
| `intent_routing_console_review.html` | 디자인 검토용 HTML (7화면 하이파이 와이어프레임). **운영 배포 산출물 아님.** |
| `README.md` | 이 문서 — 설계 합의, 화면 스펙, Phase 분리, API 매트릭스 |
| `SETUP_GUIDE.md` | Ant Design Pro v6 셋업 방법론, 실제 API 경로, 코드 패턴 |
