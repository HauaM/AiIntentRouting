from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from os import environ

SESSION_TOKEN_HASH_ALGORITHM = "sha256"
ADMIN_SESSION_COOKIE_NAME = "irt_admin_session"
ADMIN_SESSION_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24
ADMIN_SESSION_COOKIE_SECURE_ENV = "ADMIN_SESSION_COOKIE_SECURE"


def create_admin_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_admin_session_token(token: str) -> str:
    if not token.strip():
        raise ValueError("admin session token must not be blank")
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"{SESSION_TOKEN_HASH_ALGORITHM}:{digest}"


def verify_admin_session_token(token: str, token_hash: str) -> bool:
    if not token.strip() or not token_hash.startswith(f"{SESSION_TOKEN_HASH_ALGORITHM}:"):
        return False
    return hmac.compare_digest(hash_admin_session_token(token), token_hash)


def admin_session_expires_at(*, hours: int = 0, days: int = 0) -> datetime:
    if hours <= 0 and days <= 0:
        raise ValueError("admin session expiry duration must be positive")
    return datetime.now(UTC) + timedelta(hours=hours, days=days)


def admin_session_cookie_secure() -> bool:
    configured = environ.get(ADMIN_SESSION_COOKIE_SECURE_ENV)
    if configured is not None:
        return configured.strip().lower() in {"1", "true", "yes", "on"}

    environment = environ.get("INTENT_ROUTING_ENVIRONMENT", "local").strip().lower()
    return environment in {"pilot", "prod", "production"}
