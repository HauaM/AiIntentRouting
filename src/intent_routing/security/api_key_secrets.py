from __future__ import annotations

from collections.abc import Mapping

from intent_routing.config import load_api_key_secret_keyring_config
from intent_routing.db.models import ApiKey
from intent_routing.security.encryption import EncryptedText
from intent_routing.security.keyring import RawTextKeyring


def load_api_key_secret_keyring(
    environ: Mapping[str, str] | None = None,
) -> RawTextKeyring:
    config = load_api_key_secret_keyring_config(environ)
    return RawTextKeyring.from_values(
        active_key_id=config.active_key_id,
        active_kek_base64=config.active_kek_base64,
        legacy_keks=config.legacy_keks,
    )


def api_key_secret_encryption_context(
    *,
    service_id: str,
    key_id: str,
) -> dict[str, str]:
    return {
        "purpose": "api_key_secret",
        "service_id": service_id,
        "key_id": key_id,
    }


def encrypted_api_key_secret(api_key: ApiKey) -> EncryptedText | None:
    if (
        api_key.secret_ciphertext is None
        or api_key.secret_encrypted_dek is None
        or api_key.secret_encrypted_dek_iv is None
        or api_key.secret_encrypted_dek_auth_tag is None
        or api_key.secret_key_id is None
        or api_key.secret_iv is None
        or api_key.secret_auth_tag is None
        or api_key.secret_algorithm is None
    ):
        return None
    return EncryptedText(
        ciphertext=api_key.secret_ciphertext,
        encrypted_dek=api_key.secret_encrypted_dek,
        encrypted_dek_iv=api_key.secret_encrypted_dek_iv,
        encrypted_dek_auth_tag=api_key.secret_encrypted_dek_auth_tag,
        key_id=api_key.secret_key_id,
        iv=api_key.secret_iv,
        auth_tag=api_key.secret_auth_tag,
        algorithm=api_key.secret_algorithm,
    )


def apply_encrypted_api_key_secret(api_key: ApiKey, encrypted: EncryptedText) -> None:
    api_key.secret_ciphertext = encrypted.ciphertext
    api_key.secret_encrypted_dek = encrypted.encrypted_dek
    api_key.secret_encrypted_dek_iv = encrypted.encrypted_dek_iv
    api_key.secret_encrypted_dek_auth_tag = encrypted.encrypted_dek_auth_tag
    api_key.secret_key_id = encrypted.key_id
    api_key.secret_iv = encrypted.iv
    api_key.secret_auth_tag = encrypted.auth_tag
    api_key.secret_algorithm = encrypted.algorithm
