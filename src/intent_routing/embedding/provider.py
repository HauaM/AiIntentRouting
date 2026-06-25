"""Embedding provider selection."""

from __future__ import annotations

from functools import lru_cache
from os import environ
from pathlib import Path
from typing import Protocol


class EmbeddingProvider(Protocol):
    model_version: str
    dimension: int

    def embed_texts(self, texts: list[str], *, max_tokens: int) -> list[list[float]]:
        """Return one normalized embedding per input text."""


def get_embedding_provider() -> EmbeddingProvider:
    provider_name = _canonical_provider_name(
        environ.get("EMBEDDING_PROVIDER", "bge-m3")
    )
    if provider_name == "fake":
        return _get_embedding_provider(provider_name, None, None, None)
    if provider_name == "bge-m3":
        return _get_embedding_provider(
            provider_name,
            _normalized_model_path(environ.get("BGE_M3_MODEL_PATH")),
            _normalized_optional_text(environ.get("BGE_M3_MODEL_SHA256")),
            _normalized_batch_size_text(environ.get("BGE_M3_BATCH_SIZE", "16")),
        )
    raise ValueError("EMBEDDING_PROVIDER must be one of: fake, bge-m3.")


@lru_cache(maxsize=8)
def _get_embedding_provider(
    provider_name: str,
    model_path: str | None,
    model_sha256: str | None,
    batch_size_text: str | None,
) -> EmbeddingProvider:
    if provider_name == "fake":
        from intent_routing.embedding.fake import FakeEmbeddingProvider

        return FakeEmbeddingProvider()
    if provider_name == "bge-m3":
        from intent_routing.embedding.bge_m3 import BGEM3EmbeddingProvider

        return BGEM3EmbeddingProvider.from_config(
            model_path=model_path,
            model_sha256=model_sha256,
            batch_size_text=batch_size_text or "16",
        )
    raise ValueError("EMBEDDING_PROVIDER must be one of: fake, bge-m3.")


def _canonical_provider_name(provider_name: str) -> str:
    normalized_name = provider_name.strip().lower()
    if normalized_name in {"bge-m3", "bge_m3", "bge"}:
        return "bge-m3"
    return normalized_name


def _normalized_model_path(model_path: str | None) -> str | None:
    if model_path is None:
        return None
    stripped_path = model_path.strip()
    if not stripped_path:
        return stripped_path
    return str(Path(stripped_path).expanduser().resolve())


def _normalized_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value if stripped_value else None


def _normalized_batch_size_text(batch_size_text: str | None) -> str:
    stripped_text = (batch_size_text or "16").strip()
    if not stripped_text:
        return "16"
    try:
        return str(int(stripped_text))
    except ValueError:
        return stripped_text


def clear_embedding_provider_cache() -> None:
    _get_embedding_provider.cache_clear()
