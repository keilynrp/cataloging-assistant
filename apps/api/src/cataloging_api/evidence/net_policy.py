"""SSRF policy for remote evidence fetch: URL shape and IP-address classification.

Pure functions plus one async DNS resolution helper. No httpx/network client
lives here; `remote_fetch.py` is the only module that opens a socket. See
ADR-016 for the full threat model and rationale for each check.
"""

from __future__ import annotations

import asyncio
import re
import socket
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address, ip_network
from typing import Protocol
from urllib.parse import urlsplit

ALLOWED_SCHEMES = {"http", "https"}
_BLOCKED_HOSTNAMES = {"localhost"}

# Defense-in-depth beyond ipaddress.is_global: an explicit, auditable list of
# the exact networks the threat model calls out by name, so the policy does
# not rely solely on trusting the stdlib's is_global implementation across
# Python versions.
_EXTRA_BLOCKED_IPV4_NETWORKS: tuple[IPv4Network, ...] = tuple(
    ip_network(cidr)
    for cidr in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",
        "240.0.0.0/4",
    )
)
_EXTRA_BLOCKED_IPV6_NETWORKS: tuple[IPv6Network, ...] = tuple(
    ip_network(cidr)
    for cidr in (
        "::/128",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
        "ff00::/8",
        "2001:db8::/32",  # documentation range
        "64:ff9b::/96",  # NAT64 well-known prefix, defensive
    )
)

# A real public DNS hostname always has at least one non-digit, non-dot
# character. A host that is purely digits/dots, or contains a hex-style
# "0x.." segment, is never a legitimate registered hostname: it can only be
# an attempt to smuggle a decimal/octal/hex-encoded IP literal past a naive
# hostname parser.
_NUMERIC_ONLY_RE = re.compile(r"^[0-9.]+$")
_HEX_SEGMENT_RE = re.compile(r"0[xX][0-9a-fA-F]+")


class UrlShapeError(ValueError):
    """The URL itself is structurally rejected (scheme, userinfo, host, port)."""


class DnsResolutionError(ValueError):
    """The hostname could not be resolved to any address."""


class TargetNotPublicError(ValueError):
    """At least one resolved (or literal) IP address is not globally routable."""

    def __init__(self, host: str, ips: list[str]) -> None:
        super().__init__(f"{host} resolves to a non-public address")
        self.host = host
        self.ips = ips


@dataclass(frozen=True)
class ValidatedUrl:
    scheme: str
    host: str
    port: int
    normalized_url: str


def is_public_ip(ip: IPv4Address | IPv6Address) -> bool:
    """True only if `ip` is globally routable per policy (ADR-016 Fase 2)."""
    if isinstance(ip, IPv6Address):
        mapped = ip.ipv4_mapped
        if mapped is not None:
            return is_public_ip(mapped)
        if any(ip in network for network in _EXTRA_BLOCKED_IPV6_NETWORKS):
            return False
    else:
        if any(ip in network for network in _EXTRA_BLOCKED_IPV4_NETWORKS):
            return False
    return bool(ip.is_global)


def _looks_like_ip_encoding_trick(host: str) -> bool:
    stripped = host.rstrip(".")
    if not stripped:
        return True
    if _NUMERIC_ONLY_RE.fullmatch(stripped):
        return True
    if _HEX_SEGMENT_RE.search(stripped):
        return True
    return False


def validate_url_shape(raw_url: str) -> ValidatedUrl:
    """Structural validation: scheme, userinfo, host, port. No I/O.

    Raises UrlShapeError for any rejection. Never inspects the network.
    """
    if not raw_url or len(raw_url) > 4000:
        raise UrlShapeError("url_too_long_or_empty")

    parts = urlsplit(raw_url)
    scheme = parts.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise UrlShapeError("scheme_not_allowed")
    if parts.username is not None or parts.password is not None:
        raise UrlShapeError("userinfo_not_allowed")

    try:
        port = parts.port
    except ValueError as error:
        raise UrlShapeError("invalid_port") from error
    if port is None:
        port = 443 if scheme == "https" else 80
    if not (1 <= port <= 65535):
        raise UrlShapeError("invalid_port")

    hostname = parts.hostname
    if not hostname:
        raise UrlShapeError("missing_host")
    hostname = hostname.lower().rstrip(".")
    if not hostname:
        raise UrlShapeError("missing_host")
    if hostname in _BLOCKED_HOSTNAMES:
        raise UrlShapeError("blocked_hostname")

    try:
        ip_address(hostname)
        is_literal = True
    except ValueError:
        is_literal = False

    if not is_literal:
        if _looks_like_ip_encoding_trick(hostname):
            raise UrlShapeError("blocked_hostname")
        try:
            hostname.encode("idna")
        except UnicodeError as error:
            raise UrlShapeError("invalid_hostname") from error

    path = parts.path or "/"
    query = f"?{parts.query}" if parts.query else ""
    host_for_url = f"[{hostname}]" if is_literal and ":" in hostname else hostname
    normalized_url = f"{scheme}://{host_for_url}:{port}{path}{query}"
    return ValidatedUrl(scheme=scheme, host=hostname, port=port, normalized_url=normalized_url)


class DnsResolver(Protocol):
    async def __call__(self, host: str, port: int) -> list[str]: ...


async def resolve_public_ips(host: str, port: int) -> list[str]:
    """Resolve `host` and enforce that every returned address is public.

    If `host` is already an IP literal, no DNS lookup happens: it is
    classified directly. Raises DnsResolutionError if resolution fails or
    returns nothing, TargetNotPublicError if any resolved address is not
    public (a single non-public answer rejects the whole hostname, even if
    other answers were public).
    """
    try:
        literal = ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:
        if not is_public_ip(literal):
            raise TargetNotPublicError(host, [host])
        return [host]

    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as error:
        raise DnsResolutionError(host) from error

    ips: list[str] = []
    seen: set[str] = set()
    for _family, _socktype, _proto, _canonname, sockaddr in infos:
        candidate = sockaddr[0].split("%", 1)[0]
        if candidate in seen:
            continue
        seen.add(candidate)
        ips.append(candidate)

    if not ips:
        raise DnsResolutionError(host)
    if not all(is_public_ip(ip_address(candidate)) for candidate in ips):
        raise TargetNotPublicError(host, ips)
    return ips


async def validate_and_resolve(
    raw_url: str, *, resolver: DnsResolver = resolve_public_ips
) -> tuple[ValidatedUrl, list[str]]:
    validated = validate_url_shape(raw_url)
    ips = await resolver(validated.host, validated.port)
    return validated, ips
