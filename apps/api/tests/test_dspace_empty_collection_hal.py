import asyncio

import httpx
import pytest

from cataloging_api.dspace.client import DSpaceClient, DSpaceError


def test_empty_schema_page_without_embedded_is_valid() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/core/metadatafields/search/bySchema")
        assert request.url.params["schema"] == "local"
        return httpx.Response(
            200,
            json={
                "page": {
                    "size": 100,
                    "totalElements": 0,
                    "totalPages": 0,
                    "number": 0,
                },
                "_links": {},
            },
        )

    async def run() -> None:
        async with DSpaceClient(
            "http://dspace.test/server/api",
            transport=httpx.MockTransport(handler),
        ) as client:
            page = await client.get_metadata_fields_by_schema_page(
                "local", page=0, size=100
            )
        assert page.items == []
        assert page.page == 0
        assert page.total_elements == 0
        assert page.total_pages == 0
        assert page.raw_payload["page"]["totalElements"] == 0

    asyncio.run(run())


def test_missing_embedded_relation_with_reported_elements_fails_closed() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "page": {
                    "size": 100,
                    "totalElements": 1,
                    "totalPages": 1,
                    "number": 0,
                },
                "_links": {},
            },
        )

    async def run() -> None:
        async with DSpaceClient(
            "http://dspace.test/server/api",
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(DSpaceError) as exc_info:
                await client.get_metadata_fields_by_schema_page(
                    "dc", page=0, size=100
                )
        assert exc_info.value.code == "invalid_hal"

    asyncio.run(run())
