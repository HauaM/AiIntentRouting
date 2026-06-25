from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, cast

from intent_routing.domain.schemas import FallbackPolicy
from intent_routing.policy.service_policy import ServiceOffTopicPolicy
from intent_routing.routing.engine import IntentCandidate


def off_topic_policy_from_config(config: Mapping[str, Any]) -> ServiceOffTopicPolicy | None:
    enabled = bool(config.get("enabled"))
    keywords = [
        value
        for value in config.get("keywords", [])
        if isinstance(value, str)
    ]
    fallback_payload = config.get("fallback_policy")
    fallback_policy = None
    if isinstance(fallback_payload, Mapping):
        fallback_policy = FallbackPolicy.model_validate(dict(fallback_payload))
    return ServiceOffTopicPolicy(
        enabled=enabled,
        keywords=keywords,
        message=str(config.get("message", "Request is outside the service policy.")),
        fallback_policy=fallback_policy,
    )


def candidates_from_snapshot(snapshot: object) -> list[IntentCandidate]:
    if not isinstance(snapshot, Iterable) or isinstance(snapshot, (str, bytes, bytearray)):
        return []
    candidates: list[IntentCandidate] = []
    for item in snapshot:
        if not isinstance(item, Mapping):
            continue
        intent_id = item.get("intent_id")
        display_name = item.get("display_name")
        domain = item.get("domain")
        route_key = item.get("route_key")
        if not all(
            isinstance(value, str)
            for value in (intent_id, display_name, domain, route_key)
        ):
            continue
        resolved_intent_id = cast("str", intent_id)
        resolved_display_name = cast("str", display_name)
        resolved_domain = cast("str", domain)
        resolved_route_key = cast("str", route_key)
        candidates.append(
            IntentCandidate(
                intent_id=resolved_intent_id,
                display_name=resolved_display_name,
                domain=resolved_domain,
                route_key=resolved_route_key,
                include_keywords=tuple(_string_list(item.get("include_keywords"))),
                exclude_keywords=tuple(_string_list(item.get("exclude_keywords"))),
            )
        )
    return candidates


def _string_list(raw_values: object) -> list[str]:
    if not isinstance(raw_values, Iterable) or isinstance(raw_values, (str, bytes, bytearray)):
        return []
    return [value for value in raw_values if isinstance(value, str)]
