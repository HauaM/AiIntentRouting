from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "frontend/intent-routing-console/config/config.ts"


def test_admin_ui_routes_include_account_login_page() -> None:
    text = CONFIG.read_text(encoding="utf-8")

    assert "{ path: '/login', component: './Login' }" in text
    assert "{ path: '/login', redirect: '/dashboard' }" not in text


def test_admin_ui_routes_include_phase1_write_flow_pages() -> None:
    text = CONFIG.read_text(encoding="utf-8")

    for route in (
        "{ path: '/releases', component: './Releases' }",
        "{ path: '/test-runs', component: './TestRuns' }",
        "{ path: '/api-keys', component: './ApiKeys' }",
    ):
        assert route in text

def test_admin_ui_routes_keep_phase0_read_screens() -> None:
    text = CONFIG.read_text(encoding="utf-8")

    for route in (
        "{ path: '/', redirect: '/dashboard' }",
        "{ path: '/dashboard', component: './Dashboard' }",
        "{ path: '/intents', component: './Intents' }",
        "{ path: '/runtime-logs', component: './RuntimeLogs' }",
        "{ path: '/audit-logs', component: './AuditLogs' }",
    ):
        assert route in text


def test_admin_ui_dev_proxy_supports_runtime_live_test_calls() -> None:
    text = CONFIG.read_text(encoding="utf-8")

    assert "'/v1'" in text
    assert "target: adminApiProxy" in text
