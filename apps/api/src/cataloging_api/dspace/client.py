import asyncio
import copy
import random
from dataclasses import dataclass
from typing import Any

import httpx


class DSpaceError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class DiscoverPage:
    items: list[dict[str, Any]]
    page: int
    total_pages: int
    total_elements: int


@dataclass(frozen=True)
class HalCollectionPage:
    """One immutable observation page from a DSpace HAL collection."""

    items: list[dict[str, Any]]
    page: int
    total_pages: int
    total_elements: int
    raw_payload: dict[str, Any]


class DSpaceClient:
    """Narrow, read-only client. It intentionally exposes no generic HTTP method."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 20,
        max_retries: int = 4,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._max_retries = max_retries
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds),
            headers={"Accept": "application/hal+json, application/json"},
            transport=transport,
        )

    async def __aenter__(self) -> "DSpaceClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.get(path, params=params)
            except httpx.TimeoutException as exc:
                if attempt >= self._max_retries:
                    raise DSpaceError("timeout", f"DSpace timed out at {path}") from exc
                await self._backoff(attempt)
                continue
            except httpx.HTTPError as exc:
                raise DSpaceError("network_error", f"DSpace request failed at {path}") from exc

            if response.status_code == 404:
                raise DSpaceError(
                    "not_found",
                    f"DSpace resource not found: {path}",
                    status_code=404,
                )
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < self._max_retries:
                    await self._backoff(attempt)
                    continue
            try:
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPStatusError, ValueError) as exc:
                raise DSpaceError(
                    "invalid_response",
                    f"Unexpected DSpace response at {path}: HTTP {response.status_code}",
                    status_code=response.status_code,
                ) from exc
            if not isinstance(payload, dict):
                raise DSpaceError("invalid_hal", f"Expected a HAL object at {path}")
            return payload
        raise AssertionError("retry loop exhausted")

    @staticmethod
    async def _backoff(attempt: int) -> None:
        delay = min(8.0, 0.5 * (2**attempt)) + random.uniform(0, 0.25)
        await asyncio.sleep(delay)

    async def _get_collection_page(
        self,
        path: str,
        relation: str,
        *,
        page: int,
        size: int,
        extra_params: dict[str, Any] | None = None,
    ) -> HalCollectionPage:
        params = {"page": page, "size": size, **(extra_params or {})}
        payload = await self._get(path, params=params)
        page_info = payload.get("page")
        if not isinstance(page_info, dict):
            raise DSpaceError("invalid_hal", f"Expected page metadata at {path}")

        returned_page = int(page_info.get("number", page))
        total_pages = int(page_info.get("totalPages", 0))
        total_elements = int(page_info.get("totalElements", 0))
        embedded = payload.get("_embedded")

        # Spring HATEOAS may omit `_embedded` entirely for a proven-empty
        # collection page. Accept that shape only when pagination metadata
        # explicitly reports zero elements. Otherwise fail closed so a
        # malformed/partial response cannot masquerade as removals.
        if total_elements == 0 and (
            embedded is None or (isinstance(embedded, dict) and relation not in embedded)
        ):
            values: list[dict[str, Any]] = []
        else:
            if not isinstance(embedded, dict) or relation not in embedded:
                raise DSpaceError("invalid_hal", f"Expected HAL relation {relation} at {path}")
            values = embedded[relation]
            if not isinstance(values, list) or any(
                not isinstance(value, dict) for value in values
            ):
                raise DSpaceError(
                    "invalid_hal",
                    f"Expected object list for HAL relation {relation} at {path}",
                )

        return HalCollectionPage(
            items=copy.deepcopy(values),
            page=returned_page,
            total_pages=total_pages,
            total_elements=total_elements,
            raw_payload=copy.deepcopy(payload),
        )

    async def get_root(self) -> dict[str, Any]:
        return await self._get("")

    async def get_collection(self, collection_uuid: str) -> dict[str, Any]:
        return await self._get(f"/core/collections/{collection_uuid}")

    async def get_item(self, item_uuid: str) -> dict[str, Any]:
        return await self._get(f"/core/items/{item_uuid}")

    async def get_item_bundles(self, item_uuid: str) -> list[dict[str, Any]]:
        payload = await self._get(f"/core/items/{item_uuid}/bundles", params={"size": 100})
        return _embedded_list(payload, "bundles")

    async def get_bundle_bitstreams(self, bundle_uuid: str) -> list[dict[str, Any]]:
        payload = await self._get(
            f"/core/bundles/{bundle_uuid}/bitstreams",
            params={"size": 100},
        )
        return _embedded_list(payload, "bitstreams")

    async def get_metadata_schemas_page(
        self, *, page: int, size: int = 100
    ) -> HalCollectionPage:
        return await self._get_collection_page(
            "/core/metadataschemas",
            "metadataschemas",
            page=page,
            size=size,
        )

    async def get_metadata_fields_page(
        self, *, page: int, size: int = 100
    ) -> HalCollectionPage:
        return await self._get_collection_page(
            "/core/metadatafields",
            "metadatafields",
            page=page,
            size=size,
        )

    async def get_metadata_fields_by_schema_page(
        self,
        schema_prefix: str,
        *,
        page: int,
        size: int = 100,
    ) -> HalCollectionPage:
        return await self._get_collection_page(
            "/core/metadatafields/search/bySchema",
            "metadatafields",
            page=page,
            size=size,
            extra_params={"schema": schema_prefix},
        )

    async def get_submission_definitions_page(
        self, *, page: int, size: int = 100
    ) -> HalCollectionPage:
        return await self._get_collection_page(
            "/config/submissiondefinitions",
            "submissiondefinitions",
            page=page,
            size=size,
        )

    async def get_submission_sections_page(
        self, *, page: int, size: int = 100
    ) -> HalCollectionPage:
        return await self._get_collection_page(
            "/config/submissionsections",
            "submissionsections",
            page=page,
            size=size,
        )

    async def get_submission_forms_page(
        self, *, page: int, size: int = 100
    ) -> HalCollectionPage:
        return await self._get_collection_page(
            "/config/submissionforms",
            "submissionforms",
            page=page,
            size=size,
        )

    async def get_submission_definition_for_collection(
        self, collection_uuid: str
    ) -> dict[str, Any]:
        return await self._get(
            "/config/submissiondefinitions/search/findByCollection",
            params={"uuid": collection_uuid},
        )

    async def get_submission_definition_sections_page(
        self,
        definition_name: str,
        *,
        page: int,
        size: int = 100,
    ) -> HalCollectionPage:
        return await self._get_collection_page(
            f"/config/submissiondefinitions/{definition_name}/sections",
            "submissionsections",
            page=page,
            size=size,
        )

    async def discover_items(self, collection_uuid: str, *, page: int, size: int) -> DiscoverPage:
        payload = await self._get(
            "/discover/search/objects",
            params={
                "dsoType": "ITEM",
                "scope": collection_uuid,
                "page": page,
                "size": size,
            },
        )
        search_result = payload.get("_embedded", {}).get("searchResult", {})
        objects = search_result.get("_embedded", {}).get("objects", [])
        items: list[dict[str, Any]] = []
        for entry in objects:
            candidate = entry.get("_embedded", {}).get("indexableObject")
            if isinstance(candidate, dict) and candidate.get("type") == "item":
                items.append(candidate)
        page_info = search_result.get("page", payload.get("page", {}))
        return DiscoverPage(
            items=items,
            page=int(page_info.get("number", page)),
            total_pages=int(page_info.get("totalPages", 0)),
            total_elements=int(page_info.get("totalElements", len(items))),
        )


def _embedded_list(payload: dict[str, Any], relation: str) -> list[dict[str, Any]]:
    values = payload.get("_embedded", {}).get(relation, [])
    return [value for value in values if isinstance(value, dict)]
