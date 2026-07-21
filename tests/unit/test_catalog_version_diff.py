from types import SimpleNamespace
from typing import cast

from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.versions.catalogs import build_catalog_version_diff


class FakeCatalogVersionRepository:
    def __init__(self) -> None:
        self.versions: dict[str, SimpleNamespace] = {
            "cat-v1": SimpleNamespace(
                intent_catalog_version="cat-v1",
                snapshot={
                    "intents": [
                        {
                            "intent_id": "t1",
                            "display_name": "테스트 문의",
                            "route_key": "test.route",
                            "examples": [
                                {
                                    "example_id": "ex-1",
                                    "example_type": "positive",
                                    "text_masked": "기존 예시",
                                    "approved": True,
                                }
                            ],
                        }
                    ]
                },
            ),
            "cat-v2": SimpleNamespace(
                intent_catalog_version="cat-v2",
                snapshot={
                    "intents": [
                        {
                            "intent_id": "t1",
                            "display_name": "테스트 문의",
                            "route_key": "test.route",
                            "examples": [
                                {
                                    "example_id": "ex-1",
                                    "example_type": "positive",
                                    "text_masked": "기존 예시",
                                    "approved": True,
                                },
                                {
                                    "example_id": "ex-2",
                                    "example_type": "negative",
                                    "text_masked": "담당자 전화번호를 알려줘",
                                    "approved": True,
                                },
                            ],
                        }
                    ]
                },
            ),
        }

    def get_catalog_version(
        self,
        service_id: str,
        intent_catalog_version: str,
    ) -> SimpleNamespace | None:
        assert service_id == "svc-test"
        return self.versions.get(intent_catalog_version)


def test_catalog_version_diff_examples_include_intent_context_and_text() -> None:
    diff = build_catalog_version_diff(
        cast(IntentRoutingRepository, FakeCatalogVersionRepository()),
        service_id="svc-test",
        intent_catalog_version="cat-v2",
        compare_to="cat-v1",
    )

    assert diff.added_examples == [
        {
            "intent_id": "t1",
            "intent_display_name": "테스트 문의",
            "route_key": "test.route",
            "example_type": "negative",
            "text_masked": "담당자 전화번호를 알려줘",
        }
    ]
