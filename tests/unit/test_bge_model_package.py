from __future__ import annotations

import builtins
import hashlib
import importlib
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

FORBIDDEN_MODEL_IMPORTS = {"FlagEmbedding", "torch", "sentence_transformers"}


def test_model_package_manifest_is_deterministic(tmp_path: Path) -> None:
    model_package = _import_model_package_module()
    model_dir = tmp_path / "bge-m3"
    model_dir.mkdir()
    (model_dir / "config.json").write_text('{"hidden_size":1024}\n', encoding="utf-8")
    (model_dir / "tokenizer.json").write_text("tokenizer\n", encoding="utf-8")

    first = model_package.build_model_package_manifest(model_dir)
    second = model_package.build_model_package_manifest(model_dir)

    assert first == second
    assert first.model_path == str(model_dir.resolve())
    assert first.file_count == 2
    assert first.total_bytes > 0
    assert first.sha256 == _expected_package_sha(
        model_dir,
        ["config.json", "tokenizer.json"],
    )
    assert first.offline_required is True


def test_model_package_json_is_deterministic(tmp_path: Path) -> None:
    model_package = _import_model_package_module()
    model_dir = tmp_path / "bge-m3"
    model_dir.mkdir()
    (model_dir / "tokenizer.json").write_text("tokenizer\n", encoding="utf-8")
    manifest = model_package.build_model_package_manifest(model_dir)

    rendered = model_package.render_model_package_json(manifest)

    assert rendered == model_package.render_model_package_json(manifest)
    assert rendered.endswith("\n")
    assert json.loads(rendered) == {
        "model_path": str(model_dir.resolve()),
        "file_count": 1,
        "total_bytes": len("tokenizer\n"),
        "sha256": manifest.sha256,
        "offline_required": True,
    }


def test_model_package_markdown_excludes_model_file_contents(tmp_path: Path) -> None:
    model_package = _import_model_package_module()
    model_dir = tmp_path / "bge-m3"
    model_dir.mkdir()
    secret_content = "do-not-print-model-content\n"
    (model_dir / "config.json").write_text(secret_content, encoding="utf-8")

    markdown = model_package.render_model_package_markdown(
        model_package.build_model_package_manifest(model_dir)
    )

    assert "BGE-M3 Package Preflight" in markdown
    assert str(model_dir.resolve()) in markdown
    assert secret_content.strip() not in markdown


def test_model_package_manifest_rejects_missing_non_directory_or_empty_path(
    tmp_path: Path,
) -> None:
    model_package = _import_model_package_module()

    with pytest.raises(ValueError, match="existing local BGE-M3 model directory"):
        model_package.build_model_package_manifest(tmp_path / "missing")

    not_directory = tmp_path / "config.json"
    not_directory.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="existing local BGE-M3 model directory"):
        model_package.build_model_package_manifest(not_directory)

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError, match="at least one file"):
        model_package.build_model_package_manifest(empty)


def test_symlink_pointing_outside_model_directory_is_skipped(tmp_path: Path) -> None:
    model_package = _import_model_package_module()
    model_dir = tmp_path / "bge-m3"
    model_dir.mkdir()
    (model_dir / "config.json").write_text("inside\n", encoding="utf-8")
    outside_file = tmp_path / "outside-tokenizer.json"
    outside_file.write_text("outside-content-must-not-be-hashed\n", encoding="utf-8")
    (model_dir / "tokenizer.json").symlink_to(outside_file)

    manifest = model_package.build_model_package_manifest(model_dir)

    assert manifest.file_count == 1
    assert manifest.total_bytes == len("inside\n")
    assert manifest.sha256 == _expected_package_sha(model_dir, ["config.json"])


def test_model_package_import_and_cli_parsing_do_not_import_runtime_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _fail_on_forbidden_model_imports(monkeypatch)
    for module_name in (
        "intent_routing.embedding.model_package",
        "scripts.verify_bge_m3_package",
    ):
        sys.modules.pop(module_name, None)

    model_package = importlib.import_module("intent_routing.embedding.model_package")
    verify_script = importlib.import_module("scripts.verify_bge_m3_package")
    importlib.reload(model_package)
    importlib.reload(verify_script)

    args = verify_script._parse_args(
        [
            "--model-path",
            str(tmp_path / "bge-m3"),
            "--out-dir",
            str(tmp_path / "reports"),
            "--expected-sha256",
            "0" * 64,
        ]
    )

    assert args.expected_sha256 == "0" * 64
    for forbidden in FORBIDDEN_MODEL_IMPORTS:
        assert forbidden not in sys.modules


def test_cli_writes_reports_then_exits_non_zero_on_checksum_mismatch(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    verify_script = _import_verify_script_module()
    model_dir = tmp_path / "bge-m3"
    model_dir.mkdir()
    secret_content = "model-content-must-not-appear\n"
    (model_dir / "config.json").write_text(secret_content, encoding="utf-8")
    out_dir = tmp_path / "benchmarks"

    with pytest.raises(SystemExit) as exc_info:
        verify_script.main(
            [
                "--model-path",
                str(model_dir),
                "--out-dir",
                str(out_dir),
                "--expected-sha256",
                "0" * 64,
            ]
        )

    json_path = out_dir / "bge-m3-package.json"
    markdown_path = out_dir / "bge-m3-package.md"
    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert json_path.exists()
    assert markdown_path.exists()
    assert str(json_path) in captured.out
    assert str(markdown_path) in captured.out
    assert secret_content.strip() not in captured.out
    assert secret_content.strip() not in captured.err
    assert secret_content.strip() not in json_path.read_text(encoding="utf-8")
    assert secret_content.strip() not in markdown_path.read_text(encoding="utf-8")


def _expected_package_sha(model_dir: Path, relative_paths: list[str]) -> str:
    sha256 = hashlib.sha256()
    for relative_path in sorted(relative_paths):
        sha256.update(relative_path.encode("utf-8"))
        sha256.update(b"\0")
        sha256.update((model_dir / relative_path).read_bytes())
        sha256.update(b"\n")
    return sha256.hexdigest()


def _fail_on_forbidden_model_imports(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def guarded_import(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> ModuleType:
        if name.split(".", maxsplit=1)[0] in FORBIDDEN_MODEL_IMPORTS:
            raise AssertionError(f"{name} must not import during package preflight")
        return real_import(name, globals, locals, fromlist, level)

    for forbidden in FORBIDDEN_MODEL_IMPORTS:
        sys.modules.pop(forbidden, None)
    monkeypatch.setattr(builtins, "__import__", guarded_import)


def _import_model_package_module() -> ModuleType:
    import intent_routing.embedding.model_package as model_package

    return model_package


def _import_verify_script_module() -> ModuleType:
    import scripts.verify_bge_m3_package as verify_script

    return verify_script
