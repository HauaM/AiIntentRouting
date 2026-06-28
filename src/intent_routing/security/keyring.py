from __future__ import annotations

from collections.abc import Mapping, Sequence

from intent_routing.config import load_raw_text_keyring_config
from intent_routing.security.encryption import EncryptedText, EnvelopeEncryptor


class RawTextKeyring:
    def __init__(
        self,
        *,
        active_key_id: str,
        encryptors: Mapping[str, EnvelopeEncryptor],
    ) -> None:
        self._active_key_id = active_key_id
        self._encryptors = dict(encryptors)

    @classmethod
    def from_values(
        cls,
        *,
        active_key_id: str,
        active_kek_base64: str,
        legacy_keks: Mapping[str, str],
    ) -> RawTextKeyring:
        active_key_id = active_key_id.strip()
        if not active_key_id:
            raise ValueError("active_key_id must not be blank")
        if active_key_id in legacy_keks:
            raise ValueError("active key_id must not appear in legacy_keks")

        encryptors: dict[str, EnvelopeEncryptor] = {
            active_key_id: EnvelopeEncryptor(
                kek_id=active_key_id,
                kek_base64=active_kek_base64,
            )
        }
        for raw_key_id, kek_base64 in legacy_keks.items():
            key_id = raw_key_id.strip()
            if not key_id:
                raise ValueError("legacy key_id must not be blank")
            if key_id in encryptors:
                raise ValueError("active key_id must not appear in legacy_keks")
            encryptors[key_id] = EnvelopeEncryptor(
                kek_id=key_id,
                kek_base64=kek_base64,
            )
        return cls(active_key_id=active_key_id, encryptors=encryptors)

    @property
    def active_key_id(self) -> str:
        return self._active_key_id

    def key_ids(self) -> Sequence[str]:
        return tuple(self._encryptors)

    def encrypt_text(self, plaintext: str) -> EncryptedText:
        return self._encryptors[self._active_key_id].encrypt_text(plaintext)

    def decrypt_text(self, encrypted: EncryptedText) -> str:
        encryptor = self._encryptors.get(encrypted.key_id)
        if encryptor is None:
            raise ValueError("No KEK configured for encrypted text key_id")
        return encryptor.decrypt_text(encrypted)

    def __repr__(self) -> str:
        return (
            "RawTextKeyring("
            f"active_key_id={self._active_key_id!r}, "
            f"key_ids={tuple(self._encryptors)!r})"
        )


def load_raw_text_keyring(
    environ: Mapping[str, str] | None = None,
) -> RawTextKeyring:
    config = load_raw_text_keyring_config(environ)
    return RawTextKeyring.from_values(
        active_key_id=config.active_key_id,
        active_kek_base64=config.active_kek_base64,
        legacy_keks=config.legacy_keks,
    )
