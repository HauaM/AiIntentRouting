# macOS Docker 환경 구성: Colima, PostgreSQL, Portainer

이 문서는 Docker Desktop 없이 Homebrew, Docker CLI, Docker Compose, Colima를 사용해 macOS에서 이 프로젝트의 PostgreSQL/pgvector를 실행하는 방법을 설명합니다. Portainer CE는 선택적인 로컬 관리 UI로 함께 구성합니다.

## 구성 개요

```text
macOS Docker CLI / Docker Compose
              │
              ▼
       Colima Docker runtime
              │
        ┌─────┴─────┐
        ▼           ▼
 PostgreSQL/pgvector  Portainer CE
 127.0.0.1:30142      https://127.0.0.1:9443
```

Colima가 Linux VM과 Docker daemon을 제공하고, macOS의 Docker CLI와 Compose가 Colima의 Docker context를 통해 컨테이너를 관리합니다. 이 프로젝트에서 우선 Docker로 실행하는 구성 요소는 PostgreSQL/pgvector입니다.

## 전체 개발 환경 실행

최초 도구 설치가 끝난 뒤에는 저장소 루트에서 zsh 전용 스크립트 하나로 로컬 개발 환경을 실행합니다.

```bash
./scripts/run_local_dev_stack_macos.sh
```

스크립트는 `.env`를 자동으로 읽고 다음 작업을 수행합니다.

1. Colima 실행 및 Docker context 선택
2. PostgreSQL 컨테이너 시작과 준비 상태 확인
3. DB 마이그레이션과 로컬 관리자 준비
4. 백엔드와 Admin UI 시작

같은 터미널에서 백엔드 로그는 청록색 `[backend]`, 프론트엔드 로그는 보라색 `[frontend]`로 구분됩니다. 색상을 사용하지 않으려면 다음과 같이 실행합니다.

```bash
NO_COLOR=1 ./scripts/run_local_dev_stack_macos.sh
```

`Ctrl+C`를 누르면 스크립트가 시작한 백엔드, 프론트엔드와 로그 프로세스만 종료합니다. PostgreSQL 컨테이너와 named volume의 데이터는 유지됩니다.

## 1. Homebrew 설치 확인

Homebrew가 없다면 [Homebrew 공식 설치 안내](https://brew.sh/)에 따라 먼저 설치합니다. 설치 여부를 확인합니다.

```bash
brew --version
brew update
```

Apple Silicon Mac에서 `brew`를 찾지 못하면 Homebrew 설치 완료 메시지에 나온 shell 환경 설정 명령을 적용한 뒤 새 터미널을 여세요.

## 2. Docker CLI, Compose, Colima 설치

Docker Desktop은 설치하지 않습니다. 필요한 CLI와 런타임만 Homebrew로 설치합니다.

```bash
brew install docker docker-compose colima
```

Docker Compose Homebrew formula는 Docker CLI plugin입니다. 설치 후 `docker compose`가 인식되지 않으면 `~/.docker/config.json`의 최상위 객체에 Homebrew plugin 경로를 추가합니다.

Apple Silicon 기본 경로:

```json
{
  "cliPluginsExtraDirs": [
    "/opt/homebrew/lib/docker/cli-plugins"
  ]
}
```

Intel Mac 기본 경로:

```json
{
  "cliPluginsExtraDirs": [
    "/usr/local/lib/docker/cli-plugins"
  ]
}
```

이미 `~/.docker/config.json`에 다른 설정이 있다면 파일 전체를 덮어쓰지 말고 `cliPluginsExtraDirs` 항목만 병합하세요. 실제 Homebrew prefix는 다음 명령으로 확인할 수 있습니다.

```bash
brew --prefix
brew --prefix docker-compose
```

설치 결과를 확인합니다.

```bash
docker --version
docker compose version
colima version
```

## 3. Colima 최초 시작

PostgreSQL과 Portainer 중심의 로컬 개발 환경에는 CPU 2개와 메모리 4GiB부터 시작할 수 있습니다. 향후 API, Admin UI 또는 다른 컨테이너를 함께 실행한다면 CPU 4개와 메모리 8GiB로 늘리는 편이 안정적입니다.

처음 생성할 때 다음과 같이 실행합니다.

```bash
colima start --runtime docker --cpu 2 --memory 4 --disk 30
```

이미 기본 profile을 만든 상태라면 디스크 축소를 시도하지 말고 기존 설정으로 시작합니다.

```bash
colima start
```

리소스를 변경하려면 Colima를 중지한 뒤 다시 시작합니다. 디스크 크기는 늘릴 수 있지만 기존 VM의 디스크를 줄일 수는 없습니다.

```bash
colima stop
colima start --runtime docker --cpu 4 --memory 8
```

상태와 Docker context를 확인합니다.

```bash
colima status
docker context ls
docker context show
docker info
```

`docker context show` 결과는 일반적으로 `colima`입니다. 다른 context가 선택되어 있으면 다음과 같이 변경합니다.

```bash
docker context use colima
```

간단한 컨테이너 실행으로 연결을 확인합니다.

```bash
docker run --rm hello-world
```

## 4. 프로젝트 PostgreSQL/pgvector 실행

저장소 루트로 이동합니다.

```bash
cd /path/to/AiIntentRouting
```

현재 프로젝트의 DB 기본값은 다음과 같습니다.

| 항목 | 값 |
| --- | --- |
| 이미지 | `pgvector/pgvector:pg16` |
| macOS 접속 주소 | `127.0.0.1:30142` |
| 컨테이너 포트 | `5432` |
| 데이터베이스 | `intent_routing` |
| 사용자 | `intent` |
| 로컬 비밀번호 | `intent` |
| 데이터 볼륨 | `postgres_data` |

DB 컨테이너를 시작합니다.

```bash
docker compose up -d postgres
```

최초 실행에는 이미지 다운로드 시간이 필요할 수 있습니다. 상태와 준비 여부를 확인합니다.

```bash
docker compose ps postgres
docker compose exec postgres pg_isready -U intent -d intent_routing
docker compose logs postgres
```

정상 상태가 되면 애플리케이션의 DB 접속 문자열은 다음과 같습니다.

```bash
export DATABASE_URL=postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing
```

Python 의존성을 설치하고 마이그레이션을 적용합니다.

```bash
uv sync --dev
uv run alembic upgrade head
uv run alembic current
```

pgvector 확장도 확인할 수 있습니다.

```bash
docker compose exec postgres \
  psql -U intent -d intent_routing \
  -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

애플리케이션 마이그레이션에서 확장을 생성하므로, 마이그레이션 전에는 조회 결과가 비어 있을 수 있습니다.

## 5. DB 중지, 재시작, 초기화

데이터를 보존하면서 DB만 중지하거나 다시 시작합니다.

```bash
docker compose stop postgres
docker compose start postgres
```

컨테이너를 삭제해도 named volume의 DB 데이터는 유지됩니다.

```bash
docker compose down
docker compose up -d postgres
```

DB 데이터를 완전히 삭제하고 처음부터 구성할 때만 `-v`를 사용합니다.

```bash
docker compose down -v
docker compose up -d postgres
uv run alembic upgrade head
```

> `docker compose down -v`는 로컬 PostgreSQL의 모든 프로젝트 데이터를 삭제합니다. 필요한 데이터가 없는지 확인한 뒤 실행하세요.

## 6. Portainer CE 설치

Portainer는 Homebrew 애플리케이션이 아니라 Colima Docker runtime 안에서 컨테이너로 실행합니다. Docker context가 `colima`인지 먼저 확인합니다.

```bash
docker context show
```

Portainer 데이터를 위한 volume을 만들고 LTS 이미지를 실행합니다. 로컬 머신 외부에서 UI에 접근하지 못하도록 `9443`을 `127.0.0.1`에만 바인딩합니다. Edge Agent를 사용하지 않으므로 `8000` 포트는 열지 않습니다.

```bash
docker volume create portainer_data

docker run -d \
  --name portainer \
  --restart=always \
  -p 127.0.0.1:9443:9443 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:lts
```

상태와 로그를 확인합니다.

```bash
docker ps --filter name=portainer
docker logs portainer
```

브라우저에서 <https://127.0.0.1:9443>에 접속해 초기 관리자 계정을 만듭니다. Portainer가 자체 서명 인증서를 사용하므로 브라우저에서 최초 접속 시 인증서 경고가 나타날 수 있습니다.

초기 화면에서 local Docker environment를 선택하면 Colima 안에서 실행 중인 `postgres` 컨테이너와 `postgres_data` volume을 확인할 수 있습니다. Docker socket을 연결한 Portainer 관리자는 모든 컨테이너와 volume을 제어할 수 있으므로 강한 비밀번호를 사용하고 `9443`을 외부 인터페이스에 공개하지 마세요.

Portainer만 중지하거나 다시 시작합니다.

```bash
docker stop portainer
docker start portainer
```

Portainer 컨테이너를 다시 만들어도 `portainer_data` volume을 유지하면 설정이 보존됩니다.

## 7. macOS 재부팅 후 시작

재부팅 후 Colima를 먼저 시작해야 Docker CLI와 `--restart=always` 컨테이너가 동작합니다.

```bash
colima start
docker context use colima
docker compose up -d postgres
```

Colima가 시작되면 Portainer의 `--restart=always` 정책이 적용됩니다. 실행되지 않았다면 다음 명령을 사용합니다.

```bash
docker start portainer
```

전체 상태를 확인합니다.

```bash
colima status
docker compose ps postgres
docker ps --filter name=portainer
```

## 8. 자주 발생하는 문제

### Docker daemon에 연결할 수 없음

```text
Cannot connect to the Docker daemon
```

Colima와 context를 확인합니다.

```bash
colima start
docker context use colima
docker info
```

Docker context를 인식하지 못하는 별도 도구에서만 Colima socket을 직접 지정합니다.

```bash
export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"
```

일반적인 Docker CLI 사용에서는 `DOCKER_HOST`를 설정하지 않고 Colima context를 사용하는 편이 안전합니다.

### `docker compose`가 인식되지 않음

```bash
brew reinstall docker-compose
docker compose version
```

계속 실패하면 2절의 `cliPluginsExtraDirs`가 `brew --prefix` 결과와 일치하는지 확인합니다. `docker-compose` 명령보다 `docker compose` 형식을 사용하세요.

### PostgreSQL 포트 충돌

```text
Bind for 127.0.0.1:30142 failed: port is already allocated
```

포트를 사용하는 프로세스와 컨테이너를 확인합니다.

```bash
lsof -nP -iTCP:30142 -sTCP:LISTEN
docker ps --format 'table {{.Names}}\t{{.Ports}}'
```

기존 PostgreSQL 또는 컨테이너를 중지하거나 `compose.yaml`의 호스트 포트를 변경한 뒤 `DATABASE_URL`도 같은 포트로 변경합니다.

### PostgreSQL 컨테이너가 준비되지 않음

```bash
docker compose ps postgres
docker compose logs --tail=200 postgres
docker compose exec postgres pg_isready -U intent -d intent_routing
```

### Portainer에서 로컬 환경을 볼 수 없음

Portainer와 PostgreSQL이 같은 Colima Docker context에서 실행됐는지 확인합니다.

```bash
docker context show
docker inspect portainer --format '{{json .Mounts}}'
docker ps
```

`/var/run/docker.sock` mount가 없다면 Portainer 컨테이너를 제거한 후 6절의 명령으로 다시 만드세요. `portainer_data` volume은 제거하지 않으면 유지됩니다.

## 공식 참고 자료

- [Colima 설치 및 사용](https://github.com/abiosoft/colima)
- [Colima FAQ와 Docker socket](https://github.com/abiosoft/colima/blob/main/docs/FAQ.md)
- [Homebrew docker formula](https://formulae.brew.sh/formula/docker)
- [Homebrew docker-compose formula](https://formulae.brew.sh/formula/docker-compose)
- [Homebrew colima formula](https://formulae.brew.sh/formula/colima)
- [Portainer CE LTS Docker 설치](https://docs.portainer.io/2.33-lts/start/install-ce/server/docker/linux)
