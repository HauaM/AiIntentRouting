import base64
import json

import pytest

from intent_routing.config import (
    MissingRawTextKekError,
    RawTextKeyringConfig,
    load_raw_text_keyring_config,
)
from intent_routing.security.encryption import EnvelopeEncryptor
from intent_routing.security.keyring import RawTextKeyring


def _kek(byte: bytes = b"0") -> str:
    return base64.b64encode(byte * 32).decode("ascii")


def test_keyring_encrypts_with_active_key_and_decrypts_legacy_key() -> None:
    legacy = EnvelopeEncryptor(kek_id="old-kek", kek_base64=_kek(b"1"))
    encrypted = legacy.encrypt_text("보험금 청구 010-1234-5678")

    keyring = RawTextKeyring.from_values(
        active_key_id="new-kek",
        active_kek_base64=_kek(b"2"),
        legacy_keks={"old-kek": _kek(b"1")},
    )

    assert keyring.decrypt_text(encrypted) == "보험금 청구 010-1234-5678"
    assert keyring.encrypt_text("new text").key_id == "new-kek"


def test_keyring_rejects_unknown_encrypted_key_id() -> None:
    legacy = EnvelopeEncryptor(kek_id="old-kek", kek_base64=_kek(b"1"))
    encrypted = legacy.encrypt_text("보험금 청구")
    keyring = RawTextKeyring.from_values(
        active_key_id="new-kek",
        active_kek_base64=_kek(b"2"),
        legacy_keks={},
    )

    with pytest.raises(ValueError, match="key_id"):
        keyring.decrypt_text(encrypted)


@pytest.mark.parametrize(
    ("active_key_id", "legacy_keks", "expected_message"),
    [
        ("", {}, "active_key_id"),
        ("new-kek", {"": _kek(b"1")}, "legacy key_id"),
    ],
)
def test_keyring_rejects_missing_key_ids(
    active_key_id: str,
    legacy_keks: dict[str, str],
    expected_message: str,
) -> None:
    with pytest.raises(ValueError, match=expected_message):
        RawTextKeyring.from_values(
            active_key_id=active_key_id,
            active_kek_base64=_kek(b"2"),
            legacy_keks=legacy_keks,
        )


@pytest.mark.parametrize(
    ("active_kek_base64", "legacy_keks"),
    [
        ("not base64!!!", {}),
        (_kek(b"2"), {"old-kek": "not base64!!!"}),
    ],
)
def test_keyring_rejects_invalid_base64_key_material(
    active_kek_base64: str,
    legacy_keks: dict[str, str],
) -> None:
    with pytest.raises(ValueError, match="base64"):
        RawTextKeyring.from_values(
            active_key_id="new-kek",
            active_kek_base64=active_kek_base64,
            legacy_keks=legacy_keks,
        )


def test_keyring_rejects_duplicate_active_and_legacy_key_id() -> None:
    with pytest.raises(ValueError, match="active key_id"):
        RawTextKeyring.from_values(
            active_key_id="same-kek",
            active_kek_base64=_kek(b"2"),
            legacy_keks={"same-kek": _kek(b"1")},
        )


def test_keyring_reports_key_ids_with_active_key_first() -> None:
    keyring = RawTextKeyring.from_values(
        active_key_id="new-kek",
        active_kek_base64=_kek(b"2"),
        legacy_keks={"old-kek": _kek(b"1"), "older-kek": _kek(b"3")},
    )

    assert list(keyring.key_ids()) == ["new-kek", "old-kek", "older-kek"]
    assert keyring.active_key_id == "new-kek"


def test_keyring_and_config_repr_do_not_expose_key_material() -> None:
    active_kek = _kek(b"2")
    legacy_kek = _kek(b"1")
    config = RawTextKeyringConfig(
        active_key_id="new-kek",
        active_kek_base64=active_kek,
        legacy_keks={"old-kek": legacy_kek},
    )
    keyring = RawTextKeyring.from_values(
        active_key_id=config.active_key_id,
        active_kek_base64=config.active_kek_base64,
        legacy_keks=config.legacy_keks,
    )

    rendered = f"{config!r} {keyring!r}"

    assert "new-kek" in rendered
    assert "old-kek" in rendered
    assert active_kek not in rendered
    assert legacy_kek not in rendered


def test_load_raw_text_keyring_config_reads_env_with_defaults() -> None:
    config = load_raw_text_keyring_config(
        {
            "RAW_TEXT_KEK_BASE64": _kek(b"2"),
        }
    )

    assert config == RawTextKeyringConfig(
        active_key_id="local-kek-001",
        active_kek_base64=_kek(b"2"),
        legacy_keks={},
    )


def test_load_raw_text_keyring_config_reads_legacy_json() -> None:
    config = load_raw_text_keyring_config(
        {
            "RAW_TEXT_KEK_ID": "new-kek",
            "RAW_TEXT_KEK_BASE64": _kek(b"2"),
            "RAW_TEXT_LEGACY_KEKS_JSON": json.dumps({"old-kek": _kek(b"1")}),
        }
    )

    assert config.legacy_keks == {"old-kek": _kek(b"1")}


def test_load_raw_text_keyring_config_normalizes_whitespace_padded_legacy_key_id() -> None:
    config = load_raw_text_keyring_config(
        {
            "RAW_TEXT_KEK_ID": "new-kek",
            "RAW_TEXT_KEK_BASE64": _kek(b"2"),
            "RAW_TEXT_LEGACY_KEKS_JSON": json.dumps({" old-kek ": _kek(b"1")}),
        }
    )

    assert config.legacy_keks == {"old-kek": _kek(b"1")}


def test_load_raw_text_keyring_config_requires_active_kek() -> None:
    with pytest.raises(MissingRawTextKekError, match="RAW_TEXT_KEK_BASE64"):
        load_raw_text_keyring_config({})


@pytest.mark.parametrize(
    "legacy_json",
    [
        "not json",
        "[]",
        '{"old-kek": 1}',
    ],
)
def test_load_raw_text_keyring_config_rejects_invalid_legacy_json(
    legacy_json: str,
) -> None:
    with pytest.raises(ValueError, match="RAW_TEXT_LEGACY_KEKS_JSON"):
        load_raw_text_keyring_config(
            {
                "RAW_TEXT_KEK_ID": "new-kek",
                "RAW_TEXT_KEK_BASE64": _kek(b"2"),
                "RAW_TEXT_LEGACY_KEKS_JSON": legacy_json,
            }
        )


def test_load_raw_text_keyring_config_rejects_blank_legacy_key_id() -> None:
    with pytest.raises(ValueError, match="legacy key_id"):
        load_raw_text_keyring_config(
            {
                "RAW_TEXT_KEK_ID": "new-kek",
                "RAW_TEXT_KEK_BASE64": _kek(b"2"),
                "RAW_TEXT_LEGACY_KEKS_JSON": json.dumps({" ": _kek(b"1")}),
            }
        )


def test_load_raw_text_keyring_config_rejects_normalized_duplicate_legacy_key_ids() -> None:
    with pytest.raises(ValueError, match="duplicate legacy key_id"):
        load_raw_text_keyring_config(
            {
                "RAW_TEXT_KEK_ID": "new-kek",
                "RAW_TEXT_KEK_BASE64": _kek(b"2"),
                "RAW_TEXT_LEGACY_KEKS_JSON": json.dumps(
                    {
                        "old-kek": _kek(b"1"),
                        " old-kek ": _kek(b"2"),
                    }
                ),
            }
        )


def test_load_raw_text_keyring_config_rejects_duplicate_active_legacy_key_id() -> None:
    with pytest.raises(ValueError, match="active key_id"):
        load_raw_text_keyring_config(
            {
                "RAW_TEXT_KEK_ID": "same-kek",
                "RAW_TEXT_KEK_BASE64": _kek(b"2"),
                "RAW_TEXT_LEGACY_KEKS_JSON": json.dumps({"same-kek": _kek(b"1")}),
            }
        )


def test_load_raw_text_keyring_config_rejects_active_legacy_duplicate_with_whitespace() -> None:
    with pytest.raises(ValueError, match="active key_id"):
        load_raw_text_keyring_config(
            {
                "RAW_TEXT_KEK_ID": " same-kek ",
                "RAW_TEXT_KEK_BASE64": _kek(b"2"),
                "RAW_TEXT_LEGACY_KEKS_JSON": json.dumps({" same-kek ": _kek(b"1")}),
            }
        )
