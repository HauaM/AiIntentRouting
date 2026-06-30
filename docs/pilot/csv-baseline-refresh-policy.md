# CSV Baseline Refresh Policy

This policy is maintained in `docs/pilot/csv-baseline-refresh-policy.md` and is
the source of truth for approving CSV baseline refreshes.

## Current Baseline

The current checked-in baseline is docs/pilot/it-helpdesk-pilot-baseline.json.
It freezes the standard 50-row CSV for the balanced preset.

The baseline policy keeps the regression gate strict:

- `allowed_new_failures: 0`
- `allowed_new_reviews: 0`

allowed_new_failures remains 0.
allowed_new_reviews remains 0.

Baseline JSON must not contain raw query text or secret-bearing fields.

## Pilot Launch Freeze Approval

When the baseline is intentionally kept frozen for pilot launch, complete
docs/pilot/csv-baseline-freeze-approval-template.md and link the completed copy
from release-ticket.md.

Refresh remains blocked unless the policy-approved approval ID and reviewed diff
evidence are attached.

## When Refresh Is Allowed

Refresh is allowed only when a reviewer intentionally accepts changed pilot
behavior. Acceptable reasons include a curated pilot CSV update, a catalog route
change, or a threshold policy change.

Refresh requires an approval ID and a reviewed CSV diff, catalog diff, or
threshold policy diff.

## When Refresh Is Blocked

Do not refresh the baseline merely to make a failing rehearsal pass.

Block the refresh when the change introduces unexplained new failures,
disallowed reviews, pass-rate regressions, `risk_pass_rate` regressions, or
decision, intent, or route-key drift.

Block the refresh when the baseline JSON would contain raw query text,
authorization headers, API keys, bearer tokens, encrypted DEKs, ciphertext, KEK
material, or other secret-bearing fields.

## Required Review Evidence

A baseline refresh pull request must include:

- The approval ID that authorized the changed pilot behavior.
- The reviewed CSV diff, catalog diff, or threshold policy diff.
- The `compare_csv_baseline.py compare` JSON and Markdown evidence from the new
  baseline.
- Confirmation that `allowed_new_failures: 0` remains in force.
- Confirmation that `allowed_new_reviews: 0` remains in force.
- Confirmation that the baseline contains no raw query text or secret-bearing
  fields.

## Freeze Command

Use `compare_csv_baseline.py freeze` only after the required review evidence is
approved.

```bash
uv run python scripts/compare_csv_baseline.py freeze \
  --threshold-report var/evidence/${SERVICE_ID}/rehearsal/e2e/${SERVICE_ID}-threshold-comparison.json \
  --csv docs/pilot/it-helpdesk-pilot-cases.csv \
  --preset balanced \
  --baseline-id it-helpdesk-pilot-standard-YYYYMMDD \
  --out docs/pilot/it-helpdesk-pilot-baseline.json
```

## Compare Command

Use `compare_csv_baseline.py compare` to produce review evidence for the
candidate baseline.

```bash
uv run python scripts/compare_csv_baseline.py compare \
  --threshold-report var/evidence/${SERVICE_ID}/rehearsal/e2e/${SERVICE_ID}-threshold-comparison.json \
  --baseline docs/pilot/it-helpdesk-pilot-baseline.json \
  --csv docs/pilot/it-helpdesk-pilot-cases.csv \
  --out-dir var/evidence/${SERVICE_ID}/rehearsal/csv-baseline
```

## Pull Request Requirements

Pull requests that modify `docs/pilot/it-helpdesk-pilot-baseline.json` must link
the approval ID, explain the accepted behavior change, and attach the reviewed
CSV diff, catalog diff, or threshold policy diff.

The pull request must also include the comparison evidence, the baseline secret
scan result, and the reviewer conclusion for any `risk_pass_rate`, pass-rate,
decision, intent, or route-key movement.

## Rollback

If a refreshed baseline is approved in error, revert
`docs/pilot/it-helpdesk-pilot-baseline.json` to the last approved baseline and
rerun `compare_csv_baseline.py compare` against the restored file.
