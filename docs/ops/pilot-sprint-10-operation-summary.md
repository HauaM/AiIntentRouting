# Sprint 10 Pilot Operation Summary

## Status

- Date/timezone: 2026-07-01 to 2026-07-02, Asia/Seoul.
- Initial Stage 0 operation-start HEAD: `f186297b1a9a0960f95eeacc85ddd47a06029000`.
- BGE Stage 0 and Stage 1 operation-start HEAD: `3b1e6c2e3fa6b33685d8e2b88555a2a5f146658e`.
- Stage 2 preflight HEAD: `85fcdaf35460caf4fa1946bf005d8886fc097374`.
- Stage 2A fallback-window check HEAD:
  `7102708fcdc0784d57f4e217cd634f723f447526`.
- Service identifier: `it-helpdesk-pilot-sprint10-operation-monitoring`.
- Summary scope: Stage 0 pre-window, Stage 1 operator traffic, Stage 2
  preflight, and Stage 2A fallback-window readiness check.
- Recommendation value: hold.
- Admin UI implementation: excluded.
- Runtime evidence committed: no.

## Stage Result

| stage | cap | actual requests | result |
| --- | ---: | ---: | --- |
| 0 pre-window | 0 | 0 | completed |
| 1 operator traffic | 10 | 10 | completed |
| 2 preflight | 0 | 0 | completed |
| 2A fallback-window readiness | 15 | 0 | held |
| 2 limited user traffic | 50 | 0 | held |
| 3 one-business-day traffic | 100 | 0 | not started |

Stage 1 was initially held because the first local Stage 0 run used
`emb-fake-v1`. The operator then confirmed the local BGE-M3 path as
`/home/haua/workspace/models/embedded/bge-m3`, and the Stage 0 BGE package,
benchmark, readiness, and ops evidence were regenerated before Stage 1 traffic.
Stage 1 was capped at 10 internal operator requests and did not exceed the cap.

Stage 2 preflight completed after the primary-window cutoff. The primary window
required preflight completion by 2026-07-01 13:00 Asia/Seoul, but preflight was
captured at 2026-07-01 13:19 Asia/Seoul. Stage 2A traffic was not opened. Use
the fallback window, 2026-07-02 10:30-14:30 Asia/Seoul, and rerun final
readiness immediately before sending Stage 2A requests.

Stage 2A fallback-window readiness was attempted on 2026-07-02, Asia/Seoul.
BGE package verification and branch protection capture passed, but the
operator-managed runtime at `http://127.0.0.1:8002` was not reachable and the
operator shell did not provide the required admin token and database URL for
ops evidence export. Stage 2A traffic was not opened.

## Readiness And Release

- Stage 2 preflight readiness status: ready.
- Database check: ok.
- Alembic check: ok.
- pgvector check: ok.
- Active release version: `rel-it-helpdesk-pilot-sprint10-operation-monitoring-20260701-001`.
- Active release environment: `dev`.
- Initial active release model version observed in Stage 0: `emb-fake-v1`.
- BGE active release model version observed in Stage 0 and Stage 1:
  `emb-bge-m3-local`.
- BGE model path: `/home/haua/workspace/models/embedded/bge-m3`.
- BGE model package SHA-256:
  `7a680f2c38c16cfee81e29cfc04320271c95496c9b4ec119a6672672535019d3`.
- BGE embedding dimension: 1024.
- BGE benchmark p95: 2862 ms for the local 50-query benchmark.
- Stage 2 preflight active release model version: `emb-bge-m3-local`.
- Stage 2 preflight readiness: ready.
- Stage 2A fallback-window runtime readiness: not reachable on port 8002.
- Stage 2A pre-traffic ops evidence export: not run because required operator
  environment variables were missing.

## Monitoring Snapshot

- Runtime request count: 10.
- Stage 2 preflight request count: 0.
- Stage 2A request count: 0.
- Runtime error count: 0.
- Latency p50: 227 ms.
- Latency p95: 252 ms.
- Latency max: 252 ms.
- Decision counts: confident 8, clarify 1, fallback 1, off-topic 0, risk 0.
- Combined fallback, clarify, and off-topic rate: 20 percent.
- Top route keys: `it.api_timeout.manual_lookup` 3,
  `it.vpn_access.ticket_create` 3, `it.password_reset.self_service` 2.
- Rollback used: no.
- Stage 2A rollback used: no, because traffic was not opened.

## Dify And BGE Status

- Dify Sprint 9 accepted caller record: `DIFY-HTTP-SMOKE-SPRINT9-20260701-001`.
- Dify operator decision: no extra Dify integration test was required for this
  local operator window because Dify is an HTTP caller for `/v1/intent-route`.
- Dify Stage 1 result: direct HTTP-shape operator requests were used; no Dify
  workflow export, screenshot, or external workflow payload was committed.
- Dify Stage 2 preflight result: no Stage 2 traffic was sent; Dify remains an
  HTTP caller boundary for `/v1/intent-route`.
- Dify Stage 2A result: no Stage 2A traffic was sent because final readiness
  did not pass.
- BGE Sprint 9 accepted status: measured-pass.
- BGE Stage 0 local runtime observation: the active model version was
  `emb-bge-m3-local`.
- BGE Stage 1 result: completed with BGE-M3 active, error count 0, and runtime
  p95 below the 2000 ms stop threshold.
- BGE Stage 2 preflight result: BGE-M3 package SHA matched, active release
  model was `emb-bge-m3-local`, and preflight request count remained 0.
- BGE Stage 2A pre-traffic result: package SHA matched before traffic, but
  runtime readiness and ops evidence export did not pass.

## Branch Protection

- Main branch protection checked: yes.
- Required status check: `verify`.
- Strict required status checks: true.
- Enforce admins: true.

## Local Evidence

Runtime evidence remains local under ignored paths.

| artifact | sha256 |
| --- | --- |
| `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/pre-window/ops/ops-evidence.json` | `9ce73522f999efd351e4d2d3164724aa1173142980ce4bf4729d1307244cfe04` |
| `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/pre-window/ops/ops-evidence.md` | `4a998cd24a836b5363fdb3c9c2a751c2379cc04f5a1e07446b236bd8c9048e77` |
| `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage0-bge/bge-package/bge-m3-package.json` | `b64bc76cea7d2416f3a92b9a7e41e7e7e34b882d34154f9e235c5308f910652e` |
| `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage0-bge/bge-benchmark/bge-m3-benchmark.json` | `afee437a935b5a49ec3b99dadf01bff6e3d4fc3b6f19218ee38701826c03efce` |
| `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage0-bge/ops/ops-evidence.json` | `2bcb8ec519008825b119a79cb80f158ff6a67458912d797cf1730ec90da63d80` |
| `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage1-operator/ops-final/ops-evidence.json` | `cd262f69c0bd83c61969b37f23a558c65a521a4a883f6456c1e08daa029776bf` |
| `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/preflight/bge-package/bge-m3-package.json` | `b64bc76cea7d2416f3a92b9a7e41e7e7e34b882d34154f9e235c5308f910652e` |
| `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/preflight/ops/ops-evidence.json` | `d10ccbcc69099e1291fd275b0789fb1657374d94cd263b22fe7c1452c95ea227` |
| `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/stage2a/pre-traffic/bge-package/bge-m3-package.json` | `b64bc76cea7d2416f3a92b9a7e41e7e7e34b882d34154f9e235c5308f910652e` |
| `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/stage2a/pre-traffic/bge-package/bge-m3-package.md` | `ef2fd02cfef4e9fc75bd0d27973c7cb13d06a8a5822e76a03cd500c8335ed077` |
| `var/evidence/it-helpdesk-pilot-sprint10-operation-monitoring/stage2/stage2a/pre-traffic/branch-protection/main-protection.json` | `b66b29244c88978eb155eb03e15debad59e9ff87e4ed2e01571753664977255e` |

## Secret-Safety Boundary

This summary contains only aggregate counts, status values, official identifiers,
local evidence paths, and hashes. It does not inline runtime request payloads,
raw user text, credential material, Dify screenshots or workflow exports,
runtime logs, local state file contents, or secret material.
