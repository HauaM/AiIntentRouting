"""Application-level envelope encryption for raw text."""

import base64
import binascii
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

AES_GCM_TAG_BYTES = 16
AES_256_KEY_BYTES = 32
AES_GCM_IV_BYTES = 12
ALGORITHM = "AES-256-GCM"


@dataclass(frozen=True, slots=True)
class EncryptedText:
    ciphertext: bytes
    encrypted_dek: bytes
    key_id: str
    iv: bytes
    auth_tag: bytes
    algorithm: str
    encrypted_dek_iv: bytes
    encrypted_dek_auth_tag: bytes


class EnvelopeEncryptor:
    def __init__(self, *, kek_id: str, kek_base64: str) -> None:
        self._kek_id = kek_id
        self._kek = self._decode_kek(kek_base64)

    def encrypt_text(
        self,
        plaintext: str,
        *,
        context: Mapping[str, str] | None = None,
    ) -> EncryptedText:
        dek = os.urandom(AES_256_KEY_BYTES)
        text_iv = os.urandom(AES_GCM_IV_BYTES)
        dek_iv = os.urandom(AES_GCM_IV_BYTES)
        associated_data = self._associated_data(self._kek_id, ALGORITHM, context)

        text_ciphertext_with_tag = AESGCM(dek).encrypt(
            text_iv,
            plaintext.encode("utf-8"),
            associated_data,
        )
        ciphertext, auth_tag = self._split_ciphertext_and_tag(text_ciphertext_with_tag)

        encrypted_dek_with_tag = AESGCM(self._kek).encrypt(
            dek_iv,
            dek,
            associated_data,
        )
        encrypted_dek, encrypted_dek_auth_tag = self._split_ciphertext_and_tag(
            encrypted_dek_with_tag
        )

        return EncryptedText(
            ciphertext=ciphertext,
            encrypted_dek=encrypted_dek,
            key_id=self._kek_id,
            iv=text_iv,
            auth_tag=auth_tag,
            algorithm=ALGORITHM,
            encrypted_dek_iv=dek_iv,
            encrypted_dek_auth_tag=encrypted_dek_auth_tag,
        )

    def decrypt_text(
        self,
        encrypted: EncryptedText,
        *,
        context: Mapping[str, str] | None = None,
    ) -> str:
        if encrypted.algorithm != ALGORITHM:
            raise ValueError("encrypted text algorithm mismatch")
        if encrypted.key_id != self._kek_id:
            raise ValueError("encrypted text key_id mismatch")
        self._validate_envelope(encrypted)

        associated_data = self._associated_data(
            encrypted.key_id,
            encrypted.algorithm,
            context,
        )
        encrypted_dek_with_tag = encrypted.encrypted_dek + encrypted.encrypted_dek_auth_tag
        dek = AESGCM(self._kek).decrypt(
            encrypted.encrypted_dek_iv,
            encrypted_dek_with_tag,
            associated_data,
        )
        ciphertext_with_tag = encrypted.ciphertext + encrypted.auth_tag
        plaintext = AESGCM(dek).decrypt(
            encrypted.iv,
            ciphertext_with_tag,
            associated_data,
        )
        return plaintext.decode("utf-8")

    @staticmethod
    def _decode_kek(kek_base64: str) -> bytes:
        try:
            kek = base64.b64decode(kek_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("kek_base64 must be valid base64") from exc
        if len(kek) != AES_256_KEY_BYTES:
            raise ValueError("kek_base64 must decode to 32 bytes")
        return kek

    @staticmethod
    def _split_ciphertext_and_tag(ciphertext_with_tag: bytes) -> tuple[bytes, bytes]:
        return (
            ciphertext_with_tag[:-AES_GCM_TAG_BYTES],
            ciphertext_with_tag[-AES_GCM_TAG_BYTES:],
        )

    @staticmethod
    def _validate_envelope(encrypted: EncryptedText) -> None:
        if len(encrypted.iv) != AES_GCM_IV_BYTES:
            raise ValueError("encrypted text iv must be 12 bytes")
        if len(encrypted.encrypted_dek_iv) != AES_GCM_IV_BYTES:
            raise ValueError("encrypted DEK iv must be 12 bytes")
        if len(encrypted.auth_tag) != AES_GCM_TAG_BYTES:
            raise ValueError("encrypted text auth_tag must be 16 bytes")
        if len(encrypted.encrypted_dek_auth_tag) != AES_GCM_TAG_BYTES:
            raise ValueError("encrypted DEK auth_tag must be 16 bytes")
        if len(encrypted.encrypted_dek) != AES_256_KEY_BYTES:
            raise ValueError("encrypted DEK ciphertext must be 32 bytes")

    @staticmethod
    def _associated_data(
        key_id: str,
        algorithm: str,
        context: Mapping[str, str] | None,
    ) -> bytes:
        base = f"key_id={key_id};algorithm={algorithm}"
        if context is None:
            return base.encode()
        encoded_context = json.dumps(
            dict(context),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return f"{base};context={encoded_context}".encode()
