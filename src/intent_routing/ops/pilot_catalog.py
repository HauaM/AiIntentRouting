from __future__ import annotations

import csv
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from intent_routing.domain.enums import ThresholdPreset
from intent_routing.domain.schemas import validate_route_key
from intent_routing.testing.csv_runner import (
    CLASSIFICATION_CSV_COLUMNS,
    CSV_COLUMNS,
    CsvValidationError,
    ParsedTestCase,
    parse_test_cases_csv,
)


class PilotIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    route_key: str
    include_keywords: list[str] = Field(min_length=1)
    exclude_keywords: list[str] = Field(default_factory=list)
    positive_examples: list[str] = Field(min_length=1)
    negative_examples: list[str] = Field(default_factory=list)

    @field_validator("route_key")
    @classmethod
    def route_key_must_be_valid(cls, value: str) -> str:
        return validate_route_key(value)


class PilotCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    app_id: str = Field(min_length=1)
    threshold_preset: ThresholdPreset = ThresholdPreset.balanced
    intents: list[PilotIntent] = Field(min_length=1)
    off_topic_keywords: list[str] = Field(default_factory=list)
    off_topic_message: str = "서비스 범위 밖 문의입니다."


def load_pilot_catalog(path: Path) -> PilotCatalog:
    with path.open(encoding="utf-8") as handle:
        return PilotCatalog.model_validate(json.load(handle))


def load_pilot_cases(path: Path) -> list[ParsedTestCase]:
    assert_csv_header(path)
    return parse_test_cases_csv(path.read_text(encoding="utf-8"))


def assert_csv_header(path: Path) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise CsvValidationError(f"CSV header must be {CSV_COLUMNS}") from exc
    if header not in (CLASSIFICATION_CSV_COLUMNS, CSV_COLUMNS):
        raise CsvValidationError(
            f"CSV header must be {CLASSIFICATION_CSV_COLUMNS} or {CSV_COLUMNS}"
        )
