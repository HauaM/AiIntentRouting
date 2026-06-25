"""CPU-only BGE-M3 embedding provider."""

from __future__ import annotations

import inspect
import math
from os import environ
from pathlib import Path
from typing import Any

EMBEDDING_DIMENSION = 1024


class BGEM3EmbeddingProvider:
    dimension = EMBEDDING_DIMENSION

    def __init__(
        self,
        *,
        model_path: str,
        model_version: str,
        batch_size: int = 16,
    ) -> None:
        if not model_path.strip():
            raise ValueError("BGE_M3_MODEL_PATH must be configured for BGE-M3 embeddings.")
        local_model_path = Path(model_path)
        if not local_model_path.exists():
            raise ValueError(
                "BGE_M3_MODEL_PATH must point to an existing local BGE-M3 model path."
            )
        self._model_path = str(local_model_path)
        self.model_version = model_version
        self._batch_size = batch_size
        self._model: Any | None = None

    @classmethod
    def from_env(cls) -> BGEM3EmbeddingProvider:
        return cls.from_config(
            model_path=environ.get("BGE_M3_MODEL_PATH"),
            model_sha256=environ.get("BGE_M3_MODEL_SHA256"),
            batch_size_text=environ.get("BGE_M3_BATCH_SIZE", "16"),
        )

    @classmethod
    def from_config(
        cls,
        *,
        model_path: str | None,
        model_sha256: str | None,
        batch_size_text: str,
    ) -> BGEM3EmbeddingProvider:
        if model_path is None or not model_path.strip():
            raise ValueError("BGE_M3_MODEL_PATH must be configured for BGE-M3 embeddings.")
        model_version = (
            f"emb-bge-m3-{model_sha256.strip()}"
            if model_sha256 is not None and model_sha256.strip()
            else "emb-bge-m3-local"
        )
        try:
            batch_size = int(batch_size_text)
        except ValueError as exc:
            raise ValueError("BGE_M3_BATCH_SIZE must be an integer.") from exc
        if batch_size < 1:
            raise ValueError("BGE_M3_BATCH_SIZE must be at least 1.")
        return cls(
            model_path=model_path,
            model_version=model_version,
            batch_size=batch_size,
        )

    def embed_texts(self, texts: list[str], *, max_tokens: int) -> list[list[float]]:
        encoded = self._model_instance().encode(
            texts,
            batch_size=self._batch_size,
            max_length=max_tokens,
        )
        dense_vectors = encoded["dense_vecs"] if isinstance(encoded, dict) else encoded
        vectors = [_as_float_list(vector) for vector in dense_vectors]
        for vector in vectors:
            if len(vector) != self.dimension:
                raise ValueError("BGE-M3 dense embedding dimension must be 1024.")
        return [_normalize(vector) for vector in vectors]

    def _model_instance(self) -> Any:
        if self._model is None:
            _force_offline_hugging_face()
            from FlagEmbedding import BGEM3FlagModel  # type: ignore[import-not-found]

            kwargs: dict[str, object] = {"use_fp16": False}
            if _constructor_supports_local_files_only(BGEM3FlagModel):
                kwargs["local_files_only"] = True
            self._model = BGEM3FlagModel(self._model_path, **kwargs)
        return self._model


def _force_offline_hugging_face() -> None:
    environ["HF_HUB_OFFLINE"] = "1"
    environ["TRANSFORMERS_OFFLINE"] = "1"
    environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


def _constructor_supports_local_files_only(constructor: Any) -> bool:
    try:
        parameters = inspect.signature(constructor).parameters
    except (TypeError, ValueError):
        return False
    return "local_files_only" in parameters


def _as_float_list(vector: Any) -> list[float]:
    if hasattr(vector, "tolist"):
        vector = vector.tolist()
    return [float(value) for value in vector]


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        raise ValueError("Embedding provider returned a zero vector.")
    return [value / norm for value in vector]
