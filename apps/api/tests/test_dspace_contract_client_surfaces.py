import asyncio

import httpx

from cataloging_api.dspace.client import DSpaceClient


def _page(relation: str) -> dict:
    return {
        "_embedded": {relation: [{"id": "x", "name": "x"}]},
        "page": {"number": 0, "totalPages": 1, "totalElements": 1},
    }


def test_metadata_fields_by_schema_preserves_schema_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_page("metadatafields"))

    async def run() -> None:
        async with DSpaceClient(
            "https://dspace.example/server/api",
            transport=httpx.MockTransport(handler),
        ) as client:
            await client.get_metadata_fields_by_schema_page("dc", page=0, size=50)

    asyncio.run(run())
    request = seen[0]
    assert request.url.path == "/server/api/core/metadatafields/search/bySchema"
    assert request.url.params["schema"] == "dc"
    assert request.url.params["page"] == "0"
    assert request.url.params["size"] == "50"


def test_submission_forms_and_active_definition_endpoints_are_read_only() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/submissionforms"):
            return httpx.Response(200, json=_page("submissionforms"))
        if request.url.path.endswith("/search/findByCollection"):
            return httpx.Response(200, json={"name": "traditional", "type": "submissiondefinition"})
        return httpx.Response(200, json=_page("submissionsections"))

    async def run() -> None:
        async with DSpaceClient(
            "https://dspace.example/server/api",
            transport=httpx.MockTransport(handler),
        ) as client:
            await client.get_submission_forms_page(page=0)
            await client.get_submission_definition_for_collection("collection-uuid")
            await client.get_submission_definition_sections_page("traditional", page=0)

    asyncio.run(run())
    assert [request.method for request in seen] == ["GET", "GET", "GET"]
    assert seen[0].url.path == "/server/api/config/submissionforms"
    assert seen[1].url.path.endswith("/config/submissiondefinitions/search/findByCollection")
    assert seen[1].url.params["uuid"] == "collection-uuid"
    assert seen[2].url.path.endswith("/config/submissiondefinitions/traditional/sections")
