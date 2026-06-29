# Branch Protection Required Check Operations

## Scope

Protect `main` so every merge requires the GitHub Actions `CI / verify` job to
pass. The workflow runs on `pull_request`, `push` to `main`, and
`workflow_dispatch`; branch protection uses the `pull_request` check before merge
and `workflow_dispatch` is the operator path for rerunning the same commit during
rollback or bypass review.

## GitHub UI Path

1. Open the repository in GitHub.
2. Go to **Settings** > **Branches**.
3. Add or edit the branch protection rule for `main`.
4. Enable `Require status checks to pass before merging`.
5. Select the required status check `CI / verify`.
6. Enable `Require branches to be up to date before merging`.
7. Save the rule.
8. Open a test pull request and confirm GitHub blocks merge until `CI / verify`
   passes on the current head commit.

## GitHub CLI/API Reference Path

Use the GitHub API only from an authenticated operator shell. Do not put tokens,
personal access tokens, GitHub App private keys, or secret values in the payload
file, shell history, or this runbook.

Safe command shape:

```bash
gh api --method PUT repos/HauaM/AiIntentRouting/branches/main/protection --input branch-protection-payload.json
```

Safe payload shape:

```json
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["CI / verify"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": null,
  "restrictions": null
}
```

In this payload, `"strict": true` is the API equivalent of
`Require branches to be up to date before merging`, and the `contexts` entry is
the required `CI / verify` status check.

## Evidence Check

After applying the rule, verify the latest pull request run:

1. Confirm the `CI / verify` job is attached to the pull request and is required.
2. Confirm the `pilot-e2e-evidence` artifact is present when the workflow runs.
3. Confirm the artifact retention is `14 days`.
4. Confirm artifact contents include runtime evidence and `api.log`.
5. Confirm there is no .secret.json file in the artifact contents.

Record the rule snapshot, required check verification, merge block verification,
artifact review, rollback or bypass details, and final state in
`docs/ops/branch-protection-evidence-template.md`.

If the implementer does not have repository admin permission, create an evidence request using docs/ops/branch-protection-evidence-template.md and mark the rule snapshot as operator-not-permitted.
operator-not-permitted does not satisfy pilot go/no-go until an authorized operator attaches the rule snapshot.

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
if "CI / verify" not in contexts:
    raise SystemExit("CI / verify is not a required status check")

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
CI / verify appears as a required status check
strict is true
enforce_admins is true, or enforce_admins.enabled is true, when repository policy requires admin enforcement
```

## branch protection rollback

Use rollback only for a CI infrastructure issue that blocks an urgent merge after
reviewers agree the application change is safe.

1. Record the temporary bypass approval ID in the incident, release, or change
   ticket before changing the rule or bypassing the required check.
2. Record the exact commit SHA being merged.
3. Merge only the approved commit and avoid batching unrelated changes.
4. Rerun `CI / verify` on the same commit with `workflow_dispatch` as soon as
   GitHub Actions is healthy.
5. Download `pilot-e2e-evidence` from that rerun.
6. Verify the artifact contains no .secret.json file.
7. Restore the `main` branch protection rule if it was temporarily changed.
8. Close the rollback record with the temporary bypass approval ID, rerun URL,
   artifact review result, and final branch protection state.
