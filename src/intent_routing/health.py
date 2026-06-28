from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from functools import lru_cache
from pathlib import Path
from typing import Literal

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.orm import Session

CheckState = Literal["ok", "failed", "skipped"]
ReadinessPayload = dict[str, str | dict[str, CheckState]]
SessionFactory = Callable[[], AbstractContextManager[Session]]

ROOT = Path(__file__).resolve().parents[2]


def build_readiness_payload(session_factory: SessionFactory) -> ReadinessPayload:
    checks: dict[str, CheckState] = {
        "database": "skipped",
        "alembic": "skipped",
        "pgvector": "skipped",
    }

    if not check_database(session_factory):
        checks["database"] = "failed"
        return {"status": "not_ready", "checks": checks}
    checks["database"] = "ok"

    checks["alembic"] = "ok" if check_alembic_head(session_factory) else "failed"
    checks["pgvector"] = "ok" if check_pgvector(session_factory) else "failed"

    status = "ready" if all(value == "ok" for value in checks.values()) else "not_ready"
    return {"status": status, "checks": checks}


def check_database(session_factory: SessionFactory) -> bool:
    try:
        with session_factory() as session:
            session.execute(text("SELECT 1")).scalar_one()
    except Exception:
        return False
    return True


def check_alembic_head(session_factory: SessionFactory) -> bool:
    try:
        with session_factory() as session:
            version = session.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
    except Exception:
        return False
    return version == _alembic_head_revision()


def check_pgvector(session_factory: SessionFactory) -> bool:
    try:
        with session_factory() as session:
            installed = session.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            ).scalar_one_or_none()
    except Exception:
        return False
    return installed == 1


@lru_cache(maxsize=1)
def _alembic_head_revision() -> str:
    config = Config(str(ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    head = script.get_current_head()
    if head is None:
        raise RuntimeError("Alembic head revision is not configured.")
    return head
