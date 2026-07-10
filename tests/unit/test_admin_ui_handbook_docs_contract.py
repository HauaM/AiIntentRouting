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
        "Do not run a browser",
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
        "GET /admin/v1/users?query={email_or_name}&limit=25",
        "GET /admin/v1/services/{service_id}/members",
        "POST /admin/v1/services/{service_id}/members/{user_id}/roles",
        "DELETE /admin/v1/services/{service_id}/members/{user_id}/roles/{role}",
        "service_membership.role_granted",
        "service_membership.role_revoked",
        "`system_admin` can search users, list members, grant roles, and revoke roles",
        "service_owner delegation",
        "future/non-baseline",
        "irt_admin_session",
        "C-2 frontend must not send `X-Admin-Token`, `X-Actor-Id`, "
        "`X-Actor-Roles`, `X-Service-Scope`, or `Authorization: Bearer`",
        "Do not add React Query or axios",
    ):
        assert expected in contract
