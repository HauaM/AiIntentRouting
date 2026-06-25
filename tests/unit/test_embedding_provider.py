from __future__ import annotations

import builtins
import os
import sys
from collections.abc import Iterator
from types import ModuleType

import pytest

from intent_routing.embedding.provider import (
    clear_embedding_provider_cache,
    get_embedding_provider,
)


@pytest.fixture(autouse=True)
def _reset_embedding_provider_cache() -> Iterator[None]:
    clear_embedding_provider_cache()
    yield
    clear_embedding_provider_cache()


def _fail_on_flag_embedding_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def guarded_import(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> ModuleType:
        if name == "FlagEmbedding":
            raise AssertionError("FlagEmbedding must not load during provider selection")
        return real_import(name, globals, locals, fromlist, level)

    sys.modules.pop("FlagEmbedding", None)
    monkeypatch.setattr(builtins, "__import__", guarded_import)


def test_selecting_bge_provider_does_not_import_or_load_flag_embedding(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "bge-m3")
    model_path = tmp_path_factory.mktemp("bge-m3")
    monkeypatch.setenv("BGE_M3_MODEL_PATH", str(model_path))
    _fail_on_flag_embedding_import(monkeypatch)

    provider = get_embedding_provider()

    assert provider.model_version == "emb-bge-m3-local"
    assert provider.dimension == 1024
    assert "FlagEmbedding" not in sys.modules


def test_bge_provider_requires_existing_local_model_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "bge-m3")
    monkeypatch.setenv("BGE_M3_MODEL_PATH", "BAAI/bge-m3")
    _fail_on_flag_embedding_import(monkeypatch)

    with pytest.raises(ValueError, match="local BGE-M3 model path"):
        get_embedding_provider()

    assert "FlagEmbedding" not in sys.modules


def test_get_embedding_provider_reuses_bge_provider_instance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "bge-m3")
    monkeypatch.setenv("BGE_M3_MODEL_PATH", str(tmp_path_factory.mktemp("bge-m3")))

    first_provider = get_embedding_provider()
    second_provider = get_embedding_provider()

    assert first_provider is second_provider


def test_get_embedding_provider_cache_is_keyed_by_effective_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    fake_provider = get_embedding_provider()

    monkeypatch.setenv("EMBEDDING_PROVIDER", "bge-m3")
    monkeypatch.setenv("BGE_M3_MODEL_PATH", str(tmp_path_factory.mktemp("bge-m3")))
    bge_provider = get_embedding_provider()

    assert fake_provider.model_version == "emb-fake-v1"
    assert bge_provider.model_version == "emb-bge-m3-local"
    assert bge_provider is not fake_provider


def test_get_embedding_provider_cache_normalizes_bge_aliases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    model_path = tmp_path_factory.mktemp("bge-m3")
    monkeypatch.setenv("BGE_M3_MODEL_PATH", str(model_path))

    monkeypatch.setenv("EMBEDDING_PROVIDER", "bge")
    first_provider = get_embedding_provider()
    monkeypatch.setenv("EMBEDDING_PROVIDER", "bge_m3")
    second_provider = get_embedding_provider()
    monkeypatch.setenv("EMBEDDING_PROVIDER", "bge-m3")
    third_provider = get_embedding_provider()

    assert first_provider is second_provider
    assert second_provider is third_provider


def test_selecting_fake_provider_does_not_import_flag_embedding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    _fail_on_flag_embedding_import(monkeypatch)

    provider = get_embedding_provider()

    assert provider.model_version == "emb-fake-v1"
    assert provider.dimension == 1024
    assert "FlagEmbedding" not in sys.modules


def test_bge_provider_loads_model_only_when_embedding(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    from intent_routing.embedding.bge_m3 import BGEM3EmbeddingProvider

    constructed: list[tuple[str, bool]] = []
    construction_env: dict[str, str | None] = {}
    fake_module = ModuleType("FlagEmbedding")

    class FakeBGEM3FlagModel:
        def __init__(self, model_path: str, *, use_fp16: bool) -> None:
            construction_env["HF_HUB_OFFLINE"] = os.environ.get("HF_HUB_OFFLINE")
            construction_env["TRANSFORMERS_OFFLINE"] = os.environ.get(
                "TRANSFORMERS_OFFLINE"
            )
            construction_env["HF_HUB_DISABLE_TELEMETRY"] = os.environ.get(
                "HF_HUB_DISABLE_TELEMETRY"
            )
            constructed.append((model_path, use_fp16))

        def encode(
            self,
            texts: list[str],
            *,
            batch_size: int,
            max_length: int,
        ) -> dict[str, list[list[float]]]:
            del texts, batch_size, max_length
            return {"dense_vecs": [[1.0] + [0.0] * 1023]}

    fake_module.BGEM3FlagModel = FakeBGEM3FlagModel  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "FlagEmbedding", fake_module)
    monkeypatch.setenv("HF_HUB_OFFLINE", "0")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "0")
    monkeypatch.setenv("HF_HUB_DISABLE_TELEMETRY", "0")
    model_path = tmp_path_factory.mktemp("bge-m3")
    provider = BGEM3EmbeddingProvider(
        model_path=str(model_path),
        model_version="emb-bge-m3-test",
        batch_size=2,
    )

    assert constructed == []
    embedding = provider.embed_texts(["api timeout 문의"], max_tokens=256)

    assert constructed == [(str(model_path), False)]
    assert construction_env == {
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
    }
    assert embedding == [[1.0] + [0.0] * 1023]
