import base64
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from intent_routing.api.admin import get_admin_session
from intent_routing.api.runtime import get_runtime_session
from intent_routing.embedding.provider import clear_embedding_provider_cache
from intent_routing.main import create_app
from scripts.seed_pilot import seed_pilot

ROOT = Path(__file__).resolve().parents[2]


def test_seed_pilot_creates_active_release_and_runtime_secret(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", base64.b64encode(b"0" * 32).decode("ascii"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    clear_embedding_provider_cache()
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    app.dependency_overrides[get_runtime_session] = override_session

    with TestClient(app) as client:
        state = seed_pilot(
            base_url=str(client.base_url),
            admin_token="local-admin-token",
            catalog_path=ROOT / "docs/pilot/it-helpdesk-pilot-catalog.json",
            csv_path=ROOT / "docs/pilot/it-helpdesk-pilot-cases.csv",
            service_id="it-helpdesk-pilot-test",
            environment="dev",
            http_client=client,
        )

    assert state["service_id"] == "it-helpdesk-pilot-test"
    assert state["environment"] == "dev"
    assert state["api_key"].startswith("irt_")
    assert state["key_id"].startswith("key_live_")
    assert state["release_version"].startswith("rel-it-helpdesk-pilot-test-")
    assert state["test_runs"]["balanced"]["gate_passed"] is True
