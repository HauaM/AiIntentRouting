FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY src ./src

RUN uv sync --locked --extra embedding --no-dev

RUN useradd --create-home --shell /usr/sbin/nologin app \
    && chown -R app:app /app

USER app

EXPOSE 8000

CMD uv run uvicorn intent_routing.main:create_app --factory --host 0.0.0.0 --port 8000
