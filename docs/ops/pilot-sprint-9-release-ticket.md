# Sprint 9 Release Ticket

Official sanitized release ticket for Sprint 9 Go reassessment.

Runtime evidence is not committed. Evidence links only.

## Release Scope

- Date/timezone: 2026-06-30, Asia/Seoul.
- SERVICE_ID: it-helpdesk-pilot-sprint9-go-reassessment.
- Admin UI implementation: excluded.
- Local evidence root: var/evidence/it-helpdesk-pilot-sprint9-go-reassessment.
- Sprint 9 plan commit: 4630f05.
- Base main closure: d45c099cb3e1598cd8e30d8b133e18ece5bbf15e.

## Local Rehearsal Evidence

- Local rehearsal status: PASS.
- final_status: PASS.
- secret_scan.passed: true.
- Manifest path: var/evidence/it-helpdesk-pilot-sprint9-go-reassessment/rehearsal/pilot-rehearsal-manifest.md.
- Manifest JSON SHA256: b645a3322a41b6314641446131aca37160ee86b6027f9f92ca6851091c1519b6.
- Manifest Markdown SHA256: 051856591452adeb96ec45d785ee679f018942948e5f2a87dda8531176566441.
- Reviewer checks: JSON format pass, no local secret state in rehearsal evidence, forbidden marker scan no matches.

## BGE Reassessment Evidence

- BGE closed-network: measured-pass.
- BGE catalog scope protection PR: https://github.com/HauaM/AiIntentRouting/pull/10.
- BGE PR head commit: 9eee8728d620414b41ba93a1e34544a3b2286569.
- BGE PR merge commit: 9cdf90b4b1d6ecaed4635c54de8433a2b9f394f8.
- BGE PR CI verify: PASS.
- BGE measured evidence root: var/evidence/it-helpdesk-pilot-bge-scope-protection-20260630/rehearsal.
- BGE measured final_status: PASS.
- BGE package preflight: PASS.
- BGE benchmark: PASS.
- BGE Dify smoke matrix: PASS.
- BGE CSV baseline comparison: PASS.
- BGE measured manifest JSON SHA256: 605cd1899057bce080da52863ee21d0e9c322cd94809ef4874e28debebe3ffdb.
- BGE measured manifest Markdown SHA256: 1d2afc114cbc1f0d45cd8aa8876d493d1b2112a1ecc10cbf25fd16a8eeb2b12a.

## Dify HTTP Caller Evidence

- Dify integration status: accepted by HTTP smoke matrix.
- Dify approval ID: DIFY-HTTP-SMOKE-SPRINT9-20260701-001.
- Approval actor: pilot-test-manager.
- Actor roles: system_admin.
- Review timestamp: 2026-07-01, Asia/Seoul.
- Evidence path: var/evidence/it-helpdesk-pilot-bge-scope-protection-20260630/rehearsal/dify/dify-smoke-matrix.md.
- Boundary: Dify must remain a pass-through HTTP caller for `/v1/intent-route`.

## CSV Freeze Approval

- CSV baseline freeze: approved.
- Freeze approval ID: CSV-FREEZE-SPRINT9-20260701-001.
- Approval actor: pilot-test-manager.
- Actor roles: system_admin.
- Release owner: pilot-test-manager.
- QA/security reviewer: pilot-test-manager.
- Review timestamp: 2026-07-01, Asia/Seoul.
- Refresh status: refresh not approved.
- Comparison result: CSV baseline comparison PASS.
- Accepted behavior change: none.

## Branch Protection Evidence

- Branch protection: accepted.
- Branch protection approval ID: BRANCH-PROTECTION-SPRINT9-20260701-001.
- Authorized operator: HauaM.
- Operator permission result: authorized.
- Repository visibility: public.
- Review timestamp: 2026-07-01, Asia/Seoul.
- Rule snapshot path: var/evidence/it-helpdesk-pilot-sprint9-go-reassessment/branch-protection/main-protection.json.
- Rule snapshot SHA256: b66b29244c88978eb155eb03e15debad59e9ff87e4ed2e01571753664977255e.
- Verification output: branch protection capture verified.
- Required status check: `verify` API context, displayed in GitHub as `CI / verify`.
- Branch protection settings: `strict: true`, `enforce_admins: true`.
- Rollback or temporary bypass used: no.
- Final branch protection state: confirmed.

## Blocked Gates

- None.

## Evidence Links Only

- Official closure: docs/ops/pilot-sprint-9-execution-closure.md.
- Go/no-go decision: docs/ops/pilot-sprint-9-go-no-go-decision.md.
- Local evidence index: var/evidence/it-helpdesk-pilot-sprint9-go-reassessment/sprint-9-go-reassessment-index.md.
- Runtime evidence, screenshots, workflow exports, and local secret state are not committed.

## Go Reassessment

- Decision value: Go.
- Pilot traffic approved.
- Conditional Go is not required because all required gates have accepted evidence.
