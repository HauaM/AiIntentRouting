import pytest

from intent_routing.domain.schemas import validate_route_key


@pytest.mark.parametrize(
    "route_key",
    [
        "it.api_timeout.manual_lookup",
        "it.password_reset.self_service",
        "insurance.claim.guide",
        "loan.limit.check.mobile",
    ],
)
def test_validate_route_key_accepts_supported_format(route_key: str) -> None:
    assert validate_route_key(route_key) == route_key


@pytest.mark.parametrize(
    "route_key",
    [
        "IT.api_timeout.manual_lookup",
        "it.api timeout.manual_lookup",
        "it.api",
        "it.api.timeout.manual.lookup.extra",
        "보험.claim.guide",
        "it.api_timeout.prod",
    ],
)
def test_validate_route_key_rejects_invalid_format_or_environment_segments(
    route_key: str,
) -> None:
    with pytest.raises(ValueError):
        validate_route_key(route_key)
