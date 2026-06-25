"""Deterministic fake embeddings for tests."""

from __future__ import annotations

import math

EMBEDDING_DIMENSION = 1024


class FakeEmbeddingProvider:
    model_version = "emb-fake-v1"
    dimension = EMBEDDING_DIMENSION

    def embed_texts(self, texts: list[str], *, max_tokens: int) -> list[list[float]]:
        del max_tokens
        return [_normalized_vector(text) for text in texts]


def _normalized_vector(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSION
    lower_text = text.casefold()
    if (
        "timeout" in lower_text
        or "타임아웃" in lower_text
        or "500" in lower_text
        # Test-only Korean server-error bucket for Sprint 0 confusing cases.
        or "에러" in lower_text
    ):
        vector[0] = 1.0
        vector[1] = 0.2
        vector[2] = 0.02
    elif "비밀번호" in lower_text or "password" in lower_text:
        vector[0] = 0.2
        vector[1] = 1.0
        vector[2] = 0.02
    elif "날씨" in lower_text or "weather" in lower_text:
        vector[0] = 0.02
        vector[1] = 0.02
        vector[2] = 1.0
    else:
        vector[3] = 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector]
