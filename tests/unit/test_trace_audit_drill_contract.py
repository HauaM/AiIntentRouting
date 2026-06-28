import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_trace_audit_drill_script_documents_masked_and_decrypt_paths() -> None:
    text = (ROOT / "scripts/trace_audit_drill.py").read_text(encoding="utf-8")

    assert "/runtime-logs" in text
    assert ":decrypt-raw-query" in text
    assert "--approval-id" in text
    assert "--view-reason" in text
    assert "query_raw" not in _stdout_safe_strings(text)


def test_main_decrypt_mode_prints_redacted_metadata_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    script_path = ROOT / "scripts/trace_audit_drill.py"
    if not script_path.exists():
        pytest.skip("script not implemented yet")

    trace_audit_drill = importlib.import_module("scripts.trace_audit_drill")
    state_path = tmp_path / "pilot.state.secret.json"
    state_path.write_text(json.dumps({"service_id": "svc-test"}), encoding="utf-8")
    fake_client = _FakeAdminApiClient(
        response={
            "trace_id": "trace-123",
            "service_id": "svc-test",
            "query_raw": "super secret raw query",
            "viewed_by": "pilot-auditor",
            "viewed_at": "2026-06-28T10:00:00Z",
        }
    )

    monkeypatch.setattr(trace_audit_drill, "AdminApiClient", fake_client.factory)

    trace_audit_drill.main(
        [
            "--base-url",
            "http://admin.test",
            "--admin-token",
            "local-admin-token",
            "--state",
            str(state_path),
            "--trace-id",
            "trace-123",
            "--approval-id",
            "SEC-20260628-001",
            "--view-reason",
            "장애 분석 ticket INC-20260626-001",
        ]
    )

    stdout = capsys.readouterr().out
    assert fake_client.calls == [
        {
            "path": "/admin/v1/services/svc-test/runtime-logs/trace-123:decrypt-raw-query",
            "json": {
                "view_reason": (
                    "approval=SEC-20260628-001; "
                    "reason=장애 분석 ticket INC-20260626-001"
                )
            },
        }
    ]
    assert fake_client.entered is True
    assert fake_client.exited is True
    assert "super secret raw query" not in stdout
    assert '"raw_query_viewed": true' in stdout
    assert '"trace_id": "trace-123"' in stdout


def test_main_uses_env_admin_token_when_cli_token_is_omitted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    trace_audit_drill = importlib.import_module("scripts.trace_audit_drill")
    state_path = tmp_path / "pilot.state.secret.json"
    state_path.write_text(json.dumps({"service_id": "svc-test"}), encoding="utf-8")
    fake_client = _FakeAdminApiClient(
        response=[
            {
                "trace_id": "trace-123",
                "service_id": "svc-test",
                "query_masked": "***",
            }
        ]
    )
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "env-admin-token")
    monkeypatch.setattr(trace_audit_drill, "AdminApiClient", fake_client.factory)

    trace_audit_drill.main(
        [
            "--base-url",
            "http://admin.test",
            "--state",
            str(state_path),
        ]
    )

    stdout = capsys.readouterr().out
    assert fake_client.init_kwargs["admin_token"] == "env-admin-token"
    assert fake_client.calls == [
        {
            "path": "/admin/v1/services/svc-test/runtime-logs",
            "params": {"limit": 5},
        }
    ]
    assert '"trace_id": "trace-123"' in stdout


def test_parse_args_reads_state_as_path_type() -> None:
    trace_audit_drill = importlib.import_module("scripts.trace_audit_drill")

    args = trace_audit_drill._parse_args(
        [
            "--base-url",
            "http://admin.test",
            "--state",
            "var/pilot/example.state.secret.json",
        ]
    )

    assert isinstance(args.state, Path)
    assert args.state == Path("var/pilot/example.state.secret.json")


def test_parse_args_rejects_view_reason_without_trace_id() -> None:
    trace_audit_drill = importlib.import_module("scripts.trace_audit_drill")

    with pytest.raises(SystemExit, match="--view-reason requires --trace-id"):
        trace_audit_drill._parse_args(
            [
                "--base-url",
                "http://admin.test",
                "--state",
                "var/pilot/example.state.secret.json",
                "--view-reason",
                "ticket INC-20260626-001",
            ]
        )


def test_parse_args_rejects_approval_id_without_view_reason() -> None:
    trace_audit_drill = importlib.import_module("scripts.trace_audit_drill")

    with pytest.raises(SystemExit, match="--approval-id requires --trace-id and --view-reason"):
        trace_audit_drill._parse_args(
            [
                "--base-url",
                "http://admin.test",
                "--state",
                "var/pilot/example.state.secret.json",
                "--trace-id",
                "trace-123",
                "--approval-id",
                "SEC-20260628-001",
            ]
        )


def _stdout_safe_strings(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if "print(" in line:
            lines.append(line)
    return "\n".join(lines)


class _FakeAdminApiClient:
    def __init__(self, *, response: object) -> None:
        self._response = response
        self.calls: list[dict[str, object]] = []
        self.entered = False
        self.exited = False
        self.init_kwargs: dict[str, object] = {}

    def factory(self, **kwargs: object) -> "_FakeAdminApiClient":
        self.init_kwargs = dict(kwargs)
        return self

    def __enter__(self) -> "_FakeAdminApiClient":
        self.entered = True
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: object,
    ) -> None:
        self.exited = True

    def get(self, path: str, *, params: dict[str, int] | None = None) -> object:
        self.calls.append({"path": path, "params": params})
        return self._response

    def post(self, path: str, *, json: dict[str, str] | None = None) -> object:
        self.calls.append({"path": path, "json": json})
        return self._response
