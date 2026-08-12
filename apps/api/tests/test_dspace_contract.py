import json
from pathlib import Path

import httpx
import pytest

from cataloging_api.dspace.client import DSpaceClient
from cataloging_api.dspace.normalizer import LINGUISTIC_FIELDS, normalize_item

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.asyncio
async def test_discover_parses_hal_and_uses_get_only() -> None:
    observed_methods: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        observed_methods.append(request.method)
        return httpx.Response(200, json=load_fixture("discover_page.json"))

    client = DSpaceClient("https://dspace.example/api", transport=httpx.MockTransport(handler))
    try:
        page = await client.discover_items("collection-id", page=0, size=20)
    finally:
        await client.aclose()

    assert observed_methods == ["GET"]
    assert page.total_elements == 1
    assert page.items[0]["uuid"] == "11111111-1111-4111-8111-111111111111"


def test_normalizer_preserves_repeated_metadata_contract() -> None:
    item = normalize_item(
        load_fixture("item.json"),
        collection_uuid="e9a8f44f-a8d3-4d22-b02a-cf590285bac6",
        bundles=[],
    )
    values = [value for value in item.metadata_values if value.field == "dc.subject.linguiscgroup"]

    assert "dc.subject.linguiscgroup" in LINGUISTIC_FIELDS
    assert [(value.value, value.place) for value in values] == [("Grupo A", 0), ("Grupo B", 1)]
    assert values[0].authority == "auth:1"
    assert values[0].confidence == 600
    assert item.raw_json["metadata"]["dc.subject.linguiscgroup"][1]["value"] == "Grupo B"
