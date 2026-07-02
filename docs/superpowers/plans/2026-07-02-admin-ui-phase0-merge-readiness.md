# Admin UI Phase 0 Merge Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare the Sprint 11 Admin UI Phase 0 console for safe main integration through a reviewed PR.

**Architecture:** Keep the Admin UI as a separate Umi Max frontend app under `frontend/intent-routing-console`, backed by existing Admin API read endpoints. Before integration, verify the runtime-log security path with one real masked runtime event, then stage only source/docs files and keep generated artifacts, secret state, and evidence output out of git.

**Tech Stack:** Python backend with `uv`, FastAPI, PostgreSQL on `127.0.0.1:55432`, Umi Max 4, React 18, Ant Design 5, ProComponents, pnpm via Corepack, frontend port `30140`, backend port `30141`.

---

All paths are relative to `/home/haua/workspace/AiIntentRouting`.

## Scope

In scope:
- Verify Admin UI Phase 0 runtime log behavior with a real runtime request.
- Verify Runtime Logs displays `query_masked` only, never raw query fields.
- Re-run frontend and backend verification before staging.
- Stage only intended Admin UI source, lockfile/config, `.gitignore`, and Admin UI plan docs.
- Create a commit on `codex/admin-ui-phase0`.
- Push and open a PR for main integration.

Out of scope:
- Direct local merge to `main`.
- Phase 1 write flows.
- Phase 2 raw/original query approval or decrypt UI.
- Committing `var/`, `var/pilot`, `var/evidence`, `.umi`, `.umi-production`, `dist`, `node_modules`, or secret state files.
- Staging unrelated `docs/superpowers/plans/2026-07-02-intent-routing-sprint-10-stage2a-execution.md` unless the user explicitly says it belongs to this PR.

## File Structure

- Read: `frontend/intent-routing-console/src/components/RuntimeLogsTable.tsx`
  - Confirm runtime detail drawer only renders decision, route, and masked query.
- Read: `frontend/intent-routing-console/src/services/adminServices.ts`
  - Confirm Runtime Logs list calls `/runtime-logs` with `limit` and never asks for raw query.
- Read: `frontend/intent-routing-console/src/app.tsx`
  - Confirm Admin API headers use `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`, and `X-Service-Scope`.
- Read: `var/pilot/it-helpdesk-pilot-sprint10-operation-monitoring.state.local.json`
  - Use only as a local ignored runtime secret state file; never stage it or print the API key.
- Stage: `.gitignore`
  - Includes frontend generated-directory ignores.
- Stage: `docs/superpowers/plans/2026-07-01-admin-ui-phase0-polish.md`
  - Documents the polish work already executed.
- Stage: `docs/superpowers/plans/2026-07-02-admin-ui-phase0-merge-readiness.md`
  - Documents this merge readiness plan.
- Stage: `frontend/intent-routing-console/**`
  - Source, config, package metadata, tests, and lockfile only; ignored generated directories stay out.

---

### Task 1: Workspace And Intentional-File Audit

**Files:**
- Read: `.gitignore`
- Read: `frontend/intent-routing-console/package.json`
- Read: `frontend/intent-routing-console/src/app.tsx`
- Read: `frontend/intent-routing-console/src/services/adminServices.ts`
- Read: `frontend/intent-routing-console/src/components/RuntimeLogsTable.tsx`

- [ ] **Step 1: Confirm branch and workspace status**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
git branch --show-current
git status --short --branch
```

Expected:
- Branch is `codex/admin-ui-phase0`.
- Admin UI files are still unstaged or untracked before the final staging step.
- `docs/superpowers/plans/2026-07-02-intent-routing-sprint-10-stage2a-execution.md` may appear as untracked and must remain out of this Admin UI PR unless explicitly approved.

- [ ] **Step 2: Confirm ignored generated and secret paths**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
git check-ignore -v \
  var/pilot \
  var/evidence \
  frontend/intent-routing-console/node_modules \
  frontend/intent-routing-console/dist \
  frontend/intent-routing-console/src/.umi \
  frontend/intent-routing-console/src/.umi-production
```

Expected:
- Every path is ignored.
- Output should cite `.gitignore` rules for `var/`, `frontend/**/node_modules/`, `frontend/**/dist/`, `.umi`, and `.umi-production`.

- [ ] **Step 3: Confirm Admin UI uses allowed Admin API auth headers**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
rg -n "X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope" src/app.tsx src/models src/components src/services
```

Expected:
- `src/app.tsx` contains all four custom Admin API headers.
- Runtime API bearer authentication may exist in backend scripts/docs, but Admin UI source must not use it.

- [ ] **Step 4: Confirm Runtime Logs source has no raw query UI**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
rg -n "query_raw|raw query|original request|decrypt|query_masked" src/components/RuntimeLogsTable.tsx src/services/adminServices.ts
```

Expected:
- `query_masked` appears.
- `query_raw`, raw/original query copy, and decrypt UI do not appear in `RuntimeLogsTable.tsx` or `adminServices.ts`.

---

### Task 2: Runtime Logs Real-Row Security QA

**Files:**
- Read: `scripts/smoke_runtime_dify.py`
- Read: `var/pilot/it-helpdesk-pilot-sprint10-operation-monitoring.state.local.json`
- Read via API: `/admin/v1/services/it-helpdesk-pilot-sprint10-operation-monitoring/runtime-logs`

- [ ] **Step 1: Stop any existing backend on 30141 if it is this project server**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
BACKEND_PID="$(lsof -tiTCP:30141 -sTCP:LISTEN || true)"
if [ -n "$BACKEND_PID" ]; then
  ps -o pid,args= -p "$BACKEND_PID"
fi
```

Expected:
- If the process args contain `intent_routing.main:create_app`, stop that process before Step 2.
- If the process is unrelated, stop and ask before touching it.

If the process is the project backend, run:

```bash
kill "$BACKEND_PID"
```

Expected:
- Port `30141` is free afterward.

- [ ] **Step 2: Start backend on 30141 with runtime environment matching the local pilot state**

Run in a long-running terminal:

```bash
cd /home/haua/workspace/AiIntentRouting
DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:55432/intent_routing \
ADMIN_BOOTSTRAP_TOKEN=local-admin-token \
INTENT_ROUTING_ENVIRONMENT=dev \
RAW_TEXT_KEK_ID=local-kek-001 \
RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= \
EMBEDDING_PROVIDER=fake \
uv run uvicorn intent_routing.main:create_app \
  --factory \
  --host 127.0.0.1 \
  --port 30141
```

Expected:
- Uvicorn starts successfully.
- Backend listens on `127.0.0.1:30141`.
- `INTENT_ROUTING_ENVIRONMENT=dev` matches `var/pilot/it-helpdesk-pilot-sprint10-operation-monitoring.state.local.json`.
- `EMBEDDING_PROVIDER=fake` matches `docs/ops/intent-routing-local-runbook.md`; omitting it makes the backend default to `bge-m3`, which requires a local BGE-M3 model path.

- [ ] **Step 3: Verify the local runtime secret state exists without printing the secret**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
jq -r '{service_id, environment, app_id, key_id, release_version, has_api_key:(.api_key != null)}' \
  var/pilot/it-helpdesk-pilot-sprint10-operation-monitoring.state.local.json
```

Expected:

```json
{
  "service_id": "it-helpdesk-pilot-sprint10-operation-monitoring",
  "environment": "dev",
  "app_id": "dify-platform",
  "key_id": "key_live_8c1e6b15e1c649679d757eb8548f921a",
  "release_version": "rel-it-helpdesk-pilot-sprint10-operation-monitoring-20260701-001",
  "has_api_key": true
}
```

Do not print `.api_key`.

- [ ] **Step 4: Create one runtime log with PII that should be masked**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run python scripts/smoke_runtime_dify.py \
  --base-url http://127.0.0.1:30141 \
  --state var/pilot/it-helpdesk-pilot-sprint10-operation-monitoring.state.local.json \
  --query 'API timeout 500 에러가 납니다 전화 010-1234-5678' \
  --expect-decision confident \
  --expect-route-key it.api_timeout.manual_lookup \
  --request-id "admin-ui-phase0-merge-readiness-$(date +%Y%m%d%H%M%S)"
```

Expected:
- Command exits 0.
- JSON response includes `decision: "confident"` and `route_key: "it.api_timeout.manual_lookup"`.
- Response does not include the raw query text.

- [ ] **Step 5: Confirm Admin Runtime Logs returns masked query only**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
curl -sS \
  -H 'X-Admin-Token: local-admin-token' \
  -H 'X-Actor-Id: admin-user' \
  -H 'X-Actor-Roles: system_admin' \
  -H 'X-Service-Scope: it-helpdesk-pilot-sprint10-operation-monitoring' \
  'http://127.0.0.1:30141/admin/v1/services/it-helpdesk-pilot-sprint10-operation-monitoring/runtime-logs?limit=5' \
  | jq '.[0] | {trace_id, request_id, query_masked, decision, route_key, has_query_raw: has("query_raw"), has_query_raw_ciphertext: has("query_raw_ciphertext"), has_original_text: has("original_text")}'
```

Expected:

```json
{
  "trace_id": "<latest trace id>",
  "request_id": "admin-ui-phase0-merge-readiness-<timestamp>",
  "query_masked": "API timeout 500 에러가 납니다 전화 010-****-5678",
  "decision": "confident",
  "route_key": "it.api_timeout.manual_lookup",
  "has_query_raw": false,
  "has_query_raw_ciphertext": false,
  "has_original_text": false
}
```

- [ ] **Step 6: Verify the UI can render the new Runtime Logs row**

Run the frontend if it is not already running:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm exec max setup
corepack pnpm dev:local
```

Open:

```text
http://127.0.0.1:30140/runtime-logs
```

Manual expected result:
- Runtime Logs table shows a row for the new request.
- `Masked query` shows `010-****-5678`.
- Clicking the row opens a drawer with decision, route, and masked query.
- Drawer does not show raw/original query text, decrypt controls, approve controls, or copy-raw controls.

---

### Task 3: Full Automated Verification

**Files:**
- Verify: backend and frontend source tree.

- [ ] **Step 1: Stop frontend dev server before build verification**

If `corepack pnpm dev:local` is running, stop it with `Ctrl-C`.

Then verify port 30140 is free or intentionally stopped:

```bash
lsof -nP -iTCP:30140 -sTCP:LISTEN || true
```

Expected:
- No frontend process is required while running `max build`.
- This avoids `src/.umi` MFSU cache churn during build verification.

- [ ] **Step 2: Run frontend verification**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit
corepack pnpm typecheck
corepack pnpm build
```

Expected:
- `vitest run`: 4 files, 11 tests pass.
- `tsc --noEmit`: exit 0.
- `max build`: Webpack compiled successfully.

- [ ] **Step 3: Run backend/runtime regression suite**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest -q
```

Expected:
- Test suite exits 0.
- Previously observed healthy baseline was `348 passed, 126 skipped`; count may increase only if new tests were added intentionally.

- [ ] **Step 4: Run Admin UI forbidden-pattern scan**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Axios|Authorization: Bearer|server pagination|live polling" src config package.json
```

Expected:
- No output.
- Transitive lockfile packages are not a source violation; direct source/package usage would be a violation.
- The source scan includes `Axios` so Umi request configuration does not import axios-named types directly.

- [ ] **Step 5: Restart frontend dev server for final browser check**

Run in a long-running terminal:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm exec max setup
corepack pnpm dev:local
```

Expected:
- Frontend listens on `http://127.0.0.1:30140`.
- No `.umi/umi.ts` MFSU error appears after compile settles.

---

### Task 4: Manual Browser QA Checklist

**Files:**
- No file changes.

- [ ] **Step 1: Verify Dashboard**

Open:

```text
http://127.0.0.1:30140/dashboard
```

Expected:
- If session token is missing, only the session-required warning is shown for data panels.
- After saving Admin token `local-admin-token`, metrics load.
- `Latency p95` displays `-` when API returns `null`.
- Service environment tag is `local` after saving the session with `Environment=local`.

- [ ] **Step 2: Verify Intent Catalog**

Open:

```text
http://127.0.0.1:30140/intents
```

Expected:
- Read-only intent list loads.
- Detail drawer opens from `상세`.
- No create, edit, delete, release, approve, or reject controls are visible.

- [ ] **Step 3: Verify Runtime Logs**

Open:

```text
http://127.0.0.1:30140/runtime-logs
```

Expected:
- Recent runtime log row from Task 2 is visible.
- `Masked query` contains `010-****-5678`.
- Row drawer shows decision, route, and masked query only.
- No raw/original query text and no Phase 2 decrypt action are visible.
- Phase 2 notice remains disabled/informational.

- [ ] **Step 4: Verify Audit Logs**

Open:

```text
http://127.0.0.1:30140/audit-logs
```

Expected:
- Audit logs load.
- `recorded` tag is readable and visually softer than the previous strong green.
- Long target IDs truncate with tooltip.
- No edit, delete, export, approve, or reject controls are visible.

---

### Task 5: Stage, Commit, Push, And PR

**Files:**
- Stage: `.gitignore`
- Stage: `docs/superpowers/plans/2026-07-01-admin-ui-phase0-polish.md`
- Stage: `docs/superpowers/plans/2026-07-02-admin-ui-phase0-merge-readiness.md`
- Stage: `frontend/intent-routing-console/**`
- Do not stage: `docs/superpowers/plans/2026-07-02-intent-routing-sprint-10-stage2a-execution.md`
- Do not stage: `var/**`
- Do not stage: frontend generated directories.

- [ ] **Step 1: Stage only intended files**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
git add \
  .gitignore \
  docs/superpowers/plans/2026-07-01-admin-ui-phase0-polish.md \
  docs/superpowers/plans/2026-07-02-admin-ui-phase0-merge-readiness.md \
  frontend/intent-routing-console
```

Expected:
- Source/config/test/lock files under `frontend/intent-routing-console` are staged.
- Ignored generated files remain unstaged.
- Unrelated `docs/superpowers/plans/2026-07-02-intent-routing-sprint-10-stage2a-execution.md` remains untracked.

- [ ] **Step 2: Inspect staged files**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
git diff --cached --stat
git diff --cached --name-only | sed -n '1,240p'
```

Expected:
- Staged files are limited to Admin UI frontend, `.gitignore`, and the two Admin UI plan docs.

- [ ] **Step 3: Block forbidden staged paths**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
if git diff --cached --name-only | rg -n '(^var/|node_modules|/dist/|/src/\.umi|/src/\.umi-production|\.secret\.json|\.state\.local\.json)'; then
  echo "Forbidden generated/secret path staged"
  exit 1
else
  echo "Staged paths clean"
fi
```

Expected:

```text
Staged paths clean
```

- [ ] **Step 4: Commit**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
git commit -m "feat: add admin ui phase 0 console"
```

Expected:
- Commit succeeds on `codex/admin-ui-phase0`.

- [ ] **Step 5: Push branch**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
git push -u origin codex/admin-ui-phase0
```

Expected:
- Branch is pushed to origin.

- [ ] **Step 6: Create PR body**

Run:

```bash
cat > /tmp/admin-ui-phase0-pr.md <<'EOF'
## Summary
- Add Sprint 11 Admin UI Phase 0 console under `frontend/intent-routing-console`.
- Implement read-only Dashboard, Intent Catalog, Runtime Logs, and Audit Logs using Umi Max, Ant Design, and ProComponents.
- Keep Phase 1 writes and Phase 2 raw/original text flows disabled or absent.

## Security / Phase Boundaries
- Admin UI uses `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`, and `X-Service-Scope`.
- Runtime Logs display `query_masked` only.
- No React Query, axios, fake pagination, fake live polling, or Admin bearer auth was added.
- `var/`, secret state, generated frontend output, and evidence files are not staged.

## Verification
- `corepack pnpm test:unit`
- `corepack pnpm typecheck`
- `corepack pnpm build`
- `uv run pytest -q`
- Runtime Logs real-row masked-query QA with phone masking
- Route/API smoke on Dashboard, Intent Catalog, Runtime Logs, and Audit Logs at `127.0.0.1:30140`
- Pending before undraft/merge: manual visual browser QA on Dashboard, Intent Catalog, Runtime Logs, and Audit Logs
EOF
```

Expected:
- `/tmp/admin-ui-phase0-pr.md` contains the PR body.

- [ ] **Step 7: Open draft PR**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
gh pr create \
  --draft \
  --base main \
  --head codex/admin-ui-phase0 \
  --title "feat: add Admin UI Phase 0 console" \
  --body-file /tmp/admin-ui-phase0-pr.md
```

Expected:
- Draft PR is created against `main`.

---

## Self-Review

Spec coverage:
- Main integration concern is addressed by a PR flow, not direct merge.
- Runtime Logs real-data gap is covered by Task 2.
- Phase 0 UI manual QA is covered by Task 4.
- Full frontend/backend verification is covered by Task 3.
- Staging safety and generated/secret file exclusion are covered by Task 5.
- Existing unrelated untracked Stage 2A plan file is explicitly excluded from this Admin UI PR.

Placeholder scan:
- No `TBD`, `TODO`, `implement later`, or fill-in placeholders are present.
- Commands use concrete paths, ports, service IDs, and expected outputs.

Phase boundary check:
- No Phase 1 write flow is added.
- No Phase 2 decrypt/raw-original query flow is enabled.
- Runtime Logs verification explicitly checks `query_masked` and absence of raw query fields.
