from __future__ import annotations

from dataclasses import dataclass

from intent_routing.domain.schemas import FallbackPolicy


@dataclass(frozen=True, slots=True)
class OffTopicEvaluation:
    matched: bool
    message: str | None = None
    fallback_policy: FallbackPolicy | None = None


@dataclass(frozen=True, slots=True)
class ServiceOffTopicPolicy:
    enabled: bool
    keywords: list[str]
    message: str
    fallback_policy: FallbackPolicy | None = None

    def evaluate(self, query: str) -> OffTopicEvaluation:
        if not self.enabled:
            return OffTopicEvaluation(matched=False)

        normalized_query = query.casefold()
        for keyword in self.keywords:
            normalized_keyword = keyword.strip()
            if not normalized_keyword:
                continue
            if normalized_keyword.casefold() in normalized_query:
                return OffTopicEvaluation(
                    matched=True,
                    message=self.message,
                    fallback_policy=self.fallback_policy,
                )
        return OffTopicEvaluation(matched=False)
