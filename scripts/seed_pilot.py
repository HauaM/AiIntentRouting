from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

import httpx

from intent_routing.ops.admin_client import AdminApiClient
from intent_routing.ops.pilot_catalog import PilotCatalog, PilotIntent, load_pilot_catalog

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "docs/pilot/it-helpdesk-pilot-catalog.json"
DEFAULT_CSV = ROOT / "docs/pilot/it-helpdesk-pilot-cases.csv"
BALANCED_GATE_PRESET = "balanced"


class _AdminApi(Protocol):
    def post(self, path: str, *, json: Mapping[str, Any] | None = None) -> Any: ...

    def patch(self, path: str, *, json: Mapping[str, Any] | None = None) -> Any: ...


def seed_pilot(
    *,
    base_url: str,
    admin_token: str,
    catalog_path: Path,
    csv_path: Path,
    service_id: str | None = None,
    environment: str | None = None,
    http_client: Any | None = None,
) -> dict[str, Any]:
    catalog = load_pilot_catalog(catalog_path)
    resolved_service_id = service_id or catalog.service_id
    resolved_environment = environment or catalog.environment
    if http_client is not None:
        return _seed_pilot_with_api(
            api=_TestClientAdminApi(
                http_client=http_client,
                admin_token=admin_token,
                actor_id="pilot-seed",
                actor_roles="system_admin",
            ),
            catalog=catalog,
            csv_path=csv_path,
            service_id=resolved_service_id,
            environment=resolved_environment,
        )

    with AdminApiClient(
        base_url=base_url,
        admin_token=admin_token,
        actor_id="pilot-seed",
        actor_roles="system_admin",
    ) as api:
        return _seed_pilot_with_api(
            api=api,
            catalog=catalog,
            csv_path=csv_path,
            service_id=resolved_service_id,
            environment=resolved_environment,
        )


def _seed_pilot_with_api(
    *,
    api: _AdminApi,
    catalog: PilotCatalog,
    csv_path: Path,
    service_id: str,
    environment: str,
) -> dict[str, Any]:
    catalog_threshold_preset = _threshold_preset_value(catalog)

    api.post(
        "/admin/v1/services",
        json={
            "service_id": service_id,
            "display_name": catalog.display_name,
            "environment": environment,
            "default_threshold_preset": catalog_threshold_preset,
            "max_input_tokens": 256,
        },
    )
    api_key = api.post(
        "/admin/v1/api-keys",
        json={
            "service_id": service_id,
            "environment": environment,
            "app_id": catalog.app_id,
            "allowed_intents": [intent.intent_id for intent in catalog.intents],
            "allowed_route_keys": [intent.route_key for intent in catalog.intents],
            "expires_in_days": 365,
        },
    )
    for intent in catalog.intents:
        api.post(
            f"/admin/v1/services/{service_id}/intents",
            json=_intent_create_payload(intent),
        )
    for intent in catalog.intents:
        api.patch(
            f"/admin/v1/services/{service_id}/intents/{intent.intent_id}",
            json={"status": "active"},
        )
    for intent in catalog.intents:
        for text_raw in intent.positive_examples:
            example = api.post(
                f"/admin/v1/services/{service_id}/intents/{intent.intent_id}/examples",
                json=_example_payload("positive", text_raw),
            )
            api.patch(
                f"/admin/v1/services/{service_id}/examples/{example['example_id']}:approve"
            )
        for text_raw in intent.negative_examples:
            example = api.post(
                f"/admin/v1/services/{service_id}/intents/{intent.intent_id}/examples",
                json=_example_payload("negative", text_raw),
            )
            api.patch(
                f"/admin/v1/services/{service_id}/examples/{example['example_id']}:approve"
            )

    policy_version = api.post(
        f"/admin/v1/services/{service_id}/policy-versions",
        json={
            "threshold_preset": catalog_threshold_preset,
            "clarify_margin": 0.08,
            "min_candidate_score": 0.55,
            "fallback_score": 0.45,
            "risk_policy": {"enabled": True},
            "off_topic_policy": {
                "enabled": True,
                "keywords": catalog.off_topic_keywords,
                "message": catalog.off_topic_message,
                "fallback_policy": {
                    "type": "fixed_message",
                    "retryable": False,
                    "recommended_action": "handoff_to_default_channel",
                },
            },
        },
    )
    catalog_version = api.post(
        f"/admin/v1/services/{service_id}/catalog-versions",
        json={"description": "Pilot catalog version seed"},
    )
    test_run = api.post(
        f"/admin/v1/services/{service_id}/test-runs",
        json={
            "policy_version": policy_version["policy_version"],
            "intent_catalog_version": catalog_version["intent_catalog_version"],
            "source_filename": csv_path.name,
            "csv_text": csv_path.read_text(encoding="utf-8"),
        },
    )
    if test_run["gate_passed"] is not True:
        raise RuntimeError(
            "Pilot CSV gate failed for balanced threshold: "
            + json.dumps(test_run, ensure_ascii=False, sort_keys=True)
        )

    release = api.post(
        f"/admin/v1/services/{service_id}/releases",
        json={
            "environment": environment,
            "policy_version": policy_version["policy_version"],
            "intent_catalog_version": catalog_version["intent_catalog_version"],
            "test_run_id": test_run["test_run_id"],
        },
    )
    active_release = api.post(
        f"/admin/v1/services/{service_id}/releases/{release['release_version']}:activate"
    )

    return {
        "service_id": service_id,
        "environment": environment,
        "app_id": catalog.app_id,
        "key_id": api_key["key_id"],
        "api_key": api_key["api_key"],
        "policy_version": policy_version["policy_version"],
        "intent_catalog_version": catalog_version["intent_catalog_version"],
        "test_runs": {BALANCED_GATE_PRESET: test_run},
        "release_version": active_release["release_version"],
    }


def main() -> None:
    args = _parse_args()
    admin_token = args.admin_token or os.environ.get("ADMIN_BOOTSTRAP_TOKEN")
    if not admin_token:
        raise SystemExit("--admin-token or ADMIN_BOOTSTRAP_TOKEN is required")

    catalog_path = Path(args.catalog)
    catalog = load_pilot_catalog(catalog_path)
    service_id = args.service_id or catalog.service_id
    environment = args.environment or catalog.environment
    state_path = Path(args.state_path) if args.state_path else _default_state_path(service_id)
    state = seed_pilot(
        base_url=args.base_url,
        admin_token=admin_token,
        catalog_path=catalog_path,
        csv_path=Path(args.csv),
        service_id=service_id,
        environment=environment,
    )
    _write_state(state_path, state)
    print(f"service_id={state['service_id']}")
    print(f"key_id={state['key_id']}")
    print(f"release_version={state['release_version']}")
    print(f"policy_version={state['policy_version']}")
    print(f"intent_catalog_version={state['intent_catalog_version']}")
    print(f"state_path={state_path}")


class _TestClientAdminApi:
    def __init__(
        self,
        *,
        http_client: Any,
        admin_token: str,
        actor_id: str,
        actor_roles: str,
    ) -> None:
        self._http_client = http_client
        self._headers = {
            "X-Admin-Token": admin_token,
            "X-Actor-Id": actor_id,
            "X-Actor-Roles": actor_roles,
        }

    def post(self, path: str, *, json: Mapping[str, Any] | None = None) -> Any:
        return self._request("POST", path, json=json)

    def patch(self, path: str, *, json: Mapping[str, Any] | None = None) -> Any:
        return self._request("PATCH", path, json=json)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._http_client.request(
            method,
            path,
            headers=self._headers,
            **kwargs,
        )
        if response.status_code >= 400:
            raise RuntimeError(_format_response_error(response))
        if not response.content:
            return None
        return response.json()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the pilot admin API workflow.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--admin-token")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--service-id")
    parser.add_argument("--environment")
    parser.add_argument("--state-path", type=Path)
    return parser.parse_args()


def _intent_create_payload(intent: PilotIntent) -> dict[str, Any]:
    return {
        "intent_id": intent.intent_id,
        "domain": intent.domain,
        "display_name": intent.display_name,
        "description": intent.description,
        "route_key": intent.route_key,
        "include_keywords": intent.include_keywords,
        "exclude_keywords": intent.exclude_keywords,
    }


def _example_payload(example_type: str, text_raw: str) -> dict[str, Any]:
    return {
        "example_type": example_type,
        "text_raw": text_raw,
        "source": "pilot-seed",
        "test_case_id": None,
    }


def _threshold_preset_value(catalog: PilotCatalog) -> str:
    return catalog.threshold_preset.value


def _default_state_path(service_id: str) -> Path:
    return ROOT / "var/pilot" / f"{service_id}.state.secret.json"


def _write_state(path: Path, state: Mapping[str, Any]) -> None:
    payload = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = -1
    temp_path: Path | None = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            text=True,
        )
        temp_path = Path(temp_name)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        if fd >= 0:
            os.close(fd)
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise
    path.chmod(0o600)


def _format_response_error(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"{response.status_code} HTTP_ERROR {response.text}"
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        return (
            f"{response.status_code} "
            f"{error.get('code', 'UNKNOWN_ERROR')} "
            f"{error.get('message', '')}"
        ).strip()
    return f"{response.status_code} HTTP_ERROR {body}"


if __name__ == "__main__":
    main()
