from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDBOOK = ROOT / "docs/AdminUI_Handbook"
V04 = HANDBOOK / "v04"


def _read(path: Path) -> str:
    assert path.exists(), f"{path} must exist"
    return path.read_text(encoding="utf-8")


def test_admin_ui_v04_handbook_files_exist() -> None:
    for relative_path in (
        "README.md",
        "SETUP_GUIDE.md",
        "PATTERN_KIT.md",
        "ONBOARDING_FLOW.md",
        "examples/adminServices.ts",
        "examples/AdminShell.tsx",
        "examples/ServiceScopeBar.tsx",
        "examples/IntentCatalogTable.tsx",
        "examples/RuntimeLogsTable.tsx",
        "examples/AuditLogsTable.tsx",
        "examples/ConfirmActionButton.tsx",
        "examples/FutureFeatureNotice.tsx",
    ):
        assert (V04 / relative_path).exists()


def test_admin_ui_v04_records_sprint9_reference_boundary() -> None:
    readme = _read(V04 / "README.md")
    pattern_kit = _read(V04 / "PATTERN_KIT.md")
    admin_shell = _read(V04 / "examples/AdminShell.tsx")

    for expected in (
        "Sprint 9",
        "Go",
        "Admin UI implementation: excluded",
        "future Admin UI sprint",
        "reference implementation",
    ):
        assert expected in f"{readme}\n{pattern_kit}"

    assert 'message="Sprint 9: Go"' in admin_shell
    assert "Admin UI implementation was excluded from Sprint 9" in admin_shell


def test_admin_ui_v04_uses_umi_request_without_react_query_or_axios() -> None:
    setup_guide = _read(V04 / "SETUP_GUIDE.md")
    services = _read(V04 / "examples/adminServices.ts")
    examples = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((V04 / "examples").glob("*"))
    )

    assert "Do not install React Query or axios" in setup_guide
    assert "from '@umijs/max'" in services
    assert "withCredentials: true" in setup_guide
    assert "/auth/login" in setup_guide
    assert "/auth/me" in setup_guide
    assert "/me/services" in setup_guide
    assert "irt_admin_session" in setup_guide

    forbidden_implementation_patterns = (
        "@tanstack/react-query",
        "new QueryClient",
        "useQuery(",
        "useMutation(",
        "from 'axios'",
        'from "axios"',
        "headers!['Authorization']",
        'headers!["Authorization"]',
    )
    for pattern in forbidden_implementation_patterns:
        assert pattern not in examples


def test_admin_ui_v04_records_authorization_first_onboarding_flow() -> None:
    onboarding = _read(V04 / "ONBOARDING_FLOW.md")
    pattern_kit = _read(V04 / "PATTERN_KIT.md")
    readme = _read(V04 / "README.md")

    for expected in (
        "C-1: Service Onboarding",
        "C-2: Service Membership, Roles, And Developer Validation",
        "C-3: Runtime Integration And Operations",
        "Service picker options come from `/me/services`",
        "Do not send `X-Admin-Token`",
        "GET /admin/v1/services/{service_id}/api-keys",
        "GET /admin/v1/services/{service_id}/runtime-setup",
        "explicit runtime live-test workflow",
        "operator manually enters an API Secret",
        "`selected_key` metadata only",
    ):
        assert expected in onboarding

    assert "Authorization-first onboarding" in pattern_kit
    assert "Runtime setup guidance" in pattern_kit
    assert "`POST /services/{sid}/api-keys`" in pattern_kit
    assert "ONBOARDING_FLOW.md" in readme


def test_admin_ui_v04_records_c2_membership_role_assignment_contract() -> None:
    onboarding = _read(V04 / "ONBOARDING_FLOW.md")
    pattern_kit = _read(V04 / "PATTERN_KIT.md")
    contract = f"{onboarding}\n{pattern_kit}"

    for expected in (
        "GET /admin/v1/services/{service_id}/users?query={email_or_name}&limit=25",
        "GET /admin/v1/services/{service_id}/members",
        "POST /admin/v1/services/{service_id}/members/{user_id}/roles",
        "DELETE /admin/v1/services/{service_id}/members/{user_id}/roles/{role}",
        "service_membership.role_granted",
        "service_membership.role_revoked",
        "Accepted authorization: `system_admin` and an authorized `service_owner`",
        "service-scoped user lookup",
        "selected-Service boundary",
        "irt_admin_session",
        "C-2 frontend must not send `X-Admin-Token`, `X-Actor-Id`, "
        "`X-Actor-Roles`, `X-Service-Scope`, or `Authorization: Bearer`",
        "Do not add React Query or axios",
    ):
        assert expected in contract

    for stale_phrase in (
        "Baseline C-2 membership administration is `system_admin` only",
        "service_owner delegation",
        "future/non-baseline",
    ):
        assert stale_phrase not in contract


def test_admin_ui_v04_records_release_owned_environment_and_concrete_role_gates() -> None:
    checklist = _read(V04 / "E2E_DX_QA_CHECKLIST.md")
    pattern_kit = _read(V04 / "PATTERN_KIT.md")
    normalized_pattern_kit = " ".join(pattern_kit.split())
    membership_negative = checklist.split(
        "### TC-056 Service membership 권한 경계",
        maxsplit=1,
    )[1].split("### TC-059", maxsplit=1)[0]
    api_key_negative = checklist.split(
        "### TC-059 Non-system-admin API Key 관리 시도",
        maxsplit=1,
    )[1].split("### TC-060", maxsplit=1)[0]

    service_creation = checklist.split("### TC-008", maxsplit=1)[0]
    release_creation = checklist.split("### TC-032 Release 생성", maxsplit=1)[1].split(
        "### TC-033", maxsplit=1
    )[0]
    for expected in (
        "Service ID",
        "Display name",
        "Max input tokens",
    ):
        assert expected in service_creation
    assert "Release 생성 시 passed test candidate에서 Environment를 지정한다." in release_creation
    for stale_field in (
        "Environment 기본값",
        "Environment를 선택한다.",
        "Default threshold preset",
        "Default preset",
    ):
        assert stale_field not in service_creation

    for expected in (
        "`service_operator`: scoped runtime metrics, runtime log inspection, and "
        "audit log inspection.",
        "`auditor`: scoped runtime log inspection, audit log inspection, security "
        "lifecycle read, raw-query approval/review paths, and masked export.",
        "Organization Directory and Permission Management are system-admin-only.",
        "Audit Logs are not shown to `service_owner` or `service_developer`.",
    ):
        assert expected in normalized_pattern_kit

    for expected in (
        "선택한 Service의 `service_owner` 계정으로 user lookup, membership list, "
        "grant/revoke를 시도한다.",
        "`system_admin`과 인가된 `service_owner`만 membership을 관리할 수 있다.",
    ):
        assert expected in membership_negative
    assert "baseline C-2에서는 모두 차단된다." not in membership_negative
    assert "향후 owner delegation" not in membership_negative

    for expected in (
        "선택한 Service의 `service_owner` 계정으로 API key 생성 또는 revoke를 시도한다.",
        "runtime key lifecycle은 `system_admin`과 인가된 `service_owner`로 통제된다.",
    ):
        assert expected in api_key_negative


def test_admin_ui_v04_records_audited_api_key_secret_reveal() -> None:
    pattern_kit = _read(V04 / "PATTERN_KIT.md")
    onboarding = _read(V04 / "ONBOARDING_FLOW.md")
    checklist = _read(V04 / "E2E_DX_QA_CHECKLIST.md")
    theme = _read(ROOT / "docs/THEME_AND_UX_GUIDE_v1.md")
    text = f"{pattern_kit}\n{onboarding}\n{checklist}\n{theme}"

    for phrase in (
        "Secret 보기/복사",
        "POST /admin/v1/services/{service_id}/api-keys/{key_id}:reveal",
        "api_key.secret_revealed",
        "encrypted secret material",
        "raw secret is copied only through the audited reveal endpoint",
        "Creation displays and copies the initial raw secret; later copying uses "
        "the audited reveal endpoint.",
        "자동으로 secret이 다시 표시되거나 UI 상태에 재생성되지 않는다.",
        "권한 있는 `system_admin` 또는 선택한 Service의 `service_owner`만",
        "감사되는 명시적 reveal/copy 동작으로 secret을 확인할 수 있다.",
        "생성 응답에 raw API key secret이 표시되고, 이후에는 명시적 audited",
    ):
        assert phrase in text

    for stale_phrase in (
        "운영자가 secret을 재조회할 수 없다는 보안 제약",
        "raw API key secret은 한 번만 표시된다.",
        "raw API key secret이 생성 직후 한 번만 표시된다.",
    ):
        assert stale_phrase not in text
