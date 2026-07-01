# Branch Protection Evidence Template

Use this template when applying, verifying, rolling back, or temporarily
bypassing the `main` branch protection rule. Store completed evidence under
`var/evidence/${SERVICE_ID}/branch-protection/`; do not commit generated
evidence files.

Template path: `docs/ops/branch-protection-evidence-template.md`

## Capture Metadata

- Evidence type: apply / verify / rollback / operator-not-permitted
- Authorized operator:
- Operator permission result: authorized / operator-not-permitted
- Rule snapshot path:
  `var/evidence/${SERVICE_ID}/branch-protection/main-protection.json`
- Verification output: branch protection capture verified
- Final state reviewer:
- Release ticket path: var/evidence/${SERVICE_ID}/release-ticket.md
- Go/no-go decision path: var/evidence/${SERVICE_ID}/pilot-go-no-go-decision.md

Use this section for authorized operator capture, apply evidence, rollback
evidence, or an operator-not-permitted evidence request.

## Operator Permission Policy

operator-not-permitted may record an evidence request, but it does not satisfy
pilot go/no-go.
An authorized operator must attach main-protection.json or explicitly approve a
blocked Conditional Go with owner and deadline.

## Rule Snapshot

- Branch: `main`
- Required check: `CI / verify`
- API required check context: `verify`
- GitHub UI settings:
  - `Require status checks to pass before merging`
  - `Require branches to be up to date before merging`
- Contract shorthand:
  - `strict: true`
  - `checks: [{"context": "verify", "app_id": 15368}]`
  - `enforce_admins: true`
- Operator status: `<authorized | operator-not-permitted>`

Required rule value:

```json
{
  "required_status_checks": {
    "strict": true,
    "checks": [
      {
        "context": "verify",
        "app_id": 15368
      }
    ]
  },
  "enforce_admins": true
}
```

Manual capture command, for an authorized operator only:

```bash
mkdir -p var/evidence/${SERVICE_ID}/branch-protection
gh api repos/HauaM/AiIntentRouting/branches/main/protection \
  > var/evidence/${SERVICE_ID}/branch-protection/main-protection.json
```

Verification command:

```bash
uv run python - var/evidence/${SERVICE_ID}/branch-protection/main-protection.json <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    protection = json.load(fh)

required_status_checks = protection.get("required_status_checks") or {}
if required_status_checks.get("strict") is not True:
    raise SystemExit("required_status_checks.strict is not true")

contexts = set(required_status_checks.get("contexts") or [])
for check in required_status_checks.get("checks") or []:
    contexts.update(
        value
        for value in (check.get("context"), check.get("name"))
        if isinstance(value, str)
    )
if "CI / verify" not in contexts and "verify" not in contexts:
    raise SystemExit("CI / verify or verify is not a required status check")

enforce_admins = protection.get("enforce_admins")
admins_enabled = enforce_admins is True or (
    isinstance(enforce_admins, dict) and enforce_admins.get("enabled") is True
)
if not admins_enabled:
    raise SystemExit("enforce_admins is not enabled")

print("branch protection capture verified")
PY
```

Expected:

```text
branch protection capture verified
```

## Required Check Verification

- Pull request URL:
- Head commit:
- `CI / verify` run URL:
- `workflow_dispatch` rerun URL, when used:
- Verification result:
- Notes:

## Pull Request Merge Block Verification

- Pull request URL:
- Merge blocked before `CI / verify` passed: `<yes | no>`
- Merge allowed only after the current head commit passed: `<yes | no>`
- Evidence screenshot or log reference:
- Reviewer:

## Artifact Verification

- `pilot-e2e-evidence` artifact URL:
- Artifact retention: `14 days`
- `api.log` present: `<yes | no>`
- Runtime evidence present: `<yes | no>`
- `no .secret.json` confirmation: `<yes | no>`
- Artifact review result:

## Rollback Or Temporary Bypass Record

- temporary bypass approval ID:
- rollback approval ID:
- exact commit SHA:
- reason:
- reviewers:
- workflow_dispatch rerun URL:
- pilot-e2e-evidence artifact review result:
- no .secret.json confirmation:
- final branch protection state:

## Final State

- restore or confirm final branch protection state:
- `CI / verify` required on `main`:
- API required check context `verify` confirmed:
- `strict: true` confirmed:
- `checks: [{"context": "verify", "app_id": 15368}]` confirmed:
- Operator:
- Timestamp:
