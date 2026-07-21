# Task 4 Report: Frontend Route, Services, And Helpers

## 변경 파일

- `frontend/intent-routing-console/config/config.ts`
  - `/permission-management` 라우트를 추가했습니다.
- `frontend/intent-routing-console/src/components/AdminShell.tsx`
  - 좌측 메뉴에 `권한관리` 항목과 `SafetyOutlined` 아이콘을 추가했습니다.
- `frontend/intent-routing-console/src/types/api.d.ts`
  - Permission Management Admin 사용자 요약, Service 역할 요약, 위험 finding, query param 타입을 추가했습니다.
  - `API.AuditLog.service_id`를 백엔드 응답에 맞춰 `string | null`로 수정했습니다.
- `frontend/intent-routing-console/src/services/adminServices.ts`
  - `listPermissionAdminUsers`
  - `listPermissionServiceRoles`
  - `listPermissionAuditLogs`
  - `listPermissionRiskFindings`
- `frontend/intent-routing-console/src/services/adminServices.test.ts`
  - Permission Management 서비스 함수가 GET과 query params만 사용하는지 검증하는 테스트를 추가했습니다.
- `frontend/intent-routing-console/src/pages/PermissionManagement/permissionManagement.ts`
  - 탭 키, 접근 가드, 위험도 색상, 역할 라벨, row key helper를 추가했습니다.
- `frontend/intent-routing-console/src/pages/PermissionManagement/permissionManagement.test.ts`
  - 접근 가드, 위험도 색상, 역할 라벨, 탭 키, row key helper 테스트를 추가했습니다.

## 테스트 결과

- RED 확인:
  - `pnpm vitest run src/services/adminServices.test.ts src/pages/PermissionManagement/permissionManagement.test.ts`
  - 기대한 실패 확인: `listPermissionAdminUsers is not a function`, `./permissionManagement` 모듈 부재.
- GREEN 확인:
  - `pnpm vitest run src/services/adminServices.test.ts src/pages/PermissionManagement/permissionManagement.test.ts`
  - 결과: 2개 파일, 22개 테스트 통과.
- Typecheck:
  - `pnpm run typecheck`
  - 결과: 실패.
  - 원인: Umi route setup 단계에서 `./PermissionManagement` 페이지 컴포넌트를 찾지 못함. 이번 Task 4는 실제 UI 페이지 구현(Task 5)을 제외하므로 `index.tsx`는 만들지 않았습니다.
- 금지 패턴 검색:
  - 지정된 금지 구현 패턴 검색 결과 매치 없음.

## 남은 리스크

- `/permission-management` 라우트는 추가되었지만 실제 페이지 컴포넌트는 Task 5 범위라 아직 없습니다.
- Task 5에서 `frontend/intent-routing-console/src/pages/PermissionManagement/index.tsx`가 추가되기 전까지 `pnpm run typecheck`는 Umi route resolve 단계에서 실패합니다.
