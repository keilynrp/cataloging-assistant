"""Dedicated, SSRF-safe HTTP client for explicit remote evidence fetch.

Separate from cataloging_api.dspace.client on purpose (ADR-016 Fase 4):
DSpace is a known internal backend, this client fetches whatever URL a
catalogador types, so it needs its own trust boundary, timeouts and header
policy. No cookies, no credentials, no Authorization header, no user-
supplied headers or proxies (`trust_env=False`), no automatic redirect
following (handled manually so every hop is revalidated).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import urljoin

import httpx

from cataloging_api.config import Settings
from cataloging_api.evidence.net_policy import (
    DnsResolutionError,
    DnsResolver,
    TargetNotPublicError,
    UrlShapeError,
    resolve_public_ips,
    validate_url_shape,
)

ALLOWED_MIME_TYPES = {
    "text/plain",
    "text/html",
    "application/xhtml+xml",
    "application/pdf",
    "application/xml",
    "text/xml",
}
_REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}

__all__ = [
    "ALLOWED_MIME_TYPES",
    "ContentTooLargeError",
    "ContentTypeNotAllowedError",
    "DnsResolutionError",
    "FetchTimeoutError",
    "RedirectLimitError",
    "RedirectLoopError",
    "RemoteFetchOutcome",
    "TargetNotPublicError",
    "UpstreamError",
    "UrlShapeError",
    "fetch_remote_resource",
]


class RedirectLoopError(ValueError):
    pass


class RedirectLimitError(ValueError):
    pass


class ContentTypeNotAllowedError(ValueError):
    def __init__(self, media_type: str) -> None:
        super().__init__(media_type)
        self.media_type = media_type


class ContentTooLargeError(ValueError):
    pass


class FetchTimeoutError(ValueError):
    pass


class UpstreamError(ValueError):
    pass


@dataclass(frozen=True)
class RemoteFetchOutcome:
    requested_url: str
    final_url: str
    redirect_chain: list[str]
    resolved_ips: list[str]
    resolved_hops: list[dict[str, object]]
    status_code: int
    media_type: str
    content_length: int
    body: bytes
    body_sha256: str
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def _build_timeout(settings: Settings) -> httpx.Timeout:
    read_write_pool = settings.evidence_remote_fetch_timeout_seconds
    connect = min(5.0, read_write_pool)
    return httpx.Timeout(
        connect=connect, read=read_write_pool, write=read_write_pool, pool=read_write_pool
    )


async def fetch_remote_resource(
    url: str,
    *,
    settings: Settings,
    resolver: DnsResolver = resolve_public_ips,
) -> RemoteFetchOutcome:
    """Fetch `url` under the full SSRF/size/MIME policy.

    Every hop (the initial URL and each redirect Location) is independently
    revalidated: scheme, userinfo, DNS resolution, IP policy. Streams the
    body and aborts as soon as it would exceed the configured max size,
    never buffering or persisting a partial body. Raises one of the typed
    errors in this module or `net_policy` on any policy violation; callers
    map those to stable API error codes (see `evidence.service`).
    """
    requested_url = url
    chain: list[str] = []
    visited: set[str] = set()
    resolved_hops: list[dict[str, object]] = []
    next_url = url
    hop = 0

    headers = {
        "User-Agent": settings.evidence_remote_fetch_user_agent,
        "Accept": (
            "text/html,application/xhtml+xml,application/pdf,"
            "text/plain,application/xml,text/xml,*/*;q=0.1"
        ),
    }

    async with httpx.AsyncClient(
        timeout=_build_timeout(settings),
        follow_redirects=False,
        trust_env=False,
        headers=headers,
    ) as client:
        while True:
            validated = validate_url_shape(next_url)
            current_url = validated.normalized_url
            if current_url in visited:
                raise RedirectLoopError(current_url)
            visited.add(current_url)
            resolved_ips = await resolver(validated.host, validated.port)
            # Recorded for every hop attempted (initial URL and each
            # redirect Location), not just the final one, so provenance
            # shows exactly which IPs were validated at each step.
            resolved_hops.append(
                {"url": current_url, "host": validated.host, "resolved_ips": resolved_ips}
            )

            try:
                async with client.stream("GET", current_url) as response:
                    if response.status_code in _REDIRECT_STATUS_CODES:
                        location = response.headers.get("location")
                        if not location:
                            raise UpstreamError("redirect_without_location")
                        if hop >= settings.evidence_remote_fetch_max_redirects:
                            raise RedirectLimitError(current_url)
                        chain.append(current_url)
                        next_url = urljoin(current_url, location)
                        hop += 1
                        continue

                    status_code = response.status_code
                    if not (200 <= status_code < 300):
                        # Only a genuine 2xx is evidence. A 4xx/5xx (or any
                        # other non-redirect, non-2xx status such as 304)
                        # must never have its body/MIME processed as if it
                        # were a real document — reject before either check.
                        raise UpstreamError(f"upstream_status_{status_code}")

                    content_type_raw = response.headers.get("content-type", "")
                    media_type = content_type_raw.split(";")[0].strip().lower()
                    if media_type not in ALLOWED_MIME_TYPES:
                        raise ContentTypeNotAllowedError(media_type or "unknown")

                    max_bytes = settings.evidence_remote_fetch_max_bytes
                    content_length_header = response.headers.get("content-length")
                    if content_length_header is not None:
                        try:
                            declared_length = int(content_length_header)
                        except ValueError:
                            declared_length = None
                        if declared_length is not None and declared_length > max_bytes:
                            raise ContentTooLargeError(str(declared_length))

                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > max_bytes:
                            raise ContentTooLargeError(str(len(body)))
                    break
            except httpx.TimeoutException as error:
                raise FetchTimeoutError(current_url) from error
            except httpx.HTTPError as error:
                raise UpstreamError(type(error).__name__) from error

    body_bytes = bytes(body)
    return RemoteFetchOutcome(
        requested_url=requested_url,
        final_url=current_url,
        redirect_chain=chain,
        resolved_ips=resolved_ips,
        resolved_hops=resolved_hops,
        status_code=status_code,
        media_type=media_type,
        content_length=len(body_bytes),
        body=body_bytes,
        body_sha256=hashlib.sha256(body_bytes).hexdigest(),
    )
