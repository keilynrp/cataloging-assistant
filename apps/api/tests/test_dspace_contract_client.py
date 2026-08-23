import asyncio

import httpx

from cataloging_api.dspace.client import DSpaceClient, DSpaceError


def _hal_page(relation: str) -> dict:
    return {
        "_embedded": {
            relation: [
                {"id": 1, "name": "first"},
                {"id": 2, "name": "second"},
            ]
        },
        "page": {
            "number": 3,
            "size": 25,
            "totalPages": 9,
            "totalElements": 202,
        },
    }


def test_metadata_fields_page_preserves_raw_hal_and_pagination() -> None:
    expected = _hal_page("metadatafields")
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=expected)

    async def run() -> None:
        async with DSpaceClient(
            "https://dspace.example/server/api",
            transport=httpx.MockTransport(handler),
        ) as client:
            page = await client.get_metadata_fields_page(page=3, size=25)

        assert [item["id"] for item in page.items] == [1, 2]
        assert page.page == 3
        assert page.total_pages == 9
        assert page.total_elements == 202
        assert page.raw_payload == expected
        assert seen[0].url.path == "/server/api/core/metadatafields"
        assert seen[0].url.params["page"] == "3"
        assert seen[0].url.params["size"] == "25"

    asyncio.run(run())


def test_contract_collection_methods_use_explicit_read_only_endpoints() -> None:
    expected_by_path = {
        "/server/api/core/metadataschemas": "metadataschemas",
        "/server/api/core/metadatafields": "metadatafields",
        "/server/api/config/submissiondefinitions": "submissiondefinitions",
        "/server/api/config/submissionsections": "submissionsections",
    }
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        relation = expected_by_path[request.url.path]
        return httpx.Response(200, json=_hal_page(relation))

    async def run() -> None:
        async with DSpaceClient(
            "https://dspace.example/server/api",
            transport=httpx.MockTransport(handler),
        ) as client:
            schemas = await client.get_metadata_schemas_page(page=0)
            fields = await client.get_metadata_fields_page(page=0)
            definitions = await client.get_submission_definitions_page(page=0)
            sections = await client.get_submission_sections_page(page=0)

        assert schemas.items[0]["name"] == "first"
        assert fields.items[0]["name"] == "first"
        assert definitions.items[0]["name"] == "first"
        assert sections.items[0]["name"] == "first"

    asyncio.run(run())

    assert seen_paths == [
        "/server/api/core/metadataschemas",
        "/server/api/core/metadatafields",
        "/server/api/config/submissiondefinitions",
        "/server/api/config/submissionsections",
    ]


def test_repeating_same_page_request_is_observationally_idempotent() -> None:
    expected = _hal_page("metadatafields")
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=expected)

    async def run() -> None:
        async with DSpaceClient(
            "https://dspace.example/server/api",
            transport=httpx.MockTransport(handler),
        ) as client:
            first = await client.get_metadata_fields_page(page=1, size=100)
            second = await client.get_metadata_fields_page(page=1, size=100)

        assert first == second

    asyncio.run(run())
    assert calls == 2


def test_normalized_items_cannot_mutate_raw_hal_evidence() -> None:
    expected = _hal_page("metadatafields")

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=expected)

    async def run() -> None:
        async with DSpaceClient(
            "https://dspace.example/server/api",
            transport=httpx.MockTransport(handler),
        ) as client:
            page = await client.get_metadata_fields_page(page=0)

        page.items[0]["name"] = "mutated"
        assert page.raw_payload == expected
        assert page.raw_payload["_embedded"]["metadatafields"][0]["name"] == "first"

    asyncio.run(run())


def test_missing_hal_relation_is_rejected() -> None:
    malformed = {"_embedded": {}, "page": {"number": 0, "totalPages": 1, "totalElements": 0}}

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=malformed)

    async def run() -> None:
        async with DSpaceClient(
            "https://dspace.example/server/api",
            transport=httpx.MockTransport(handler),
        ) as client:
            try:
                await client.get_metadata_fields_page(page=0)
            except DSpaceError as exc:
                assert exc.code == "invalid_hal"
            else:
                raise AssertionError("missing HAL relation must be rejected")

    asyncio.run(run())


def test_malformed_hal_relation_is_rejected() -> None:
    malformed_payloads = [
        {"_embedded": {"metadatafields": {}}, "page": {}},
        {"_embedded": {"metadatafields": [{"id": 1}, "not-an-object"]}, "page": {}},
    ]

    async def run(payload: dict) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        async with DSpaceClient(
            "https://dspace.example/server/api",
            transport=httpx.MockTransport(handler),
        ) as client:
            try:
                await client.get_metadata_fields_page(page=0)
            except DSpaceError as exc:
                assert exc.code == "invalid_hal"
            else:
                raise AssertionError("malformed HAL relation must be rejected")

    for payload in malformed_payloads:
        asyncio.run(run(payload))
