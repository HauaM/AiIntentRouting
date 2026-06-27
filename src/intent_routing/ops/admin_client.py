from __future__ import annotations

from collections.abc import Mapping
from types import TracebackType
from typing import Any

import httpx


class AdminApiClient:
    def __init__(
        self,
        *,
        base_url: str,
        admin_token: str,
        actor_id: str,
        actor_roles: str,
        service_scope: str | None = None,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers = {
            "X-Admin-Token": admin_token,
            "X-Actor-Id": actor_id,
            "X-Actor-Roles": actor_roles,
        }
        if service_scope is not None:
            headers["X-Service-Scope"] = service_scope
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    def post(self, path: str, *, json: Mapping[str, Any] | None = None) -> Any:
        return self._request("POST", path, json=json)

    def get(self, path: str, *, params: Mapping[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params)

    def patch(self, path: str, *, json: Mapping[str, Any] | None = None) -> Any:
        return self._request("PATCH", path, json=json)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> AdminApiClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._client.request(method, path, **kwargs)
        if response.status_code >= 400:
            raise RuntimeError(_format_error(response))
        if not response.content:
            return None
        return response.json()


def _format_error(response: httpx.Response) -> str:
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
