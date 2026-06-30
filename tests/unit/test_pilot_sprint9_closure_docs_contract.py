from pathlib import Path

from intent_routing.ops.rehearsal import SecretScanResult, scan_evidence_directory

ROOT = Path(__file__).resolve().parents[2]
CLOSURE_DOC = ROOT / "docs/ops/pilot-sprint-9-execution-closure.md"
RELEASE_TICKET_DOC = ROOT / "docs/ops/pilot-sprint-9-release-ticket.md"
DECISION_DOC = ROOT / "docs/ops/pilot-sprint-9-go-no-go-decision.md"

CLOSURE_PATH = "docs/ops/pilot-sprint-9-execution-closure.md"
RELEASE_TICKET_PATH = "docs/ops/pilot-sprint-9-release-ticket.md"
DECISION_PATH = "docs/ops/pilot-sprint-9-go-no-go-decision.md"
SERVICE_ID = "it-helpdesk-pilot-sprint9-go-reassessment"

FORBIDDEN_SECRET_MARKERS = (
    "Bearer ",
    "Authorization: Bearer",
    "RAW_TEXT_KEK_BASE64",
    "RAW_TEXT_LEGACY_KEKS_JSON",
    "api_key=",
    "intent_routing_api_key",
    "query_raw",
    "text_raw",
    "encrypted_dek",
    "ciphertext",
    "irt_live_",
    "irt_secret",
)


def _read(path: Path) -> str:
    assert path.exists(), f"{path} must exist"
    return path.read_text(encoding="utf-8")


def test_sprint9_closure_docs_exist_and_cross_link() -> None:
    closure = _read(CLOSURE_DOC)
    release_ticket = _read(RELEASE_TICKET_DOC)
    decision = _read(DECISION_DOC)

    for heading in (
        "## Scope",
        "## Execution Sources",
        "## Gate Summary",
        "## Decision Boundary",
        "## Official Closure Links",
        "## Required Follow-Up Before Any Go",
    ):
        assert heading in closure

    assert CLOSURE_PATH in closure
    assert RELEASE_TICKET_PATH in closure
    assert DECISION_PATH in closure
    assert CLOSURE_PATH in release_ticket
    assert DECISION_PATH in release_ticket
    assert CLOSURE_PATH in decision
    assert RELEASE_TICKET_PATH in decision


def test_sprint9_release_ticket_records_gate_statuses() -> None:
    text = _read(RELEASE_TICKET_DOC)

    for expected in (
        SERVICE_ID,
        "Local rehearsal status: PASS",
        "final_status: PASS",
        "secret_scan.passed: true",
        "Manifest JSON SHA256: b645a3322a41b6314641446131aca37160ee86b6027f9f92ca6851091c1519b6",
        (
            "Manifest Markdown SHA256: "
            "051856591452adeb96ec45d785ee679f018942948e5f2a87dda8531176566441"
        ),
        "Dify UI dry-run: blocked",
        "BGE closed-network: blocked",
        "/models/bge-m3",
        "Branch protection: blocked",
        "CSV baseline freeze: blocked",
        "Runtime evidence is not committed",
        "Decision value: No Go",
    ):
        assert expected in text


def test_sprint9_decision_rules_force_no_go_for_blocked_required_gates() -> None:
    text = _read(DECISION_DOC)

    assert text.count("Decision value: No Go") == 1
    assert "Decision value: Go" not in text
    assert "Decision value: Conditional Go" not in text

    for expected in (
        "Dify UI dry-run: blocked",
        "Branch protection: blocked",
        "CSV baseline freeze: blocked",
        "BGE closed-network: blocked",
        "final_status: PASS",
        "/models/bge-m3",
        "No pilot traffic approved",
        "Conditional Go is not allowed",
        "Admin UI implementation: excluded",
    ):
        assert expected in text


def test_sprint9_closure_docs_are_secret_safe_and_admin_ui_handbook_free(
    tmp_path: Path,
) -> None:
    docs = (CLOSURE_DOC, RELEASE_TICKET_DOC, DECISION_DOC)

    for doc in docs:
        text = _read(doc)
        assert "docs/AdminUI_Handbook/" not in text
        for marker in FORBIDDEN_SECRET_MARKERS:
            assert marker not in text

    result = scan_evidence_directory(tmp_path, extra_paths=list(docs))

    assert result == SecretScanResult(passed=True, findings=[])
