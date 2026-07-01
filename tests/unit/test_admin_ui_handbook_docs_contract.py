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
    assert "X-Admin-Token" in setup_guide
    assert "X-Actor-Id" in setup_guide
    assert "X-Actor-Roles" in setup_guide
    assert "X-Service-Scope" in setup_guide

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

