# Sprint 10 Stage 2 Operation Plan

> **Operations-control document:** This plan prepares Stage 2 only. It does not
> start traffic by itself, does not authorize broad production launch, and does
> not permit committing runtime evidence.

**Goal:** Run a capped Stage 2 limited-user pilot after the accepted Stage 1
operator result, while keeping evidence local and preserving rollback control.

**Architecture:** Stage 2 uses the existing `/v1/intent-route` runtime, the
accepted HTTP caller contract, closed-network BGE-M3, the ops evidence exporter,
and branch protection. The stage is split into a 15-request observation segment
and a 35-request completion segment so the operator can pause before the full
50-request cap is consumed.

**Tech Stack:** Markdown operations records, existing FastAPI runtime and admin
APIs, HTTP caller requests to `/v1/intent-route`, BGE-M3 local model path,
existing ops evidence exporter, GitHub branch protection, repository secret
scan helper.

---

## Control Status

- Date/timezone: 2026-07-01, Asia/Seoul.
- Planning HEAD: `9079108be6e21c4507719750fb7e1aef2b6b4843`.
- Service identifier: `it-helpdesk-pilot-sprint10-operation-monitoring`.
- Stage 1 result: completed.
- Stage 1 cap and actual count: 10 of 10.
- Stage 1 runtime error count: 0.
- Stage 1 runtime p95: 252 ms.
- Stage 1 combined fallback, clarify, and off-topic rate: 20 percent.
- Stage 1 active model: `emb-bge-m3-local`.
- Stage 2 status: planned, not started.
- Admin UI implementation: excluded.
- Runtime evidence commit boundary: runtime evidence must remain uncommitted.

## Operator Window And Cap

Stage 2 remains limited pilot traffic. It is not broad production traffic.

Primary operating window:

- Window: 2026-07-01 13:30-17:30 Asia/Seoul.
- Use only if this Stage 2 plan is merged and preflight is complete by
  2026-07-01 13:00 Asia/Seoul.

Fallback operating window:

- Window: 2026-07-02 10:30-14:30 Asia/Seoul.
- Use when the primary window is missed or any preflight check is not clean.

Stage cap:

- Total cap: 50 requests.
- Audience: limited internal pilot users only.
- Scope: IT helpdesk pilot intents only.
- External or broad production users: not allowed.

Segmented ramp:

| segment | cap | target duration | action |
| --- | ---: | --- | --- |
| Stage 2 preflight | 0 | before window | confirm readiness, BGE, branch protection, and evidence paths |
| Stage 2A observation | 15 | first 60 minutes | pause at 15 requests and review aggregate evidence |
| Stage 2B completion | 35 | remaining 3 hours | continue only if Stage 2A has no stop criteria |

The operator must pause at 15 total Stage 2 requests even if the first segment
looks healthy. The remaining 35 requests can start only after the Stage 2A
checkpoint is accepted.

## Dify Boundary

Dify does not require an extra integration test for Stage 2 because the accepted
contract is that Dify acts as an HTTP caller for `/v1/intent-route`.

Stage 2 still requires operational observation of the HTTP caller contract:

- Requests must target `/v1/intent-route`.
- Request identifiers must be propagated.
- Required headers must be preserved by the caller path.
- Dify workflow exports and screenshots must not be committed.
- If the operator uses direct HTTP-shape requests during local validation, record
  that no external Dify workflow payload was used.

## BGE Boundary

- Required provider: BGE-M3.
- Required active model version: `emb-bge-m3-local`.
- Required model path: `/home/haua/workspace/models/embedded/bge-m3`.
- Required package SHA-256:
  `7a680f2c38c16cfee81e29cfc04320271c95496c9b4ec119a6672672535019d3`.
- Required dimension: 1024.

Stage 2 traffic must not start if the active release reports `emb-fake-v1`, a
missing model path, a wrong provider, a wrong dimension, or route-scope leakage.

## Stage 2A Checkpoint

Capture local ops evidence immediately after 15 Stage 2 requests.

Continue to Stage 2B only when all checkpoint conditions hold:

- Request count is no more than 15 for Stage 2A.
- Runtime error count is 0.
- Latency p95 is below 2000 ms.
- Combined fallback, clarify, and off-topic rate is at or below 30 percent, or
  the cases are explicitly explained as expected pilot traffic.
- Risk count is 0, or every risk result has operator review before continuing.
- Top route keys remain in approved IT helpdesk scope.
- Active model remains `emb-bge-m3-local`.
- Branch protection remains unchanged.
- Runtime evidence remains under ignored `var/` paths.

## Stage 2B Completion

Stage 2B can send at most 35 additional requests, for a Stage 2 total of at most
50 requests. Stop before 50 if any stop criterion is observed.

Stage 2 is accepted only when all final conditions hold:

- Total Stage 2 request count is no more than 50.
- Error rate is below 2 percent.
- Latency p95 is below 2000 ms.
- No repeated timeout or server error branch occurs.
- No authentication, service-scope, active-release, or request-shape error occurs
  after stage configuration is locked.
- Combined fallback, clarify, and off-topic rate is at or below 30 percent, or
  documented as expected pilot traffic.
- No risk result advances without operator review.
- Route keys remain inside approved IT helpdesk scope.
- BGE-M3 path and active release remain normal.
- Branch protection remains unchanged.
- No runtime evidence is staged or prepared for commit.

## Stop And Rollback

Pause Stage 2 immediately when any inherited Sprint 10 stop criterion is met.

Rollback action order:

1. Pause the HTTP caller path that sends pilot traffic.
2. Route limited pilot users to the approved fallback or human handoff path.
3. Capture immediate local ops evidence under the ignored rollback evidence path.
4. Restore the prior approved application image when the image is suspected.
5. Activate the prior known-good release through the admin release rollback flow
   when release state is suspected.
6. Confirm readiness and branch protection after rollback.
7. Write only a secret-safe rollback summary with paths and hashes.

## Evidence Boundary

Allowed local-only paths:

- `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/preflight/`
- `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/stage2a/`
- `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/stage2b/`
- `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/rollback/`
- `var/pilot/`

Official records may include aggregate counts, latency values, decision counts,
safe local evidence paths, hashes, approvals, and final recommendations.

Official records must not include runtime request payloads, raw user text,
credential material, Dify screenshots, Dify workflow exports, runtime logs,
local state contents, API keys, or secret material.

## Stage 2 Summary Requirement

After Stage 2 finishes or pauses, update
`docs/ops/pilot-sprint-10-operation-summary.md` with aggregate-only results.

Required final recommendation values:

- `continue limited pilot to Stage 3 planning`
- `hold`
- `rollback complete`
- `no-go for broader traffic`

Stage 3 planning must not start until the Stage 2 summary is reviewed and the
runtime evidence boundary is verified.
