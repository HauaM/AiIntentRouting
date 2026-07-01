# Sprint 10 Pilot Operation Summary

## Status

- Date/timezone: 2026-07-01, Asia/Seoul.
- Initial Stage 0 operation-start HEAD: `f186297b1a9a0960f95eeacc85ddd47a06029000`.
- BGE Stage 0 and Stage 1 operation-start HEAD: `3b1e6c2e3fa6b33685d8e2b88555a2a5f146658e`.
- Service identifier: `it-helpdesk-pilot-sprint10-operation-monitoring`.
- Summary scope: Stage 0 pre-window and Stage 1 operator traffic.
- Recommendation value: continue limited pilot to Stage 2 planning.
- Admin UI implementation: excluded.
- Runtime evidence committed: no.

## Stage Result

| stage | cap | actual requests | result |
| --- | ---: | ---: | --- |
| 0 pre-window | 0 | 0 | completed |
| 1 operator traffic | 10 | 10 | completed |
| 2 limited user traffic | 50 | 0 | not started |
| 3 one-business-day traffic | 100 | 0 | not started |

Stage 1 was initially held because the first local Stage 0 run used
`emb-fake-v1`. The operator then confirmed the local BGE-M3 path as
`/home/haua/workspace/models/embedded/bge-m3`, and the Stage 0 BGE package,
benchmark, readiness, and ops evidence were regenerated before Stage 1 traffic.
Stage 1 was capped at 10 internal operator requests and did not exceed the cap.

## Readiness And Release

- Readiness status: ready.
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

## Monitoring Snapshot

- Runtime request count: 10.
- Runtime error count: 0.
- Latency p50: 227 ms.
- Latency p95: 252 ms.
- Latency max: 252 ms.
- Decision counts: confident 8, clarify 1, fallback 1, off-topic 0, risk 0.
- Combined fallback, clarify, and off-topic rate: 20 percent.
- Top route keys: `it.api_timeout.manual_lookup` 3,
  `it.vpn_access.ticket_create` 3, `it.password_reset.self_service` 2.
- Rollback used: no.

## Dify And BGE Status

- Dify Sprint 9 accepted caller record: `DIFY-HTTP-SMOKE-SPRINT9-20260701-001`.
- Dify operator decision: no extra Dify integration test was required for this
  local operator window because Dify is an HTTP caller for `/v1/intent-route`.
- Dify Stage 1 result: direct HTTP-shape operator requests were used; no Dify
  workflow export, screenshot, or external workflow payload was committed.
- BGE Sprint 9 accepted status: measured-pass.
- BGE Stage 0 local runtime observation: the active model version was
  `emb-bge-m3-local`.
- BGE Stage 1 result: completed with BGE-M3 active, error count 0, and runtime
  p95 below the 2000 ms stop threshold.

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

## Secret-Safety Boundary

This summary contains only aggregate counts, status values, official identifiers,
local evidence paths, and hashes. It does not inline runtime request payloads,
raw user text, credential material, Dify screenshots or workflow exports,
runtime logs, local state file contents, or secret material.
