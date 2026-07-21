from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime

from intent_routing.domain.enums import ErrorCode

PBKDF2_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 210_000
SALT_BYTES = 16


@dataclass(frozen=True)
class ApiKeyRecord:
    key_id: str
    key_hash: str
    key_fingerprint: str
    environment: str
    app_id: str
    service_id: str
    allowed_intents: list[str]
    allowed_route_keys: list[str]
    status: str
    expires_at: datetime | None
    revoked_at: datetime | None


@dataclass(frozen=True)
class ScopeResult:
    allowed: bool
    error_code: ErrorCode | None = None


def generate_api_key_secret() -> str:
    return secrets.token_urlsafe(32)


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(encoded: str) -> bytes:
    padding = "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(f"{encoded}{padding}".encode("ascii"))


def hash_secret(secret: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return "$".join(
        (
            PBKDF2_ALGORITHM,
            str(PBKDF2_ITERATIONS),
            _b64encode(salt),
            _b64encode(digest),
        )
    )


def verify_secret(secret: str, hashed: str) -> bool:
    try:
        algorithm, iterations_raw, salt_raw, digest_raw = hashed.split("$", 3)
        if algorithm != PBKDF2_ALGORITHM:
            return False
        iterations = int(iterations_raw)
        if iterations != PBKDF2_ITERATIONS:
            return False
        salt = _b64decode(salt_raw)
        expected_digest = _b64decode(digest_raw)
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            secret.encode("utf-8"),
            salt,
            iterations,
        )
    except (binascii.Error, ValueError, TypeError):
        return False

    return hmac.compare_digest(actual_digest, expected_digest)


def fingerprint_secret(secret: str) -> str:
    digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    return f"sha256:{digest}:{secret[-4:]}"


def check_scope(
    record: ApiKeyRecord,
    app_id: str,
    service_id: str,
    route_key: str | None,
    intent_id: str | None,
) -> ScopeResult:
    if record.app_id != app_id or record.service_id != service_id:
        return ScopeResult(
            allowed=False,
            error_code=ErrorCode.SERVICE_SCOPE_DENIED,
        )

    if route_key is not None and record.allowed_route_keys:
        if route_key not in record.allowed_route_keys:
            return ScopeResult(
                allowed=False,
                error_code=ErrorCode.SERVICE_SCOPE_DENIED,
            )

    if intent_id is not None and record.allowed_intents:
        if intent_id not in record.allowed_intents:
            return ScopeResult(
                allowed=False,
                error_code=ErrorCode.SERVICE_SCOPE_DENIED,
            )

    return ScopeResult(allowed=True)
