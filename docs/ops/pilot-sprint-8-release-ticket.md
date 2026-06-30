# Sprint 8 Release Ticket

Official sanitized release ticket for Sprint 8 Pilot Execution & Evidence Capture.

runtime evidence is not committed. Evidence links only.

## Release Scope

- Date/timezone: 2026-06-30, Asia/Seoul.
- SERVICE_ID: it-helpdesk-pilot-sprint8-local.
- Admin UI implementation: excluded.
- Local evidence root: var/evidence/it-helpdesk-pilot-sprint8-local.
- Local execution commit: 32b611e2b05e240e1726ae6a733b6305cd4ff0ac.

## Code And CI Refs

- Sprint 8 plan PR: https://github.com/HauaM/AiIntentRouting/pull/7.
- PR #7 merge commit on main: ce33ff250de27721f272e35a27253d24a08ad3c3.
- PR #7 CI verify: pass, https://github.com/HauaM/AiIntentRouting/actions/runs/28421845592/job/84216398277.

## Local Rehearsal Evidence

- Local rehearsal status: PASS.
- secret_scan.passed: true.
- Rehearsal note: 127.0.0.1:55432 schema drift 확인 후 fresh isolated Postgres 127.0.0.1:55433 에서 재실행했다.
- Manifest JSON SHA256: c0cdb9dc11b581d7eab1613ee0f6241c34791eded41ae90a8824e3e713a7dd37.
- Manifest Markdown SHA256: e9f13d33ea07d3621604c2a80e7c4b04036a053bd7e01de72985c714ceb1352e.

## Blocked Gates

- Dify UI dry-run: blocked. UI access 없음, workflow version identifier 미제공, reviewer 미배정, screenshot/workflow export 미첨부.
- BGE closed-network: pending-host-access. Traffic 미승인, host/model path 및 model SHA 없음, measured-pass 미실행, exception approval ID/owner/next measurement date 없음.
- Branch protection: blocked. GitHub API capture attempted, HTTP 403/operator-not-permitted, valid main-protection.json snapshot 없음, structured verification output 없음.
- CSV baseline: comparison PASS. Checked-in baseline frozen, freeze approval ID/release owner/QA or security reviewer 미제공.

## Evidence Links Only

- Local evidence root: var/evidence/it-helpdesk-pilot-sprint8-local.
- Official closure: docs/ops/pilot-sprint-8-execution-closure.md.
- Go/no-go decision: docs/ops/pilot-sprint-8-go-no-go-decision.md.
- Runtime evidence, screenshots, workflow exports, and local secret state are not committed.
