from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from intent_routing.embedding.model_package import (
    build_model_package_manifest,
    render_model_package_json,
    render_model_package_markdown,
)

DEFAULT_JSON_REPORT = "bge-m3-package.json"
DEFAULT_MARKDOWN_REPORT = "bge-m3-package.md"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    result = verify_bge_m3_package(
        model_path=Path(args.model_path),
        out_dir=Path(args.out_dir),
    )
    print(result["json_path"])
    print(result["markdown_path"])

    try:
        expected_sha256 = _normalize_expected_sha256(args.expected_sha256)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    if expected_sha256 and expected_sha256 != result["sha256"]:
        print(
            "BGE-M3 package SHA-256 mismatch: "
            f"expected {expected_sha256}, actual {result['sha256']}",
            file=sys.stderr,
        )
        raise SystemExit(1)


def verify_bge_m3_package(*, model_path: Path, out_dir: Path) -> dict[str, str]:
    manifest = build_model_package_manifest(model_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / DEFAULT_JSON_REPORT
    markdown_path = out_dir / DEFAULT_MARKDOWN_REPORT
    json_path.write_text(render_model_package_json(manifest), encoding="utf-8")
    markdown_path.write_text(render_model_package_markdown(manifest), encoding="utf-8")
    return {
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
        "sha256": manifest.sha256,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify local BGE-M3 package checksum evidence."
    )
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--expected-sha256")
    return parser.parse_args(argv)


def _normalize_expected_sha256(expected_sha256: str | None) -> str | None:
    if expected_sha256 is None:
        return None
    normalized = expected_sha256.strip().lower()
    if not SHA256_PATTERN.fullmatch(normalized):
        raise ValueError("expected SHA-256 must be 64 lowercase hex characters.")
    return normalized


if __name__ == "__main__":
    main()
