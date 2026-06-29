from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from os import environ as process_environ
from typing import Any

DEFAULT_RAW_TEXT_KEK_ID = "local-kek-001"


class RawTextKeyringConfigError(ValueError):
    pass


class MissingRawTextKekError(RawTextKeyringConfigError):
    pass


@dataclass(frozen=True, slots=True)
class RawTextKeyringConfig:
    active_key_id: str
    active_kek_base64: str = field(repr=False)
    legacy_keks: dict[str, str] = field(default_factory=dict, repr=False)

    def __repr__(self) -> str:
        legacy_key_ids = tuple(self.legacy_keks)
        return (
            "RawTextKeyringConfig("
            f"active_key_id={self.active_key_id!r}, "
            f"legacy_key_ids={legacy_key_ids!r})"
        )


def load_raw_text_keyring_config(
    environ: Mapping[str, str] | None = None,
) -> RawTextKeyringConfig:
    env = process_environ if environ is None else environ
    active_key_id = env.get("RAW_TEXT_KEK_ID", DEFAULT_RAW_TEXT_KEK_ID).strip()
    if not active_key_id:
        raise ValueError("RAW_TEXT_KEK_ID must not be blank")
    active_kek_base64 = env.get("RAW_TEXT_KEK_BASE64")
    if active_kek_base64 is None or not active_kek_base64.strip():
        raise MissingRawTextKekError("RAW_TEXT_KEK_BASE64 is required")
    legacy_keks = _parse_legacy_keks(env.get("RAW_TEXT_LEGACY_KEKS_JSON", "{}"))
    if active_key_id in legacy_keks:
        raise ValueError("active key_id must not appear in RAW_TEXT_LEGACY_KEKS_JSON")
    return RawTextKeyringConfig(
        active_key_id=active_key_id,
        active_kek_base64=active_kek_base64,
        legacy_keks=legacy_keks,
    )


def _parse_legacy_keks(legacy_json: str) -> dict[str, str]:
    try:
        parsed: Any = json.loads(legacy_json)
    except json.JSONDecodeError as exc:
        raise ValueError("RAW_TEXT_LEGACY_KEKS_JSON must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("RAW_TEXT_LEGACY_KEKS_JSON must be a JSON object")
    legacy_keks: dict[str, str] = {}
    for raw_key_id, kek_base64 in parsed.items():
        if not isinstance(raw_key_id, str) or not isinstance(kek_base64, str):
            raise ValueError(
                "RAW_TEXT_LEGACY_KEKS_JSON must map key ID strings to base64 strings"
            )
        key_id = raw_key_id.strip()
        if not key_id:
            raise ValueError("legacy key_id must not be blank")
        if key_id in legacy_keks:
            raise ValueError("duplicate legacy key_id in RAW_TEXT_LEGACY_KEKS_JSON")
        legacy_keks[key_id] = kek_base64
    return legacy_keks
