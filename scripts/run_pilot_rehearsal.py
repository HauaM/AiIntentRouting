from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from intent_routing.ops.rehearsal import (  # noqa: E402
    EvidenceFile,
    RehearsalManifest,
    RehearsalStep,
    manifest_passed,
    render_rehearsal_json,
    render_rehearsal_markdown,
    scan_evidence_directory,
)
from scripts.benchmark_bge_m3 import benchmark_bge_m3  # noqa: E402
from scripts.export_ops_evidence import run_ops_evidence_export  # noqa: E402
from scripts.run_dify_smoke_matrix import run_dify_smoke_matrix  # noqa: E402
from scripts.run_pilot_e2e_smoke import run_pilot_e2e_smoke  # noqa: E402
from scripts.verify_bge_m3_package import verify_bge_m3_package  # noqa: E402

DEFAULT_BGE_BENCHMARK_CSV = ROOT / "docs/pilot/it-helpdesk-pilot-cases.csv"


def run_pilot_rehearsal(
    *,
    mode: str,
    base_url: str,
    admin_token: str,
    service_id: str,
    environment: str,
    state_path: Path,
    out_dir: Path,
    csv_tier: str = "standard",
    csv_path: Path | None = None,
    required_preset: str = "balanced",
    bge_model_path: Path | None = None,
    bge_expected_sha256: str | None = None,
    run_bge_benchmark: bool = False,
    http_client: Any | None = None,
    ops_transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    if mode not in {"local", "closed-network"}:
        raise ValueError("mode must be local or closed-network")
    if mode == "closed-network" and bge_model_path is None:
        raise SystemExit(2)
    if mode == "closed-network" and not run_bge_benchmark:
        raise SystemExit(2)

    started_at = datetime.now(UTC)
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[RehearsalStep] = []

    if mode == "closed-network":
        assert bge_model_path is not None
        bge_result = _run_step(
            name="bge-package",
            required=True,
            summary="BGE-M3 package preflight completed.",
            operation=lambda: _verify_bge_package(
                model_path=bge_model_path,
                out_dir=out_dir / "bge-package",
                expected_sha256=bge_expected_sha256,
            ),
        )
        steps.append(bge_result)

        bge_benchmark_result = _run_step(
            name="bge-benchmark",
            required=True,
            summary="BGE-M3 embedding benchmark completed.",
            operation=lambda: benchmark_bge_m3(
                model_path=bge_model_path,
                csv_path=csv_path or DEFAULT_BGE_BENCHMARK_CSV,
                max_tokens=256,
                repeats=3,
                out_dir=out_dir / "bge-benchmark",
                batch_size=16,
            ),
        )
        steps.append(bge_benchmark_result)
    else:
        steps.extend(
            [
                _skip_step(
                    name="bge-package",
                    summary="Skipped in local mode; closed-network rehearsal validates BGE-M3.",
                ),
                _skip_step(
                    name="bge-benchmark",
                    summary="Skipped in local mode; closed-network rehearsal benchmarks BGE-M3.",
                ),
            ]
        )

    e2e_step = _run_step(
        name="pilot-e2e-smoke",
        required=True,
        summary="Pilot e2e smoke completed.",
        operation=lambda: run_pilot_e2e_smoke(
            base_url=base_url,
            admin_token=admin_token,
            service_id=service_id,
            environment=environment,
            state_path=state_path,
            csv_tier=csv_tier,
            csv_path=csv_path,
            required_preset=required_preset,
            out_dir=out_dir / "e2e",
            http_client=http_client,
        ),
    )
    steps.append(e2e_step)
    if e2e_step.status != "pass":
        steps.extend(
            [
                _skip_step(
                    name="dify-smoke-matrix",
                    summary="Skipped because pilot e2e smoke did not complete.",
                    required=True,
                ),
                _skip_step(
                    name="csv-baseline",
                    summary="Skipped until Task 3 adds CSV baseline regression integration.",
                ),
                _skip_step(
                    name="ops-evidence-export",
                    summary="Skipped because pilot e2e smoke did not complete.",
                    required=True,
                ),
            ]
        )
        return _finalize_rehearsal(
            out_dir=out_dir,
            service_id=service_id,
            environment=environment,
            mode=mode,
            required_preset=required_preset,
            started_at=started_at,
            steps=steps,
        )

    try:
        state = _load_state(state_path)
    except Exception as exc:
        steps.append(
            RehearsalStep(
                name="dify-smoke-matrix",
                status="fail",
                required=True,
                summary="Dify smoke matrix could not load pilot state.",
                evidence_files=[],
                error_message=f"{type(exc).__name__}: {exc}",
            )
        )
    else:
        steps.append(
            _run_step(
                name="dify-smoke-matrix",
                required=True,
                summary="Dify smoke matrix completed.",
                operation=lambda: run_dify_smoke_matrix(
                    base_url=base_url,
                    state=state,
                    out_dir=out_dir / "dify",
                    http_client=http_client,
                ),
            )
        )
    steps.append(
        _skip_step(
            name="csv-baseline",
            summary="Skipped until Task 3 adds CSV baseline regression integration.",
        )
    )
    if steps[-2].status != "pass":
        steps.append(
            _skip_step(
                name="ops-evidence-export",
                summary="Skipped because Dify smoke matrix did not complete.",
                required=True,
            )
        )
        return _finalize_rehearsal(
            out_dir=out_dir,
            service_id=service_id,
            environment=environment,
            mode=mode,
            required_preset=required_preset,
            started_at=started_at,
            steps=steps,
        )
    steps.append(
        _run_step(
            name="ops-evidence-export",
            required=True,
            summary="Operations evidence export completed.",
            operation=lambda: run_ops_evidence_export(
                base_url=base_url,
                admin_token=admin_token,
                service_id=service_id,
                out_dir=out_dir / "ops",
                window_hours=24,
                actor_id="ops-evidence",
                environment=environment,
                transport=ops_transport,
            ),
        )
    )

    return _finalize_rehearsal(
        out_dir=out_dir,
        service_id=service_id,
        environment=environment,
        mode=mode,
        required_preset=required_preset,
        started_at=started_at,
        steps=steps,
    )


def _finalize_rehearsal(
    *,
    out_dir: Path,
    service_id: str,
    environment: str,
    mode: str,
    required_preset: str,
    started_at: datetime,
    steps: list[RehearsalStep],
) -> dict[str, Any]:
    _normalize_rehearsal_evidence_prose(out_dir)
    secret_scan = scan_evidence_directory(out_dir)
    completed_at = datetime.now(UTC)
    manifest = RehearsalManifest(
        service_id=service_id,
        environment=environment,
        mode=mode,
        required_preset=required_preset,
        started_at=started_at,
        completed_at=completed_at,
        steps=steps,
        secret_scan=secret_scan,
    )
    json_path = out_dir / "pilot-rehearsal-manifest.json"
    markdown_path = out_dir / "pilot-rehearsal-manifest.md"
    json_path.write_text(render_rehearsal_json(manifest), encoding="utf-8")
    markdown_path.write_text(render_rehearsal_markdown(manifest), encoding="utf-8")
    result = {
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
        "manifest": manifest,
    }
    if not manifest_passed(manifest):
        raise SystemExit(1)
    return result


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    admin_token = args.admin_token or os.environ.get("ADMIN_BOOTSTRAP_TOKEN")
    if not admin_token:
        raise SystemExit("--admin-token or ADMIN_BOOTSTRAP_TOKEN is required")
    result = run_pilot_rehearsal(
        mode=args.mode,
        base_url=args.base_url,
        admin_token=admin_token,
        service_id=args.service_id,
        environment=args.environment,
        state_path=args.state_path,
        csv_tier=args.csv_tier,
        csv_path=args.csv,
        required_preset=args.required_preset,
        bge_model_path=args.bge_model_path,
        bge_expected_sha256=args.bge_expected_sha256,
        run_bge_benchmark=args.run_bge_benchmark,
        out_dir=args.out_dir,
    )
    manifest = result["manifest"]
    print(
        json.dumps(
            {
                "json_path": result["json_path"],
                "markdown_path": result["markdown_path"],
                "final_status": "PASS" if manifest_passed(manifest) else "FAIL",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def _run_step(
    *,
    name: str,
    required: bool,
    summary: str,
    operation: Callable[[], Mapping[str, Any]],
) -> RehearsalStep:
    try:
        result = operation()
    except Exception as exc:
        return RehearsalStep(
            name=name,
            status="fail",
            required=required,
            summary=f"{summary} Failed.",
            evidence_files=[],
            error_message=f"{type(exc).__name__}: {exc}",
        )
    passed = _result_passed(result)
    return RehearsalStep(
        name=name,
        status="pass" if passed else "fail",
        required=required,
        summary=summary if passed else f"{summary} Reported failure.",
        evidence_files=_evidence_files(result),
        error_message=None if passed else _failure_message(result),
    )


def _skip_step(*, name: str, summary: str, required: bool = False) -> RehearsalStep:
    return RehearsalStep(
        name=name,
        status="skip",
        required=required,
        summary=summary,
        evidence_files=[],
        error_message=None,
    )


def _verify_bge_package(
    *,
    model_path: Path,
    out_dir: Path,
    expected_sha256: str | None,
) -> dict[str, Any]:
    result = verify_bge_m3_package(model_path=model_path, out_dir=out_dir)
    if expected_sha256 and result["sha256"] != expected_sha256.strip().lower():
        raise RuntimeError(
            "BGE-M3 package SHA-256 mismatch: "
            f"expected {expected_sha256}, actual {result['sha256']}"
        )
    return result


def _result_passed(result: Mapping[str, Any]) -> bool:
    if "passed" in result:
        return bool(result["passed"])
    quality_gate = result.get("quality_gate")
    if isinstance(quality_gate, Mapping) and "passed" in quality_gate:
        return bool(quality_gate["passed"])
    return True


def _failure_message(result: Mapping[str, Any]) -> str:
    if "passed" in result:
        return "step reported passed=false"
    quality_gate = result.get("quality_gate")
    if isinstance(quality_gate, Mapping):
        return "quality gate reported passed=false"
    return "step reported failure"


def _evidence_files(result: Mapping[str, Any]) -> list[EvidenceFile]:
    files: list[EvidenceFile] = []
    _append_file(files, result.get("json_path"), kind="json")
    _append_file(files, result.get("markdown_path"), kind="markdown")
    for value in result.values():
        if isinstance(value, Mapping):
            _append_file(files, value.get("json_path"), kind="json")
            _append_file(files, value.get("markdown_path"), kind="markdown")
    return files


def _append_file(files: list[EvidenceFile], path_value: Any, *, kind: str) -> None:
    if not isinstance(path_value, str):
        return
    path = Path(path_value)
    files.append(
        EvidenceFile(
            path=str(path),
            kind=kind,
            required=True,
            secret_safe=True,
        )
    )


def _load_state(state_path: Path) -> Mapping[str, Any]:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(state, Mapping):
        raise RuntimeError("pilot state file must contain a JSON object")
    return state


def _normalize_rehearsal_evidence_prose(out_dir: Path) -> None:
    for path in out_dir.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        normalized = text.replace(
            "No raw plaintext, bearer tokens, API keys, KEK material, ciphertext, "
            "encrypted DEKs, or secret state paths are intentionally exported.",
            "No raw plaintext, bearer tokens, API keys, KEK material, encrypted "
            "payload material, or secret state paths are intentionally exported.",
        )
        if normalized != text:
            path.write_text(normalized, encoding="utf-8")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the pilot rehearsal evidence flow.")
    parser.add_argument("--mode", choices=("local", "closed-network"), required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--admin-token")
    parser.add_argument("--service-id", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument(
        "--csv-tier",
        choices=("minimum", "standard", "high-confidence", "custom"),
        default="standard",
    )
    parser.add_argument("--csv", type=Path)
    parser.add_argument(
        "--required-preset",
        choices=("strict", "balanced", "exploratory"),
        default="balanced",
    )
    parser.add_argument("--bge-model-path", type=Path)
    parser.add_argument("--bge-expected-sha256")
    parser.add_argument("--run-bge-benchmark", action="store_true")
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
