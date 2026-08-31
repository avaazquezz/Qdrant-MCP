"""Builds one MCPServer with the shared AsyncQdrantClient and every enabled toolset."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from mcp.server import MCPServer
from qdrant_client import AsyncQdrantClient

from mcp_qdrant import __version__
from mcp_qdrant.byo_qdrant import BYOQdrantClientProxy
from mcp_qdrant.config import Settings
from mcp_qdrant.qdrant_client import build_qdrant_client
from mcp_qdrant.qdrant_client_cache import QdrantClientCache
from mcp_qdrant.tools import collections as collections_tools
from mcp_qdrant.tools import core as core_tools
from mcp_qdrant.tools import observability as observability_tools
from mcp_qdrant.tools import payload as payload_tools
from mcp_qdrant.tools import points as points_tools
from mcp_qdrant.tools import query as query_tools
from mcp_qdrant.tools import search as search_tools
from mcp_qdrant.tools import snapshots as snapshots_tools
from mcp_qdrant.tools import vectors as vectors_tools
from mcp_qdrant.tools.registry import ToolRegistry

SERVER_NAME = "mcp-qdrant"

# One entry per tool module; collections/points/query register under the
# "core" toolset (Fase 1), search under "search" (Fase 2), payload/vectors
# under "payload" (Fase 3). Fase 5 (cluster admin) was discarded. `snapshots_tools`
# (Fase 4) and `observability_tools` (Fase 6) are wired up separately below:
# they're the only modules whose `register()` also needs the configured
# QDRANT_URL, to build download/metrics URLs.
_TOOL_MODULES = (
    core_tools,
    collections_tools,
    points_tools,
    query_tools,
    search_tools,
    payload_tools,
    vectors_tools,
)


def build_server(
    settings: Settings | None = None, *, qdrant_client_cache: QdrantClientCache | None = None
) -> MCPServer[None]:
    """Construct the MCPServer: one shared AsyncQdrantClient, filtered toolsets.

    In BYO mode (`settings.byo_qdrant`), `client` is a proxy that resolves
    the real client per request from `qdrant_client_cache` instead of a
    single fixed `AsyncQdrantClient` — every tool module closes over it
    identically either way, since attribute lookups on it are lazy.
    """
    settings = settings or Settings.from_env()
    if settings.byo_qdrant:
        assert qdrant_client_cache is not None
        client = cast(AsyncQdrantClient, BYOQdrantClientProxy(qdrant_client_cache))
    else:
        client = build_qdrant_client(settings)

    @asynccontextmanager
    async def lifespan(_: MCPServer[None]) -> AsyncIterator[None]:
        try:
            yield None
        finally:
            await client.close()

    server: MCPServer[None] = MCPServer(name=SERVER_NAME, version=__version__, lifespan=lifespan)
    registry = ToolRegistry(
        server, enabled_toolsets=settings.toolsets, read_only=settings.read_only
    )
    for module in _TOOL_MODULES:
        module.register(registry, client)
    snapshots_tools.register(registry, client, settings.qdrant_url)
    observability_tools.register(registry, client, settings.qdrant_url)
    return server
