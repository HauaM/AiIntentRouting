# Intent Routing Service

폐쇄망 금융 환경의 Dify 연동을 위한 Intent Routing API와 운영자용 Admin UI입니다.

## 로컬 실행

### 사전 준비

- Python 3.12 이상
- [uv](https://docs.astral.sh/uv/)
- Docker 및 Docker Compose
- Node.js와 pnpm (`pnpm`이 없으면 Corepack 사용 가능)

처음 실행할 때 Python 및 프론트엔드 의존성을 설치합니다.

```bash
uv sync --dev
cd frontend/intent-routing-console
pnpm install
cd ../..
```

pnpm을 직접 설치하지 않았다면 `pnpm` 대신 `corepack pnpm`을 사용할 수 있습니다.

### Ubuntu에서 전체 개발 환경 한 번에 실행

`run_local_dev_stack.sh`는 Bash 4 이상의 Ubuntu/Linux 개발 환경용입니다. 저장소 루트에서 다음 명령을 실행합니다.

```bash
./scripts/run_local_dev_stack.sh
```

이 스크립트는 다음 작업을 자동으로 수행합니다.

1. PostgreSQL 컨테이너 시작 및 준비 상태 확인
2. DB 마이그레이션 적용
3. 백엔드 API 시작 및 샘플 서비스 생성
4. Admin UI 시작

실행 후 접속 주소와 기본 계정은 다음과 같습니다.

| 항목 | 주소 또는 값 |
| --- | --- |
| Admin UI | <http://127.0.0.1:30140> |
| Backend API | <http://127.0.0.1:30141> |
| API 상태 확인 | <http://127.0.0.1:30141/healthz> |
| PostgreSQL | `127.0.0.1:30142` |
| 기본 관리자 이메일 | `local-admin@example.com` |
| 기본 관리자 비밀번호 | `local-admin-password` |

종료하려면 실행한 터미널에서 `Ctrl+C`를 누릅니다. PostgreSQL 컨테이너까지 종료하려면 별도로 다음 명령을 실행합니다.

```bash
docker compose stop postgres
```

> 기본 계정과 키는 로컬 개발 전용입니다. 공유 환경이나 운영 환경에서 사용하지 마세요.

### 환경 변수 변경

원클릭 실행 스크립트는 로컬 개발용 기본값을 제공하며, 필요한 값만 실행 전에 덮어쓸 수 있습니다.

```bash
BACKEND_PORT=8011 \
FRONTEND_PORT=8010 \
ADMIN_SYSTEM_ADMIN_EMAIL=admin@example.com \
ADMIN_SYSTEM_ADMIN_PASSWORD='change-me' \
./scripts/run_local_dev_stack.sh
```

이미 다른 `system_admin` 계정이 DB에 있으면 기존 단일 소유자를 보존합니다. 기존 계정의 비밀번호를 바꾸려면 해당 이메일을 `ADMIN_SYSTEM_ADMIN_EMAIL`로 지정하고 새 비밀번호를 함께 전달하세요.

### macOS에서 전체 개발 환경 한 번에 실행

macOS에서는 zsh 전용 실행 스크립트를 사용합니다. 저장소 루트에서 다음 명령을 실행합니다.

```bash
./scripts/run_local_dev_stack_macos.sh
```

스크립트는 `.env`를 자동으로 읽고 Colima, PostgreSQL, 마이그레이션, 백엔드와 Admin UI를 순서대로 준비합니다. 한 터미널에서 백엔드는 청록색 `[backend]`, 프론트엔드는 보라색 `[frontend]`로 표시됩니다. `Ctrl+C`를 누르면 백엔드와 프론트엔드는 종료되지만 PostgreSQL 컨테이너와 데이터는 유지됩니다.

### macOS 수동 실행 및 문제 진단

원클릭 스크립트의 특정 단계가 실패할 때만 아래 절차로 PostgreSQL, 백엔드와 프론트엔드를 각각 실행해 진단합니다.

#### 1. PostgreSQL 실행

저장소 루트에서 실행합니다.

```bash
colima start
docker context use colima
docker compose up -d postgres
docker compose exec postgres pg_isready -U intent -d intent_routing
```

`accepting connections`가 출력되면 DB가 준비된 것입니다.

#### 2. 백엔드 실행

새 터미널을 열고 저장소 루트에서 환경 변수를 설정한 뒤 마이그레이션과 API를 실행합니다.

```bash
export DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing
export APP_ENV=local
export ALLOWED_RUNTIME_ENVIRONMENTS=dev,qa,prod
export ADMIN_AUTH_MODE=trusted_headers
export ADMIN_BOOTSTRAP_TOKEN=local-admin-token
export ADMIN_SYSTEM_ADMIN_EMAIL=local-admin@example.com
export ADMIN_SYSTEM_ADMIN_PASSWORD=local-admin-password
export ADMIN_SYSTEM_ADMIN_DISPLAY_NAME='Local Admin'
export RAW_TEXT_KEK_ID=local-kek-001
export RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
export RAW_TEXT_LEGACY_KEKS_JSON='{}'
export EMBEDDING_PROVIDER=fake
export SERVICE_ID=it-helpdesk-pilot-$(date +%Y%m%d%H%M%S)

uv sync --dev
uv run alembic upgrade head
uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 30141
```

백엔드 상태 확인:

```bash
curl -s http://127.0.0.1:30141/healthz
```

정상 응답은 `{"status":"ok"}`입니다. API를 종료하려면 백엔드 터미널에서 `Ctrl+C`를 누릅니다.

기존 DB에 다른 `system_admin`이 있으면 `ADMIN_SYSTEM_ADMIN_EMAIL`을 기존 관리자 이메일로 변경하세요. 새 이메일로 단일 관리자 소유권을 자동 이전하지 않습니다.

#### 3. 최초 샘플 서비스 생성

새 DB를 처음 사용하는 경우 백엔드가 실행 중인 상태에서 다른 터미널을 열고 다음 명령을 한 번 실행합니다. 이미 해당 서비스가 생성되어 있다면 생략할 수 있습니다.

```bash
export ADMIN_BOOTSTRAP_TOKEN=local-admin-token
export SERVICE_ID=it-helpdesk-pilot-sprint10-operation-monitoring
export STATE_PATH="var/pilot/${SERVICE_ID}.state.secret.json"

uv run python scripts/seed_pilot.py \
  --base-url http://127.0.0.1:30141 \
  --admin-token "${ADMIN_BOOTSTRAP_TOKEN}" \
  --service-id ${SERVICE_ID} \
  --environment dev \
  --state-path "${STATE_PATH}"
```

저장된 상태 파일로 Dify diagnostic 검증을 실행할 때는 `uv run python scripts/run_dify_smoke_matrix.py --state ${STATE_PATH}`를 사용합니다.

`STATE_PATH` 파일에는 비밀 값이 포함될 수 있으므로 Git에 추가하거나 외부로 공유하지 마세요.

#### 4. 프론트엔드 실행

별도 터미널에서 실행합니다. `dev:local`은 Admin UI를 `30140` 포트에서 열고 `/admin/v1` 요청을 `30141`의 백엔드로 전달합니다.

```bash
cd frontend/intent-routing-console
pnpm install
pnpm dev:local
```

브라우저에서 <http://127.0.0.1:30140>에 접속하고 다음 계정으로 로그인합니다.

| 항목 | 값 |
| --- | --- |
| 이메일 | `local-admin@example.com` |
| 비밀번호 | `local-admin-password` |

프론트엔드를 종료하려면 프론트엔드 터미널에서 `Ctrl+C`를 누릅니다. PostgreSQL까지 중지하려면 저장소 루트에서 `docker compose stop postgres`를 실행합니다.

## DB 환경 구성

로컬 DB는 `compose.yaml`의 `pgvector/pgvector:pg16` 이미지를 사용합니다. 기본 구성은 다음과 같습니다.

| 항목 | 기본값 |
| --- | --- |
| 호스트/포트 | `127.0.0.1:30142` |
| 데이터베이스 | `intent_routing` |
| 사용자/비밀번호 | `intent` / `intent` |
| 접속 문자열 | `postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing` |
| 데이터 볼륨 | `postgres_data` |

DB만 준비하려면 다음 명령을 실행합니다.

```bash
docker compose up -d postgres
docker compose ps postgres
docker compose exec postgres pg_isready -U intent -d intent_routing
uv run alembic upgrade head
```

마이그레이션 상태와 로그는 다음과 같이 확인합니다.

```bash
uv run alembic current
docker compose logs postgres
```

컨테이너를 정지하거나 삭제해도 named volume의 데이터는 유지됩니다.

```bash
docker compose stop postgres       # 정지만 수행
docker compose down                # 컨테이너 삭제, DB 데이터 유지
```

DB를 완전히 초기화해야 할 때만 아래 명령을 사용합니다. 이 명령은 로컬 DB 데이터를 모두 삭제합니다.

```bash
docker compose down -v
docker compose up -d postgres
uv run alembic upgrade head
```

외부 PostgreSQL을 사용하려면 pgvector 확장을 사용할 수 있는 PostgreSQL을 준비하고 `DATABASE_URL`을 변경합니다. `DATABASE_URL`이 기본값과 다르면 원클릭 실행 스크립트는 Compose PostgreSQL을 자동으로 시작하거나 관리하지 않습니다.

```bash
DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST:PORT/DB_NAME' \
./scripts/run_local_dev_stack.sh
```

## 임베딩 모델 구성

### 개발 기본값: fake 임베딩

원클릭 로컬 실행은 기본적으로 `EMBEDDING_PROVIDER=fake`를 사용합니다. 모델 파일이나 추가 ML 의존성이 필요 없고 결과가 결정적이므로 UI 개발과 자동 테스트에 적합하지만, 실제 BGE-M3 품질을 검증하는 용도는 아닙니다.

### 실제 BGE-M3 사용

이 프로젝트의 실제 임베딩 모델은 CPU 기반 BGE-M3이며 1024차원 dense vector를 생성합니다. 런타임은 모델을 다운로드하지 않으므로, 승인된 모델 디렉터리를 실행 전에 로컬 머신 또는 폐쇄망 호스트에 준비해야 합니다.

먼저 임베딩 선택 의존성을 설치합니다.

```bash
uv sync --dev --extra embedding
```

모델이 예를 들어 `/absolute/path/to/bge-m3`에 있다면 패키지를 검증합니다. 승인된 SHA-256이 없으면 `--expected-sha256`을 생략하고 생성된 보고서의 값을 별도 승인 기록과 비교합니다.

```bash
export BGE_M3_MODEL_SHA256='승인된-64자리-SHA256으로-교체'

uv run python scripts/verify_bge_m3_package.py \
  --model-path /absolute/path/to/bge-m3 \
  --out-dir var/benchmarks \
  --expected-sha256 "${BGE_M3_MODEL_SHA256}"
```

검증한 모델로 전체 개발 환경을 실행합니다.

```bash
EMBEDDING_PROVIDER=bge-m3 \
BGE_M3_MODEL_PATH=/absolute/path/to/bge-m3 \
BGE_M3_MODEL_SHA256="${BGE_M3_MODEL_SHA256}" \
BGE_M3_BATCH_SIZE=16 \
BGE_M3_MAX_TOKENS=256 \
./scripts/run_local_dev_stack.sh
```

실제 트래픽 연결 전에는 동일한 호스트에서 벤치마크를 실행합니다.

```bash
EMBEDDING_PROVIDER=bge-m3 \
BGE_M3_MODEL_PATH=/absolute/path/to/bge-m3 \
BGE_M3_BATCH_SIZE=16 \
uv run python scripts/benchmark_bge_m3.py \
  --model-path /absolute/path/to/bge-m3 \
  --csv docs/pilot/it-helpdesk-pilot-cases.csv \
  --max-tokens 256 \
  --repeats 3 \
  --out-dir var/benchmarks
```

정상 보고서의 주요 기준은 `dimension=1024`, `batch_size=16`, `max_tokens=256`입니다. 메모리 또는 지연 시간이 과도하면 `BGE_M3_BATCH_SIZE`를 낮춘 후 다시 측정하세요.

Compose 기반 폐쇄망 실행에서는 승인된 모델을 호스트의 `/models/bge-m3`에 배치합니다. `api` 서비스가 이를 컨테이너의 같은 경로에 읽기 전용으로 마운트하며, 환경 파일에는 다음 값을 설정합니다.

```dotenv
EMBEDDING_PROVIDER=bge-m3
BGE_M3_MODEL_PATH=/models/bge-m3
BGE_M3_MODEL_SHA256=승인된-64자리-SHA256으로-교체
BGE_M3_BATCH_SIZE=16
BGE_M3_MAX_TOKENS=256
```

모델 반입, 체크섬 증적, CPU 벤치마크와 폐쇄망 승인 절차는 `docs/ops/bge-m3-closed-network.md`를 참고하세요.

### 백엔드만 수동 실행

Admin UI가 필요하지 않을 때 사용합니다.

```bash
export DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing
export APP_ENV=local
export ALLOWED_RUNTIME_ENVIRONMENTS=dev,qa,prod
export ADMIN_AUTH_MODE=trusted_headers
export ADMIN_BOOTSTRAP_TOKEN=local-admin-token
export RAW_TEXT_KEK_ID=local-kek-001
export RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
export EMBEDDING_PROVIDER=fake

docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 8000
```

다른 터미널에서 상태를 확인합니다.

```bash
curl -s http://127.0.0.1:8000/healthz
```

정상 응답은 `{"status":"ok"}`입니다. 전체 환경 변수 목록은 `.env.example`을 참고하세요.

## 테스트 및 정적 검사

PostgreSQL을 시작한 상태에서 다음 명령을 실행합니다.

```bash
uv run ruff check .
uv run mypy src tests
TEST_DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing uv run pytest -v

cd frontend/intent-routing-console
pnpm typecheck
pnpm test:unit
```

CI와 동일한 상세 검증 절차는 `docs/ops/ci-verification.md`를 참고하세요.

## 파일 구조

```text
src/intent_routing/                 백엔드 애플리케이션
frontend/intent-routing-console/    Admin UI
alembic/                            DB 마이그레이션
scripts/                            로컬 실행 및 운영 스크립트
tests/                              백엔드 테스트
docs/                               운영·연동 문서
```

## 주요 문서

운영 증적을 별도로 수집해야 할 때는 `scripts/export_ops_evidence.py`를 사용하며 결과는 `ops-evidence.json`과 `ops-evidence.md`로 생성됩니다. 증적 묶음은 `docs/ops/pilot-evidence-bundle-checklist.md`를 Sprint 6 review standard로 삼아 검토하고, 하위 명령은 실패 원인을 찾는 diagnostic 용도로만 사용합니다.

- macOS Docker/Colima/Portainer 구성: `docs/ops/macos-colima-docker-setup.md`
- 로컬 실행 상세 가이드: `docs/ops/intent-routing-local-runbook.md`
- CI 검증: `docs/ops/ci-verification.md`
- 브랜치 보호 설정: `docs/ops/branch-protection.md`
- 폐쇄망 배포: `docs/ops/closed-network-deployment.md`
- BGE-M3 폐쇄망 구성: `docs/ops/bge-m3-closed-network.md`
- 파일럿 실행: `docs/ops/intent-routing-pilot-runbook.md`
- 파일럿 리허설: `docs/ops/pilot-rehearsal.md`
- 파일럿 증적 검토: `docs/ops/pilot-evidence-bundle-checklist.md`
- 파일럿 출시 준비: `docs/ops/pilot-launch-readiness-checklist.md`
- 파일럿 인계 티켓: `docs/ops/pilot-handoff-release-ticket-template.md`
- Dify 연동: `docs/integrations/dify-http-request-node.md`
- 보안 수명주기: `docs/ops/security-lifecycle.md`
- 보안 운영: `docs/ops/security-operations.md`
