"""Unit tests for the SSRF/IP/URL policy (ADR-016, VERTICAL-020).

Pure-function tests: no DB, no real DNS, no real network. `respx`/DB fixtures
belong to tests/golden/evidence for end-to-end remote-fetch scenarios; this
file only exercises cataloging_api.evidence.net_policy in isolation.
"""

from __future__ import annotations

import ast
import asyncio
import inspect
import ipaddress

import pytest

from cataloging_api.evidence import net_policy


class TestValidateUrlShape:
    def test_dotted_decimal_ipv4_literal_accepted_structurally(self) -> None:
        validated = net_policy.validate_url_shape("http://93.184.216.34/path")
        assert validated.host == "93.184.216.34"
        assert validated.port == 80

    def test_dotted_decimal_leading_zero_rejected(self) -> None:
        # ipaddress itself rejects octal-ambiguous leading zeros (CVE-2021-29921
        # class of bug); this asserts we surface that as our own UrlShapeError,
        # not let a leading-zero octet slip through as a "valid hostname".
        with pytest.raises(net_policy.UrlShapeError):
            net_policy.validate_url_shape("http://010.0.0.1/")

    def test_ipv6_literal_bracket_syntax(self) -> None:
        validated = net_policy.validate_url_shape("http://[2001:4860:4860::8888]/")
        assert validated.host == "2001:4860:4860::8888"

    def test_ipv6_loopback_literal_parses_but_is_not_public(self) -> None:
        validated = net_policy.validate_url_shape("http://[::1]/")
        assert validated.host == "::1"
        assert net_policy.is_public_ip(ipaddress.ip_address(validated.host)) is False

    def test_hostname_case_normalization(self) -> None:
        validated = net_policy.validate_url_shape("HTTP://ExAmple.TEST/Path")
        assert validated.host == "example.test"
        assert validated.scheme == "http"

    def test_trailing_dot_hostname_normalized(self) -> None:
        validated = net_policy.validate_url_shape("http://example.test./")
        assert validated.host == "example.test"

    def test_localhost_blocked(self) -> None:
        with pytest.raises(net_policy.UrlShapeError):
            net_policy.validate_url_shape("http://localhost/")

    def test_localhost_with_trailing_dot_blocked(self) -> None:
        with pytest.raises(net_policy.UrlShapeError):
            net_policy.validate_url_shape("http://localhost./")

    def test_idn_punycode_hostname_accepted_structurally(self) -> None:
        validated = net_policy.validate_url_shape("http://xn--exmple-cua.test/")
        assert validated.host == "xn--exmple-cua.test"

    def test_malformed_url_missing_host_rejected(self) -> None:
        with pytest.raises(net_policy.UrlShapeError):
            net_policy.validate_url_shape("http:///path-only")

    def test_fragment_is_dropped_from_normalized_url(self) -> None:
        validated = net_policy.validate_url_shape("https://example.test/path#section-2")
        assert "#" not in validated.normalized_url
        assert validated.normalized_url == "https://example.test:443/path"

    def test_default_ports_applied(self) -> None:
        http = net_policy.validate_url_shape("http://example.test/")
        https = net_policy.validate_url_shape("https://example.test/")
        assert http.port == 80
        assert https.port == 443

    def test_explicit_port_preserved(self) -> None:
        validated = net_policy.validate_url_shape("http://example.test:8080/")
        assert validated.port == 8080

    def test_invalid_port_rejected(self) -> None:
        with pytest.raises(net_policy.UrlShapeError):
            net_policy.validate_url_shape("http://example.test:99999/")

    @pytest.mark.parametrize("scheme", ["ftp", "file", "gopher", "data", "javascript"])
    def test_non_http_schemes_rejected(self, scheme: str) -> None:
        with pytest.raises(net_policy.UrlShapeError):
            net_policy.validate_url_shape(f"{scheme}://example.test/")

    def test_credential_userinfo_url_rejected(self) -> None:
        with pytest.raises(net_policy.UrlShapeError):
            net_policy.validate_url_shape("http://user:pass@example.test/")

    def test_userinfo_without_password_rejected(self) -> None:
        with pytest.raises(net_policy.UrlShapeError):
            net_policy.validate_url_shape("http://user@example.test/")

    @pytest.mark.parametrize(
        "host",
        ["2130706433", "017700000001", "0x7f000001", "0x7f.0.0.1"],
    )
    def test_decimal_octal_hex_ip_tricks_rejected(self, host: str) -> None:
        with pytest.raises(net_policy.UrlShapeError):
            net_policy.validate_url_shape(f"http://{host}/")


class TestIsPublicIp:
    @pytest.mark.parametrize(
        "literal",
        [
            "0.0.0.1",
            "10.1.2.3",
            "100.64.0.1",
            "127.0.0.1",
            "169.254.1.1",
            "172.16.0.1",
            "192.0.0.1",
            "192.0.2.1",
            "192.168.1.1",
            "198.18.0.1",
            "198.51.100.1",
            "203.0.113.1",
            "224.0.0.1",
            "240.0.0.1",
        ],
    )
    def test_blocked_ipv4_ranges(self, literal: str) -> None:
        assert net_policy.is_public_ip(ipaddress.ip_address(literal)) is False

    @pytest.mark.parametrize(
        "literal",
        ["::", "::1", "fc00::1", "fe80::1", "ff02::1", "2001:db8::1"],
    )
    def test_blocked_ipv6_ranges(self, literal: str) -> None:
        assert net_policy.is_public_ip(ipaddress.ip_address(literal)) is False

    def test_public_ipv4_allowed(self) -> None:
        assert net_policy.is_public_ip(ipaddress.ip_address("93.184.216.34")) is True

    def test_public_ipv6_allowed(self) -> None:
        assert net_policy.is_public_ip(ipaddress.ip_address("2001:4860:4860::8888")) is True

    def test_ipv4_mapped_ipv6_public(self) -> None:
        assert net_policy.is_public_ip(ipaddress.ip_address("::ffff:93.184.216.34")) is True

    def test_ipv4_mapped_ipv6_private_blocked(self) -> None:
        assert net_policy.is_public_ip(ipaddress.ip_address("::ffff:10.0.0.5")) is False

    def test_cloud_metadata_literal_blocked(self) -> None:
        assert net_policy.is_public_ip(ipaddress.ip_address("169.254.169.254")) is False


class TestResolvePublicIps:
    async def test_ip_literal_public_short_circuits_without_dns(self) -> None:
        ips = await net_policy.resolve_public_ips("93.184.216.34", 443)
        assert ips == ["93.184.216.34"]

    async def test_ip_literal_private_rejected_without_dns(self) -> None:
        with pytest.raises(net_policy.TargetNotPublicError):
            await net_policy.resolve_public_ips("10.0.0.5", 443)

    async def test_mixed_public_private_dns_answers_rejected(self, monkeypatch) -> None:
        async def fake_getaddrinfo(host, port, **kwargs):
            return [
                (2, 1, 6, "", ("93.184.216.34", port)),
                (2, 1, 6, "", ("10.0.0.5", port)),
            ]

        loop = asyncio.get_running_loop()
        monkeypatch.setattr(loop, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(net_policy.TargetNotPublicError):
            await net_policy.resolve_public_ips("mixed.example.test", 443)

    async def test_all_public_dns_answers_accepted(self, monkeypatch) -> None:
        async def fake_getaddrinfo(host, port, **kwargs):
            return [(2, 1, 6, "", ("93.184.216.34", port))]

        loop = asyncio.get_running_loop()
        monkeypatch.setattr(loop, "getaddrinfo", fake_getaddrinfo)
        ips = await net_policy.resolve_public_ips("safe.example.test", 443)
        assert ips == ["93.184.216.34"]

    async def test_dns_resolution_failure_raises(self, monkeypatch) -> None:
        async def fake_getaddrinfo(host, port, **kwargs):
            raise OSError("nxdomain")

        loop = asyncio.get_running_loop()
        monkeypatch.setattr(loop, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(net_policy.DnsResolutionError):
            await net_policy.resolve_public_ips("nowhere.example.test", 443)


def _imports_dspace(source: str) -> bool:
    """True if `source` actually imports/references the dspace package.

    Deliberately narrower than a raw substring search: these modules'
    docstrings legitimately discuss DSpace in prose (e.g. "separate from the
    DSpace client"), which must not fail this guard. Only a real
    `cataloging_api.dspace` import/attribute access counts.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.split(".")[0] == "dspace" for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] == "dspace":
                return True
            if node.module and "cataloging_api.dspace" in node.module:
                return True
        elif isinstance(node, ast.Attribute) and node.attr == "dspace":
            return True
    return False


def test_remote_fetch_modules_never_import_dspace() -> None:
    from cataloging_api.evidence import html_extraction, remote_fetch
    from cataloging_api.evidence import net_policy as net_policy_mod

    for module in (net_policy_mod, remote_fetch, html_extraction):
        assert not _imports_dspace(inspect.getsource(module)), module.__name__


def test_add_remote_evidence_source_never_imports_dspace() -> None:
    from cataloging_api.evidence import service

    source = inspect.getsource(service.add_remote_evidence_source) + "\n" + inspect.getsource(
        service._persist_remote_source
    )
    assert not _imports_dspace(source)
