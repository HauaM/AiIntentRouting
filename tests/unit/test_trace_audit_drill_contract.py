import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_trace_audit_drill_script_documents_masked_and_decrypt_paths() -> None:
    text = (ROOT / "scripts/trace_audit_drill.py").read_text(encoding="utf-8")

    assert "/runtime-logs" in text
    assert ":decrypt-raw-query" in text
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
            "--view-reason",
            "장애 분석 ticket INC-20260626-001",
        ]
    )

    stdout = capsys.readouterr().out
    assert fake_client.calls == [
        {
            "path": "/admin/v1/services/svc-test/runtime-logs/trace-123:decrypt-raw-query",
            "json": {"view_reason": "장애 분석 ticket INC-20260626-001"},
        }
    ]
    assert fake_client.entered is True
    assert fake_client.exited is True
    assert "super secret raw query" not in stdout
    assert '"raw_query_viewed": true' in stdout
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


def _stdout_safe_strings(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if "print(" in line:
            lines.append(line)
    return "\n".join(lines)


class _FakeAdminApiClient:
    def __init__(self, *, response: dict[str, str]) -> None:
        self._response = response
        self.calls: list[dict[str, object]] = []
        self.entered = False
        self.exited = False

    def factory(self, **_kwargs: object) -> "_FakeAdminApiClient":
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

    def post(self, path: str, *, json: dict[str, str] | None = None) -> dict[str, str]:
        self.calls.append({"path": path, "json": json})
        return self._response
