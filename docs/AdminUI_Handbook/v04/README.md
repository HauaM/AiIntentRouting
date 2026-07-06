# Handoff: Intent Routing Service — Admin Console v04 Pattern Kit

> **중요**: v04는 프로덕션 Admin UI가 아니라 **Sprint 9 기준 UI/UX pattern kit**입니다.
> 현재 프로젝트는 API-only MVP이며 Sprint 9 공식 판정은 **Go**입니다.
> Sprint 9에서 Admin UI implementation은 **excluded**였으므로, 이 폴더의 예시는 다음 UI 구현 sprint를 위한 기준 컴포넌트입니다.

## Purpose

v03는 설계 판단과 API 매트릭스 중심 문서입니다. v04는 그 판단을 실제 구현자가 반복 사용할 수 있도록 레이아웃, 데이터 패칭, 테이블, 위험 작업, Future 기능 처리 패턴으로 압축합니다.

> **Auth update**: PR #22 이후 일반 Admin UI 요청은 account login,
> `irt_admin_session` HttpOnly cookie, `/auth/me`, `/me/services`를 기준으로
> 동작합니다. `X-Admin-Token`, `X-Actor-*`, `X-Service-Scope` 헤더는 일반
> 브라우저 UI 인증 방식이 아닙니다.

## Use This Order

1. `PATTERN_KIT.md`에서 Sprint 9 상태, phase, 금지 패턴을 확인합니다.
2. `SETUP_GUIDE.md`의 login/session cookie 설정을 먼저 적용합니다.
3. `examples/adminServices.ts`의 API 함수 패턴을 참고하되, 인증은 `withCredentials`와 서버 세션에 맡깁니다.
4. `examples/AdminShell.tsx`와 `examples/ServiceScopeBar.tsx`로 기본 화면 골격을 잡습니다.
5. Phase 0 화면은 `IntentCatalogTable`, `RuntimeLogsTable`, `AuditLogsTable` 순서로 구현합니다.
6. Phase 1 쓰기 액션은 서버에서 받은 service roles 기준으로 노출하고 `ConfirmActionButton`을 통해서만 연결합니다.
7. Phase 2 기능은 `FutureFeatureNotice`로 비활성 처리하고 가짜 백엔드 상태를 만들지 않습니다.

## Included Examples

| file | purpose |
|---|---|
| `examples/adminServices.ts` | Umi `request` 기반 Admin API service 함수 |
| `examples/AdminShell.tsx` | ProLayout shell, Sprint 9 상태 배너, service scope bar |
| `examples/ServiceScopeBar.tsx` | service/environment/actor 상태 표시와 전환 UI |
| `examples/IntentCatalogTable.tsx` | 현재 배열 응답 API 기반 ProTable 목록 |
| `examples/RuntimeLogsTable.tsx` | masked query, risk row, drawer 상세 패턴 |
| `examples/AuditLogsTable.tsx` | read-only audit table + append-only 고지 |
| `examples/ConfirmActionButton.tsx` | destructive action 공통 confirm 버튼 |
| `examples/FutureFeatureNotice.tsx` | Phase 2 future 기능 비활성 안내 |

## Non-Negotiables

- React Query를 사용하지 않습니다.
- `Authorization: Bearer`를 사용하지 않습니다.
- 일반 Admin UI에서 `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`, `X-Service-Scope`를 주입하지 않습니다.
- raw query 원문은 기본 노출하지 않습니다.
- Audit Logs에는 수정/삭제 액션을 만들지 않습니다.
- 서버 페이지네이션, 복합 필터, live polling, publish approval, two-person raw query approval은 Phase 2 future backend입니다.
