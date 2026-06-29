# Handoff: Intent Routing Service — 관리 콘솔 (Admin Console)

## Overview

Intent Routing Service는 금융권 폐쇄망 환경에서 Dify/챗봇/내부 시스템이 공통으로 사용하는 Intent Routing API의 운영·감사·배포 콘솔입니다.
사용자 질문에 직접 답하지 않고 `intent`, `route_key`, `decision`(confident/clarify/fallback/off_topic/risk)을 판정하는 FastAPI 백엔드에 붙는 **내부 백오피스**입니다.

대상 역할: 시스템관리자 / 서비스개발자 / 운영자 / 감사·보안

---

## About the Design Files

`intent_routing_console_review.html` 은 **디자인 검토용 HTML 레퍼런스**입니다.
실제 프로덕션에 그대로 복사하는 파일이 아니며, 레이아웃·컴포넌트 선택·색상·업무 흐름의 **합의 기준**으로 사용하세요.

구현 목표: 이 디자인을 **Ant Design Pro v6 (React + Umi 4 + ProComponents)** 환경에서 재현합니다.
구체적인 셋업 방법·디렉터리 구조·코드 패턴은 `SETUP_GUIDE.md`를 참조하세요.

---

## Fidelity

**High-fidelity.** 색상, 타이포, 컴포넌트 선택, 컬럼 구성, 태그 색상, 마스킹 패턴, 권한 가시성이 모두 확정된 상태입니다.
아래 Design Tokens 섹션의 수치를 그대로 사용하세요.

---

## Screens / Views

### 1. Dashboard
- **목적**: 운영 현황 한눈에 파악 (24h 요청량·decision 분포·latency·top route_key·error)
- **레이아웃**: ProLayout 풀셸 (사이드바 178px + 헤더 44px + 본문 gray background `#F4F6F8`)
- **상단 우측 필터**: env 선택(prod/stg) + 기간 선택(1h/24h/7d) → 모든 메트릭에 영향
- **컴포넌트 구성**:
  - 스탯 타일 4개 (ProCard + Statistic): 총 요청 / p95 Latency / confident 비율 / error count
  - Decision 분포: 가로 스택 바 (flex + 색상 구간) + 범례 chip. 색상은 Design Tokens 참조
  - Latency 추이: @ant-design/charts `Line` 또는 `Column` (p50/p95 두 계열), 높이 120px
  - Top route_key 테이블: ProTable, 컬럼 [route_key, 요청수, confident%, p95], 페이지네이션 없음(최대 10행)
- **권한**: 전 역할 읽기

### 2. Intent Catalog — 목록
- **목적**: intent CRUD 진입점
- **레이아웃**: ProLayout 풀셸
- **헤더 액션**: `+ Intent 추가` (primary) / `CSV로 가져오기` (default)
- **필터 툴바**: intent_id/name 검색 input + route_key Select + status Select(Active/Draft/Deprecated) + 컬럼 설정 버튼
- **ProTable 컬럼**:
  | 컬럼 | 비고 |
  |---|---|
  | intent_id | monospace, 클릭 → 상세 |
  | 이름/설명 | 2줄 결합 셀 |
  | route_key | monospace blue `#1D5A96` Tag |
  | kw (inc/exc) | "12/3" 텍스트 |
  | ex (examples) | 숫자 |
  | status | Tag: Active=green / Draft=orange / Deprecated=gray |
  | 작업 | 편집 / 복제 링크 |
- **서버 페이지네이션**: request 함수로 FastAPI `/api/v1/intents?page=&size=&status=&route_key=` 연결
- **권한**: 시스템관리자·운영자·감사 읽기 / 서비스개발자 편집

### 3. Intent Catalog — 상세/편집
- **목적**: intent 속성 편집 후 검토 요청(Publish)
- **레이아웃**: 압축 아이콘 레일(50px 다크 사이드바) + 헤더(breadcrumb + 상태 Tag + 액션) + 2컬럼 본문
- **헤더 액션**: `임시저장` (default) / `검토 요청 (Publish)` (primary) → Publish 시 승인 플로우 진입
- **좌측 ProForm 필드**:
  - intent_id (disabled, monospace)
  - route_key (Select)
  - 설명 (TextArea)
  - include keywords (Select mode="tags", blue chip)
  - exclude keywords (Select mode="tags", red chip)
  - threshold preset (Select)
  - risk policy override (Select: 상속/override)
- **우측 ProCard (메타)**:
  - 버전, embedding 상태, 연결 release, 최종 수정자
  - 최근 테스트 pass rate (Progress bar)
- **권한**: 서비스개발자 편집 / 나머지 읽기

### 4. Examples & Approval
- **목적**: positive/negative example 등록 및 embedding 승인
- **레이아웃**: 압축 레일 + Steps(등록→임베딩 생성→검토→승인) + 체크박스 ProTable + 일괄 승인 버튼
- **Steps**: 현재 단계 highlight. `등록`·`임베딩 생성`은 완료(✓ green), `검토`는 진행중(blue), `승인`은 미완(gray)
- **ProTable 컬럼**: 체크박스 / example 텍스트 / type(positive=green/negative=red Tag) / intent / embedding 상태 / 작업(승인·반려)
- **일괄 승인**: 체크박스 선택 후 `선택 승인 (N)` 버튼 → `Modal.confirm`으로 영향 범위(임베딩 재생성 대상 수) 요약 → 확인
- **반려**: 사유 입력 필수 (`Modal` + TextArea)
- **권한**: 서비스개발자 편집/등록 / 감사·보안 승인 / 나머지 읽기

### 5. Releases
- **목적**: catalog·policy·test-run 기반 release 생성 및 prod 활성화
- **레이아웃**: 압축 레일 + 활성 release 배너 + 신규 생성 Steps 카드 + 이력 ProTable
- **활성 배너**: green dot pulse + release_id (monospace) + 구성(catalog vN·policy vM·test-run #N) + 활성화 일시/담당자. 읽기 전용.
- **생성 Steps 카드**: 구성 선택 → 검증(test-run 연결) → 활성화. 각 단계 완료 시 다음 버튼 활성화.
  - 구성 선택: catalog 버전 Select + policy 버전 Select + diff 요약(vs 현 활성)
  - 검증: test-run Select + pass rate / fail 수 표시
  - 활성화: `prod 활성화` 버튼 → `Modal.confirm` (영향: 현 활성 대체, 롤백 방법 안내)
- **이력 ProTable**: release_id / 구성 / status Tag(active/staged/archived/rolled-back) / pass rate / 활성화 담당자·일시
- **권한**: 서비스개발자 생성 / 시스템관리자·감사 활성화 승인

### 6. Runtime Logs
- **목적**: 실시간 API 호출 로그 조회 (query는 기본 마스킹)
- **레이아웃**: 압축 레일 + 필터 툴바 + ProTable
- **필터**: 기간 DateRangePicker + service Select + decision 다중 Select + trace_id 검색(monospace input)
- **ProTable 컬럼**: time / trace_id(monospace, 일부만 표시) / masked query(● 기호) / route_key / decision Tag / latency(ms)
  - `decision` Tag 색상: confident=green / clarify=orange / fallback=blue-gray / off_topic=gray / risk=red
  - risk 행: 전체 행 background `#FDF6F5`
- **행 클릭**: `Drawer`로 trace 상세(intent·confidence score·policy 적용 내역·embedding 거리)
- **raw query**: 기본 마스킹. 원문 조회는 Audit Logs의 2인 승인 후 시한부 열람만 허용. 테이블 하단에 고지 텍스트 필수.
- **권한**: 운영자 조회·필터 / 나머지 읽기 (raw query 열람은 감사 승인 후)

### 7. Audit Logs
- **목적**: 모든 중요 작업 이벤트 기록 조회 + raw query 조회 2인 승인
- **레이아웃**: 압축 레일 + 승인 대기 배너 + ProTable
- **승인 대기 배너**: 조회 요청자·trace_id·사유를 노란 배너로 표시 + `승인`(green) / `거부`(red outline) 버튼. 2인 승인 필수(현재 로그인 감사자 1인 + 별도 확인자).
- **ProTable**: 수정·삭제 없음(읽기 전용). 컬럼: time / actor(이름·역할) / action(monospace 코드) / target / result Tag
  - 중요 action 코드: `release.activate` / `apikey.revoke` / `rawquery.view.approve` / `catalog.publish`
  - result: success=green / pending=blue / revoked=red / approved=green
- **하단 고지**: append-only · 해시 체인 검증 · 보존 7년 · CSV 내보내기
- **필터**: actor / action 코드 검색 / 기간 DateRangePicker
- **권한**: 감사·보안 편집(승인/거부) / 나머지 읽기. 시스템관리자도 자신의 action 조회 가능.

---

## Interactions & Behavior

### 공통 플로우
- **되돌릴 수 없는 작업** (release 활성화, key revoke, example 일괄 승인): 항상 `Modal.confirm` + 영향 범위 요약. Popconfirm은 단순 삭제에만.
- **폼 저장**: `임시저장`(로컬 draft, API PATCH) → `검토 요청`(상태 draft→pending, 승인자 알림)
- **승인 반려**: 사유 필수 입력 + 입력 없으면 확인 버튼 disabled
- **Live 로그**: Runtime Logs에서 `⏸ Live` 토글로 자동 폴링(3초) on/off

### 네비게이션
- ProLayout `fixedHeader: true`, `fixSiderbar: true`
- 사이드바 접기/펼치기: 아이콘 레일(50px) ↔ 전체(178px)
- 현재 환경(env) 전환: 헤더 Select로 전역 Context 변경 → 모든 API 요청에 `?env=prod|stg` 반영

### 에러/로딩 상태
- 테이블 로딩: ProTable 내장 skeleton
- 빈 결과: AntD `Empty` 컴포넌트 (필터 적용 시: "조건을 변경해보세요")
- API 오류: `message.error()` 토스트

---

## State Management

```
initialState (getInitialState)
  ├── currentUser: { id, name, role: 'admin'|'developer'|'operator'|'auditor' }
  ├── currentEnv: 'prod' | 'stg'
  └── currentRelease: { release_id, catalog_version, policy_version }

페이지별 로컬 상태 (useState/useModel)
  ├── Dashboard: metricsData, dateRange, envFilter
  ├── IntentCatalog: tableParams, selectedRows
  ├── Examples: pendingList, selectedExamples, approvalModal
  └── Releases: activeRelease, draftRelease, createStep
```

React Query (`@tanstack/react-query`) 또는 Umi의 `useRequest`로 서버 상태 관리.
전역 env 변경 시 React Query `invalidateQueries(['*'])` 호출로 전체 캐시 무효화.

---

## Design Tokens

```typescript
// src/theme.ts
export const theme = {
  token: {
    colorPrimary:    '#1D5A96',   // 딥 네이비 — 버튼, 링크, 선택 상태
    colorLink:       '#1D5A96',
    colorSuccess:    '#2F8F5B',   // confident, Active, success
    colorWarning:    '#D4920B',   // clarify, Draft, warning
    colorError:      '#C0392B',   // risk, error, revoke
    colorTextBase:   '#1C2733',
    colorBgContainer:'#FFFFFF',
    colorBgLayout:   '#F4F6F8',
    borderRadius:    6,
    fontFamily:      "'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontFamilyCode:  "'JetBrains Mono', 'Fira Code', ui-monospace, monospace",
  },
  components: {
    Layout: {
      siderBg: '#0D2438',        // 사이드바 배경
    },
    Menu: {
      darkItemBg:         '#0D2438',
      darkSubMenuItemBg:  '#091d2e',
      darkItemSelectedBg: 'rgba(58,127,192,0.20)',
      darkItemSelectedColor: '#FFFFFF',
    },
  },
};

// decision tag 색상
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

- **폰트**: Pretendard — 폐쇄망이므로 npm 패키지(`@orioncactus/pretendard`) 로컬 설치 후 `global.css`에서 `@font-face` 등록. CDN 사용 금지.
- **아이콘**: `@ant-design/icons` 번들 사용. 외부 icon CDN 참조 없음.
- **차트**: `@ant-design/charts` 로컬 설치.
- **이미지/로고**: 별도 없음. 사이드바 상단 로고는 서비스명 텍스트 + 작은 accent 컬러 박스로 구성.

---

## Files

| 파일 | 설명 |
|---|---|
| `intent_routing_console_review.html` | 하이파이 디자인 검토 레퍼런스 (7화면 와이어프레임, IA, 컴포넌트 전략, 색상 팔레트 포함) |
| `README.md` | 이 문서 |
| `SETUP_GUIDE.md` | Ant Design Pro v6 실제 셋업 방법론, 디렉터리 구조, 코드 패턴, FastAPI 연동 방법 |
