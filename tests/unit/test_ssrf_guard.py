"""Unit tests for assert_public_qdrant_url: no real network needed — literal
IPs resolve via getaddrinfo without a DNS query, and the DNS-rebinding case
is exercised with a monkeypatched resolver.
"""

from __future__ import annotations

import socket

import pytest

from mcp_qdrant.ssrf_guard import PrivateHostError, assert_public_qdrant_url


async def test_rejects_non_http_scheme() -> None:
    with pytest.raises(PrivateHostError, match="http"):
        await assert_public_qdrant_url("ftp://example.com")


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:6333",
        "http://localhost:6333",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.5:6333",
        "http://172.16.0.5:6333",
        "http://192.168.1.5:6333",
        "http://[::1]:6333",
    ],
)
async def test_rejects_private_or_loopback_hosts(url: str) -> None:
    with pytest.raises(PrivateHostError):
        await assert_public_qdrant_url(url)


async def test_accepts_public_ip_literal() -> None:
    await assert_public_qdrant_url("http://8.8.8.8:6333")


async def test_dns_rebinding_style_hostname_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_getaddrinfo(host: str, port: object) -> list[tuple[object, ...]]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 0))]

    import asyncio

    loop = asyncio.get_running_loop()
    monkeypatch.setattr(loop, "getaddrinfo", fake_getaddrinfo)

    with pytest.raises(PrivateHostError):
        await assert_public_qdrant_url("http://looks-public.example.com:6333")
