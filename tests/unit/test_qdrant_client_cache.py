"""Unit tests for QdrantClientCache: no real Qdrant needed — AsyncQdrantClient
does not connect at construction time, only on first real request."""

from __future__ import annotations

import asyncio

import pytest

import mcp_qdrant.qdrant_client_cache as cache_module
from mcp_qdrant.qdrant_client_cache import QdrantClientCache


class _FakeClient:
    def __init__(self, **kwargs: object) -> None:
        self.closed = False
        self.kwargs = kwargs

    async def close(self) -> None:
        self.closed = True


async def test_same_key_returns_same_client() -> None:
    cache = QdrantClientCache()
    a = await cache.get_or_create("http://example.com:6333", None)
    b = await cache.get_or_create("http://example.com:6333", None)
    assert a is b
    await cache.aclose_all()


async def test_different_key_returns_different_client() -> None:
    cache = QdrantClientCache()
    a = await cache.get_or_create("http://example.com:6333", None)
    b = await cache.get_or_create("http://example.com:6333", "some-key")
    assert a is not b
    await cache.aclose_all()


async def test_eviction_beyond_max_size_creates_new_client() -> None:
    cache = QdrantClientCache(max_size=2)
    first = await cache.get_or_create("http://a.example.com:6333", None)
    await cache.get_or_create("http://b.example.com:6333", None)
    await cache.get_or_create("http://c.example.com:6333", None)  # evicts "a"

    again = await cache.get_or_create("http://a.example.com:6333", None)
    assert again is not first
    await cache.aclose_all()


async def test_explicit_port_in_url_is_left_untouched(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cache_module, "AsyncQdrantClient", _FakeClient)
    cache = QdrantClientCache()
    client = await cache.get_or_create("https://qdrant.example.com:6333", None)
    assert client.kwargs["port"] == 6333  # type: ignore[attr-defined]


async def test_https_url_without_port_defaults_to_443(monkeypatch: pytest.MonkeyPatch) -> None:
    # Regression test: AsyncQdrantClient defaults `port` to 6333 and silently
    # appends it to any URL with no explicit port — verified hands-on this
    # breaks a real HTTPS Qdrant on the standard port 443 unless the
    # matching port is passed explicitly.
    monkeypatch.setattr(cache_module, "AsyncQdrantClient", _FakeClient)
    cache = QdrantClientCache()
    client = await cache.get_or_create("https://qdrant.example.com", None)
    assert client.kwargs["port"] == 443  # type: ignore[attr-defined]


async def test_http_url_without_port_defaults_to_80(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cache_module, "AsyncQdrantClient", _FakeClient)
    cache = QdrantClientCache()
    client = await cache.get_or_create("http://qdrant.example.com", None)
    assert client.kwargs["port"] == 80  # type: ignore[attr-defined]


async def test_evicted_client_is_closed_after_grace_period(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cache_module, "AsyncQdrantClient", _FakeClient)
    cache = QdrantClientCache(max_size=1, close_grace_seconds=0.01)
    evicted = await cache.get_or_create("http://a.example.com:6333", None)
    await cache.get_or_create("http://b.example.com:6333", None)  # evicts "a"

    await asyncio.sleep(0.05)
    assert evicted.closed  # type: ignore[attr-defined]
