# Supplemental Task 3B Report: Backend Permission Service Roles API

## Status

완료.

## 구현 내용

- `GET /admin/v1/permission-management/service-roles` endpoint를 추가했습니다.
- endpoint는 `require_admin_session_context`, `admin_context_from_session_record`, `_require_system_admin(context)`, `get_admin_session` 흐름을 사용합니다.
- `system_admin`만 접근 가능하며 read-only입니다.
- 응답은 service role assignment 단위로 `service_id`, `service_display_name`, admin user 요약, optional organization user 요약, `role`, `assigned_by`, `assigned_at`을 반환합니다.
- `organization_user.department_name`은 nullable string으로 반환합니다.
- repository helper `list_permission_service_role_summaries`를 추가해 `user_service_roles` 중심으로 `AdminUser`, `Service`, optional `OrganizationUser`, `Department` metadata를 조회합니다.
- 필터 `service_id`, `user_id`, `role`, `query`, `limit(1..500, default 200)`를 지원합니다.
- query는 admin user id/email/display name, service id/display name, organization user number/name, department name을 검색합니다.
- 기존 Service membership grant/revoke helper는 변경하지 않았습니다.

## 테스트

RED:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/integration/test_permission_management_api.py tests/unit/test_permission_management_repository.py -q
```

- 예상대로 3개 실패를 확인했습니다.
- 실패 원인: service-roles route 404, repository helper 미구현.

GREEN:

```bash
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest tests/integration/test_permission_management_api.py tests/unit/test_permission_management_repository.py -q
```

- 13 passed, 1 warning.
- warning은 기존 `fastapi.testclient`/Starlette deprecation warning입니다.

Ruff:

```bash
uv run ruff check src/intent_routing/api/admin.py src/intent_routing/db/repositories.py tests/integration/test_permission_management_api.py tests/unit/test_permission_management_repository.py
```

- All checks passed.

## 변경 파일

- `src/intent_routing/api/admin.py`
- `src/intent_routing/db/repositories.py`
- `tests/integration/test_permission_management_api.py`
- `tests/unit/test_permission_management_repository.py`
- `.superpowers/sdd/task-3b-report.md`

## 우려 사항

- 기능 검증은 지정된 integration/unit test와 ruff 기준으로 완료했습니다.
- 전체 테스트 스위트는 실행하지 않았습니다.
