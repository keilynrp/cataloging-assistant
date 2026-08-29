from __future__ import annotations

from typing import Any

import httpx

from cataloging_api.dspace.client import DSpaceClient, DSpaceError


class ReadAuthenticatedDSpaceClient(DSpaceClient):
    """DSpace client that adds authentication but no repository-write surface."""

    async def authenticate(self, username: str, password: str) -> dict[str, Any]:
        if not username or not password:
            raise DSpaceError("credentials_required", "DSpace read credentials are required")

        try:
            status_response = await self._client.get("/authn/status")
        except httpx.TimeoutException as exc:
            raise DSpaceError("timeout", "DSpace timed out at /authn/status") from exc
        except httpx.HTTPError as exc:
            raise DSpaceError(
                "network_error",
                "DSpace request failed at /authn/status",
            ) from exc
        if status_response.status_code >= 400:
            raise DSpaceError(
                "auth_status_failed",
                f"DSpace auth status failed: HTTP {status_response.status_code}",
                status_code=status_response.status_code,
            )

        xsrf = self._client.cookies.get("DSPACE-XSRF-COOKIE")
        if not xsrf:
            raise DSpaceError("csrf_missing", "DSpace did not return DSPACE-XSRF-COOKIE")

        try:
            response = await self._client.post(
                "/authn/login",
                data={"user": username, "password": password},
                headers={
                    "X-XSRF-TOKEN": xsrf,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
        except httpx.TimeoutException as exc:
            raise DSpaceError("timeout", "DSpace timed out at /authn/login") from exc
        except httpx.HTTPError as exc:
            raise DSpaceError(
                "network_error",
                "DSpace request failed at /authn/login",
            ) from exc
        if response.status_code != 200:
            raise DSpaceError(
                "authentication_failed",
                f"DSpace login failed: HTTP {response.status_code}",
                status_code=response.status_code,
            )

        authorization = response.headers.get("Authorization")
        if not authorization:
            raise DSpaceError(
                "authorization_header_missing",
                "DSpace login returned 200 without Authorization header",
            )
        self._client.headers["Authorization"] = authorization

        status = await self._get("/authn/status")
        if status.get("authenticated") is not True:
            raise DSpaceError(
                "authentication_not_confirmed",
                "DSpace did not confirm authentication",
            )
        return status
