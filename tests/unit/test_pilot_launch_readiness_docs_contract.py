from pathlib import Path

from intent_routing.ops.rehearsal import SecretScanResult, scan_evidence_directory

ROOT = Path(__file__).resolve().parents[2]
CHECKLIST = ROOT / "docs/ops/pilot-launch-readiness-checklist.md"
RUNBOOK = ROOT / "docs/ops/intent-routing-pilot-runbook.md"
CHECKLIST_PATH = "docs/ops/pilot-launch-readiness-checklist.md"
DRY_FILL_COPY = (
    "Copy docs/ops/pilot-handoff-release-ticket-template.md to "
    "var/evidence/${SERVICE_ID}/release-ticket.md."
)
DRY_FILL_FIELDS = (
    "Fill the release ticket with evidence paths, hashes, statuses, reviewer "
    "names, approval IDs, and go gate summary only."
)
DRY_FILL_FORBIDDEN_CONTENT = (
    "Do not paste screenshot contents, workflow export contents, raw query text, "
    "API keys, bearer tokens, KEK material, encrypted DEKs, or ciphertext."
)
DRY_FILL_REVIEWER_COMMANDS = "Run the reviewer commands."
DRY_FILL_DECISION_LINK = "Link the release ticket from pilot-go-no-go-decision.md."
RELEASE_TICKET_PATH = "var/evidence/${SERVICE_ID}/release-ticket.md"
REQUIRED_RELEASE_REFERENCE_MARKERS = (
    "PASS|CI / verify|pilot-rehearsal-manifest.md|",
    "Dify workflow version identifier|BGE evidence status|",
    "branch protection evidence|CSV baseline|go/no-go",
)
FORBIDDEN_RELEASE_MARKER_SCAN_PARTS = (
    "Bearer |Authorization: Bearer|",
    "RAW_TEXT_KEK_BASE64|RAW_TEXT_LEGACY_KEKS_JSON|",
    "api_key=|intent_routing_api_key|",
    "query_raw|text_raw|encrypted_dek|ciphertext|",
    "irt_live_|irt_secret",
)


def _compact(text: str) -> str:
    return " ".join(text.split())


def _write_checklist_copy_without_intentional_forbidden_scan(
    tmp_path: Path, source: Path
) -> Path:
    sanitized_lines = []
    in_forbidden_marker_assignment = False
    for line in source.read_text(encoding="utf-8").splitlines():
        if "forbidden_release_markers=$(" in line:
            in_forbidden_marker_assignment = True
            sanitized_lines.append(line)
        elif in_forbidden_marker_assignment and line.strip() == ")":
            in_forbidden_marker_assignment = False
            sanitized_lines.append(line)
        elif in_forbidden_marker_assignment:
            sanitized_lines.append("    'REDACTED' \\")
        elif line.lstrip().startswith("3. Do not paste"):
            sanitized_lines.append("3. release ticket forbidden content policy: REDACTED")
        elif "ciphertext" in line:
            sanitized_lines.append("release ticket forbidden content policy: REDACTED")
        else:
            sanitized_lines.append(line)

    sanitized = tmp_path / source.name
    sanitized.write_text("\n".join(sanitized_lines) + "\n", encoding="utf-8")
    return sanitized


def test_pilot_launch_readiness_checklist_contains_required_contract() -> None:
    text = CHECKLIST.read_text(encoding="utf-8")
    compact_text = _compact(text)

    for expected in (
        CHECKLIST_PATH,
        "Pilot Launch Readiness & Evidence Closure",
        "Admin UI excluded from Sprint 7",
        "Dify UI dry-run evidence",
        "Dify workflow version identifier",
        "Dify UI dry-run evidence reviewer",
        "Dify evidence linked from release ticket",
        "Dify condition owner",
        "release-ticket.md",
        "var/evidence/${SERVICE_ID}/release-ticket.md",
        DRY_FILL_REVIEWER_COMMANDS,
        "evidence links only",
        "BGE evidence status",
        "measured-pass",
        "pending-host-access exception approval",
        "branch protection evidence",
        "authorized branch protection evidence for main",
        "operator-not-permitted does not satisfy pilot go/no-go",
        "main-protection.json",
        "branch protection capture verified",
        "artifact review result",
        "CI / verify",
        "CSV baseline freeze approval",
        "CSV baseline freeze approval:",
        "docs/pilot/csv-baseline-freeze-approval-template.md",
        "CSV baseline comparison PASS",
        "Refresh status: refresh not approved / policy-approved refresh attached",
        "Freeze approval ID:",
        "Release owner:",
        "QA or security reviewer:",
        "local rehearsal regeneration",
        "pilot go/no-go decision record",
        "Conditional Go",
        "go requires",
        "no secrets",
        "no raw query text",
    ):
        assert expected in text

    for expected in (
        DRY_FILL_COPY,
        DRY_FILL_FIELDS,
        DRY_FILL_FORBIDDEN_CONTENT,
        DRY_FILL_DECISION_LINK,
        "no screenshot contents",
        "no workflow export contents",
        "go requires BGE measured-pass before closed-network pilot traffic",
        (
            "Conditional Go with pending-host-access requires exception "
            "approval ID, exception owner, expiration before pilot traffic, "
            "and next measurement date"
        ),
        "measured-fail blocks pilot launch until corrected evidence passes",
        (
            "Do not convert a failed measurement into Conditional Go. Keep the "
            "decision as No Go until the evidence is corrected, regenerated, "
            "and accepted as measured-pass."
        ),
        (
            "Rollback or bypass evidence must include approval ID, exact commit "
            "SHA, workflow_dispatch rerun URL, artifact review result, and "
            "final branch protection state."
        ),
        "approval ID, exact commit SHA, workflow_dispatch rerun URL",
        "final branch protection state",
        (
            "go requires either CSV baseline freeze approval or a "
            "policy-approved refresh approval"
        ),
    ):
        assert expected in compact_text


def test_pilot_launch_readiness_checklist_contains_required_sections() -> None:
    text = CHECKLIST.read_text(encoding="utf-8")

    for heading in (
        "# Pilot Launch Readiness Checklist",
        "## Scope",
        "## Evidence Closure Order",
        "## Local Rehearsal Regeneration",
        "## Dify UI Dry-Run Closure",
        "## Closed-Network BGE Closure",
        "## Branch Protection Closure",
        "## CSV Baseline Freeze Closure",
        "## Release Ticket Review",
        "## Go/No-Go Decision",
        "## Failure Handling",
        "## Files That Must Not Be Committed",
    ):
        assert heading in text


def test_pilot_release_ticket_dry_fill_order_is_documented_in_runbook() -> None:
    text = _compact(RUNBOOK.read_text(encoding="utf-8"))

    for expected in (
        DRY_FILL_COPY,
        DRY_FILL_FIELDS,
        DRY_FILL_FORBIDDEN_CONTENT,
        DRY_FILL_REVIEWER_COMMANDS,
        DRY_FILL_DECISION_LINK,
    ):
        assert expected in text


def _assert_reviewer_commands_are_documented(text: str) -> None:
    assert "required_release_refs=$(" in text
    assert "forbidden_release_markers=$(" in text
    assert 'rg -n "${required_release_refs}" \\' in text
    assert 'rg -n "${forbidden_release_markers}" \\' in text
    assert RELEASE_TICKET_PATH in text
    assert "first rg prints required evidence references" in text
    assert "second rg prints no matches" in text

    for marker in REQUIRED_RELEASE_REFERENCE_MARKERS:
        assert marker in text

    for marker in FORBIDDEN_RELEASE_MARKER_SCAN_PARTS:
        assert marker in text


def test_pilot_release_ticket_reviewer_commands_are_documented_in_checklist() -> None:
    text = CHECKLIST.read_text(encoding="utf-8")

    _assert_reviewer_commands_are_documented(text)


def test_pilot_release_ticket_reviewer_commands_are_documented_in_runbook() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    _assert_reviewer_commands_are_documented(text)


def test_pilot_launch_readiness_checklist_is_secret_scan_safe(tmp_path: Path) -> None:
    sanitized_checklist = _write_checklist_copy_without_intentional_forbidden_scan(
        tmp_path, CHECKLIST
    )
    result = scan_evidence_directory(tmp_path, extra_paths=[sanitized_checklist])

    assert result == SecretScanResult(passed=True, findings=[])


def test_pilot_launch_readiness_checklist_is_linked_from_required_docs() -> None:
    for path in (
        ROOT / "README.md",
        ROOT / "docs/ops/pilot-rehearsal.md",
        ROOT / "docs/ops/intent-routing-pilot-runbook.md",
        ROOT / "docs/ops/pilot-evidence-bundle-checklist.md",
    ):
        text = path.read_text(encoding="utf-8")

        assert CHECKLIST_PATH in text
