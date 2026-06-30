from pathlib import Path

from intent_routing.ops.rehearsal import SecretScanResult, scan_evidence_directory

ROOT = Path(__file__).resolve().parents[2]
CLOSURE_DOC = ROOT / "docs/ops/pilot-sprint-8-execution-closure.md"
RELEASE_TICKET_DOC = ROOT / "docs/ops/pilot-sprint-8-release-ticket.md"
DECISION_DOC = ROOT / "docs/ops/pilot-sprint-8-go-no-go-decision.md"

CLOSURE_PATH = "docs/ops/pilot-sprint-8-execution-closure.md"
RELEASE_TICKET_PATH = "docs/ops/pilot-sprint-8-release-ticket.md"
DECISION_PATH = "docs/ops/pilot-sprint-8-go-no-go-decision.md"

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


def test_sprint8_closure_docs_exist_and_contain_required_contract() -> None:
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

    for expected in (
        "2026-06-30",
        "Asia/Seoul",
        "Admin UI implementation: excluded",
        "var/evidence/it-helpdesk-pilot-sprint8-local",
        "SERVICE_ID: it-helpdesk-pilot-sprint8-local",
        "32b611e2b05e240e1726ae6a733b6305cd4ff0ac",
        "https://github.com/HauaM/AiIntentRouting/pull/7",
        "ce33ff250de27721f272e35a27253d24a08ad3c3",
        "https://github.com/HauaM/AiIntentRouting/actions/runs/28421845592/job/84216398277",
        "Local rehearsal status: PASS",
        "secret_scan.passed: true",
        "Decision value: No Go",
        "pilot traffic approved: no",
    ):
        assert expected in closure

    for expected in (
        "Official sanitized release ticket",
        "runtime evidence is not committed",
        "c0cdb9dc11b581d7eab1613ee0f6241c34791eded41ae90a8824e3e713a7dd37",
        "e9f13d33ea07d3621604c2a80e7c4b04036a053bd7e01de72985c714ceb1352e",
        "Dify UI dry-run: blocked",
        "BGE closed-network: pending-host-access",
        "Branch protection: blocked",
        "CSV baseline: comparison PASS",
    ):
        assert expected in release_ticket

    for expected in (
        "Decision value: No Go",
        "Dify owner: not assigned",
        "Dify approval ID: not provided",
        "BGE owner: not assigned",
        "BGE exception approval ID: not provided",
        "Branch protection owner: not assigned",
        "CSV freeze approval ID: not provided",
        "no pilot traffic approved",
    ):
        assert expected in decision


def test_sprint8_top_level_closure_links_official_records() -> None:
    text = _read(CLOSURE_DOC)

    assert RELEASE_TICKET_PATH in text
    assert DECISION_PATH in text
    assert CLOSURE_PATH in text


def test_sprint8_decision_doc_allows_only_no_go_final_value() -> None:
    text = _read(DECISION_DOC)

    assert text.count("Decision value: No Go") == 1
    assert "Decision value: Go" not in text
    assert "Decision value: Conditional Go" not in text


def test_sprint8_closure_docs_are_secret_safe_and_admin_ui_handbook_free(
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
