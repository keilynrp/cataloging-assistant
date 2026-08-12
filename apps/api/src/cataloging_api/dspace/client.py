import asyncio
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
                    "not_found", f"DSpace resource not found: {path}", status_code=404
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
        payload = await self._get(f"/core/bundles/{bundle_uuid}/bitstreams", params={"size": 100})
        return _embedded_list(payload, "bitstreams")

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
