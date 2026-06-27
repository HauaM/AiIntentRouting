import httpx

from intent_routing.ops.admin_client import AdminApiClient


def test_admin_client_sends_trusted_header_context() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json={"service_id": "svc-a"})

    transport = httpx.MockTransport(handler)
    client = AdminApiClient(
        base_url="http://testserver",
        admin_token="local-admin-token",
        actor_id="pilot-seed",
        actor_roles="system_admin",
        transport=transport,
    )

    response = client.post("/admin/v1/services", json={"service_id": "svc-a"})

    assert response == {"service_id": "svc-a"}
    assert requests[0].headers["X-Admin-Token"] == "local-admin-token"
    assert requests[0].headers["X-Actor-Id"] == "pilot-seed"
    assert requests[0].headers["X-Actor-Roles"] == "system_admin"


def test_admin_client_raises_with_error_envelope_message() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            json={
                "status": "error",
                "trace_id": "irt-test",
                "error": {"code": "INVALID_REQUEST", "message": "Service already exists."},
            },
        )

    client = AdminApiClient(
        base_url="http://testserver",
        admin_token="local-admin-token",
        actor_id="pilot-seed",
        actor_roles="system_admin",
        transport=httpx.MockTransport(handler),
    )

    try:
        client.post("/admin/v1/services", json={"service_id": "svc-a"})
    except RuntimeError as exc:
        assert "409 INVALID_REQUEST Service already exists." in str(exc)
    else:
        raise AssertionError("RuntimeError was not raised")
