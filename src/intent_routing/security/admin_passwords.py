from __future__ import annotations

from intent_routing.security.api_keys import hash_secret, verify_secret


def hash_admin_password(password: str) -> str:
    return hash_secret(password)


def verify_admin_password(password: str, password_hash: str) -> bool:
    return verify_secret(password, password_hash)
