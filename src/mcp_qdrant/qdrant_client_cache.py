"""Bounded cache of per-caller AsyncQdrantClient instances for BYO mode.

Constructing a fresh client on every tool call would re-do a TCP/TLS
handshake per request; caching unboundedly on a public endpoint is a memory
leak waiting to happen. Bounded LRU keyed by (url, api_key), closing evicted
clients on a delay so an in-flight call on an evicted client isn't cut off.
"""

from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from urllib.parse import urlsplit

from qdrant_client import AsyncQdrantClient

from mcp_qdrant.qdrant_client import DEFAULT_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

_CacheKey = tuple[str, str | None]


class QdrantClientCache:
    def __init__(self, max_size: int = 256, close_grace_seconds: float = 15.0) -> None:
        self._max_size = max_size
        self._close_grace_seconds = close_grace_seconds
        self._clients: OrderedDict[_CacheKey, AsyncQdrantClient] = OrderedDict()
        self._pending_closes: set[asyncio.Task[None]] = set()

    async def get_or_create(self, url: str, api_key: str | None) -> AsyncQdrantClient:
        key = (url, api_key)
        client = self._clients.get(key)
        if client is not None:
            self._clients.move_to_end(key)
            return client

        # AsyncQdrantClient defaults `port` to 6333 and appends it to `url`
        # whenever the URL itself has no explicit port — verified hands-on
        # that this silently breaks any HTTPS Qdrant on the standard port
        # 443 (e.g. self-hosted behind a normal reverse proxy) unless the
        # matching port is passed explicitly here.
        parsed = urlsplit(url)
        port = parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else 80)
        client = AsyncQdrantClient(
            url=url, api_key=api_key, port=port, timeout=DEFAULT_TIMEOUT_SECONDS
        )
        self._clients[key] = client
        if len(self._clients) > self._max_size:
            _, evicted = self._clients.popitem(last=False)
            self._schedule_close(evicted)
        return client

    def _schedule_close(self, client: AsyncQdrantClient) -> None:
        # ponytail: fixed grace window, not refcounting in-flight calls per
        # client — upgrade to refcounted eviction only if a "client already
        # closed" error is ever actually observed in production.
        async def _delayed_close() -> None:
            await asyncio.sleep(self._close_grace_seconds)
            try:
                await client.close()
            except Exception:
                logger.warning("Error closing evicted Qdrant client", exc_info=True)

        task = asyncio.create_task(_delayed_close())
        self._pending_closes.add(task)
        task.add_done_callback(self._pending_closes.discard)

    async def aclose_all(self) -> None:
        for task in self._pending_closes:
            task.cancel()
        clients, self._clients = list(self._clients.values()), OrderedDict()
        await asyncio.gather(*(c.close() for c in clients), return_exceptions=True)
