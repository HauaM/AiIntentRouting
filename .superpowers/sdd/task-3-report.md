# Task 3 Report: Backend Permission Audit And Risk APIs

## Status

- 완료
- Branch: `codex/central-iam-permission-management`
- Commit: pending at report write time

## Summary

- `GET /admin/v1/permission-management/audit-logs` 추가
  - `event_group`, `event_type`, `actor_id`, `target_id`, `service_id`, `limit` 필터 지원
  - `admin_user` 및 `service_membership` event group은 task brief의 명시 event type 목록으로 필터링
  - 기존 `safe_audit_log_item(...)`과 `AuditLogResponse`를 재사용해 `before_state`/`after_state`와 secret metadata를 응답에서 제외
- `GET /admin/v1/permission-management/risk-findings` 추가
  - 기존 admin user summary/risk flag 산출 기준을 재사용
  - baseline categories:
    - `linked_inactive_organization_user`
    - `disabled_admin_has_service_roles`
    - `active_admin_without_roles`
    - `unlinked_admin_user`
    - `single_active_system_admin`
- 모든 신규 endpoint는 `require_admin_session_context` -> `admin_context_from_session_record` -> `_require_system_admin(context)` 흐름을 사용
- schema/migration 추가 없음

## Changed Files

- `src/intent_routing/api/admin.py`
  - `PermissionRiskFindingResponse` 추가
  - permission audit/risk endpoint 추가
  - 중앙 audit API에서 service-less admin audit log를 반환할 수 있도록 `AuditLogResponse.service_id`를 nullable로 확장
- `src/intent_routing/db/repositories.py`
  - `list_permission_audit_logs(...)` 추가
  - `list_permission_risk_findings()` 추가
  - Task 2 summary record 생성 경로를 risk finding 산출에 재사용하도록 private helper 분리
- `tests/integration/test_permission_management_api.py`
  - audit logs system_admin 권한, event group 필터, sanitized response 테스트 추가
  - risk findings baseline category 및 deterministic finding_id 테스트 추가
  - `single_active_system_admin` 검증을 위해 기존 `system_admin` role rows를 테스트 중 백업/복원

## RED Evidence

Command:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/integration/test_permission_management_api.py -q
```

Result before implementation:

```text
3 failed, 4 passed, 1 warning in 3.01s
```

Expected failures:

- `test_permission_management_audit_logs_requires_system_admin_without_db`: expected 403, got 404
- `test_permission_management_audit_logs_filter_groups_and_sanitize_states`: expected 200, got 404
- `test_permission_management_risk_findings_returns_baseline_findings`: expected 200, got 404

## GREEN Evidence

Command:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/integration/test_permission_management_api.py -q
```

Result after implementation:

```text
7 passed, 1 warning in 2.99s
```

## Lint Evidence

Command:

```bash
uv run ruff check src/intent_routing/api/admin.py src/intent_routing/db/repositories.py tests/integration/test_permission_management_api.py
```

Result:

```text
All checks passed!
```

## Concerns / Remaining Risks

- `AuditLogResponse.service_id` is now nullable because admin user audit events are intentionally service-less. Existing service-scoped audit API still returns service IDs for service logs.
- The risk findings endpoint is unpaginated by brief. It scans admin users and their roles to derive findings from existing tables.
- The integration test temporarily removes and restores existing `system_admin` role rows to make `single_active_system_admin` deterministic; cleanup restores captured rows in `finally`.
- Test output still includes the existing Starlette/httpx deprecation warning from `fastapi.testclient`.

## Review Fix

- Fixed C1 audit scope: `event_group=all` now applies the union of `admin_user.*` and `service_membership.*` allow-lists before optional filters, so non-permission events such as `api_key.created` return an empty result even when requested with `event_type`.
- Added regression coverage in `test_permission_management_audit_logs_filter_groups_and_sanitize_states` for default `event_group=all`, `event_type=api_key.created`, `actor_id`, `target_id`, and `limit` filtering.
- Hardened `test_permission_management_risk_findings_returns_baseline_findings` cleanup by moving system_admin role backup/delete inside the protected `try` block and always attempting role restore after cleanup.
- Verification:
  - `TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/integration/test_permission_management_api.py -q` -> `7 passed, 1 warning`
  - `uv run ruff check src/intent_routing/api/admin.py src/intent_routing/db/repositories.py tests/integration/test_permission_management_api.py` -> `All checks passed!`
