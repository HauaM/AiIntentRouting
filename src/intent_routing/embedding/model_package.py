"""BGE-M3 model package manifest helpers for closed-network preflight."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

HASH_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True, slots=True)
class ModelPackageManifest:
    model_path: str
    file_count: int
    total_bytes: int
    sha256: str
    offline_required: bool = True


def build_model_package_manifest(model_path: Path) -> ModelPackageManifest:
    resolved_model_path = model_path.expanduser().resolve()
    if not resolved_model_path.is_dir():
        raise ValueError(
            "model_path must point to an existing local BGE-M3 model directory."
        )

    files = _iter_package_files(resolved_model_path)
    if not files:
        raise ValueError("BGE-M3 model directory must include at least one file.")

    sha256 = hashlib.sha256()
    total_bytes = 0
    for relative_path, file_path in files:
        sha256.update(relative_path.encode("utf-8"))
        sha256.update(b"\0")
        total_bytes += _hash_file_bytes(sha256, file_path)
        sha256.update(b"\n")

    return ModelPackageManifest(
        model_path=str(resolved_model_path),
        file_count=len(files),
        total_bytes=total_bytes,
        sha256=sha256.hexdigest(),
    )


def render_model_package_json(manifest: ModelPackageManifest) -> str:
    return json.dumps(asdict(manifest), ensure_ascii=False, indent=2) + "\n"


def render_model_package_markdown(manifest: ModelPackageManifest) -> str:
    return "\n".join(
        [
            "# BGE-M3 Package Preflight",
            "",
            f"- Model path: `{manifest.model_path}`",
            f"- File count: `{manifest.file_count}`",
            f"- Total bytes: `{manifest.total_bytes}`",
            f"- SHA-256: `{manifest.sha256}`",
            f"- Offline required: `{manifest.offline_required}`",
            "",
            "This preflight report records package metadata only; it does not include "
            "model file contents.",
            "",
        ]
    )


def _iter_package_files(model_path: Path) -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for path in model_path.rglob("*"):
        file_path = _regular_file_within_model_path(path, model_path)
        if file_path is None:
            continue
        files.append((path.relative_to(model_path).as_posix(), file_path))
    return sorted(files, key=lambda item: item[0])


def _regular_file_within_model_path(path: Path, model_path: Path) -> Path | None:
    if path.is_symlink():
        try:
            resolved_path = path.resolve(strict=True)
        except OSError:
            return None
        if not resolved_path.is_relative_to(model_path):
            return None
        if resolved_path.is_file():
            return path
        return None
    if path.is_file():
        return path
    return None


def _hash_file_bytes(sha256: hashlib._Hash, file_path: Path) -> int:
    total_bytes = 0
    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(HASH_CHUNK_SIZE), b""):
            total_bytes += len(chunk)
            sha256.update(chunk)
    return total_bytes
