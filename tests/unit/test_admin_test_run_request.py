import pytest

from intent_routing.api import admin


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("true", True),
        ("false", False),
    ],
)
def test_optional_multipart_boolean_parser_accepts_only_explicit_values(
    value: str | None,
    expected: bool | None,
) -> None:
    assert admin._parse_optional_multipart_boolean(value) is expected


@pytest.mark.parametrize("value", ["TRUE", "1", "yes", "", " false "])
def test_optional_multipart_boolean_parser_rejects_ambiguous_values(value: str) -> None:
    with pytest.raises(ValueError, match="include_common_risk_pack"):
        admin._parse_optional_multipart_boolean(value)
