from __future__ import annotations

import httpx
import pytest

from cataloging_api.dspace.authenticated_client import ReadAuthenticatedDSpaceClient
from cataloging_api.dspace.client import DSpaceError


@pytest.mark.asyncio
async def test_read_authenticated_client_performs_csrf_login_and_confirms_status() -> None:
    calls: list[tuple[str, str]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.method == "GET" and request.url.path.endswith("/authn/status"):
            authenticated = request.headers.get("Authorization") == "Bearer test-token"
            return httpx.Response(
                200,
                json={"authenticated": authenticated},
                headers={"Set-Cookie": "DSPACE-XSRF-COOKIE=csrf-token; Path=/"},
            )
        if request.method == "POST" and request.url.path.endswith("/authn/login"):
            assert request.headers.get("X-XSRF-TOKEN") == "csrf-token"
            return httpx.Response(200, headers={"Authorization": "Bearer test-token"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with ReadAuthenticatedDSpaceClient(
        "http://dspace.test/server/api",
        transport=transport,
        max_retries=0,
    ) as client:
        status = await client.authenticate("reader@example.org", "secret")

    assert status["authenticated"] is True
    assert calls == [
        ("GET", "/server/api/authn/status"),
        ("POST", "/server/api/authn/login"),
        ("GET", "/server/api/authn/status"),
    ]


@pytest.mark.asyncio
async def test_read_authenticated_client_requires_credentials() -> None:
    async with ReadAuthenticatedDSpaceClient("http://dspace.test/server/api") as client:
        with pytest.raises(DSpaceError, match="read credentials are required"):
            await client.authenticate("", "")
