"""Builds one MCPServer with the shared AsyncQdrantClient and every enabled toolset."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server import MCPServer

from mcp_qdrant import __version__
from mcp_qdrant.config import Settings
from mcp_qdrant.qdrant_client import build_qdrant_client
from mcp_qdrant.tools import collections as collections_tools
from mcp_qdrant.tools import core as core_tools
from mcp_qdrant.tools import points as points_tools
from mcp_qdrant.tools import query as query_tools
from mcp_qdrant.tools import search as search_tools
from mcp_qdrant.tools.registry import ToolRegistry

SERVER_NAME = "mcp-qdrant"

# One entry per tool module; collections/points/query register under the
# "core" toolset (Fase 1), search under "search" (Fase 2).
# payload/snapshots/admin/observability land in Fases 3-6, each adding one
# module + one line here.
_TOOL_MODULES = (core_tools, collections_tools, points_tools, query_tools, search_tools)


def build_server(settings: Settings | None = None) -> MCPServer[None]:
    """Construct the MCPServer: one shared AsyncQdrantClient, filtered toolsets."""
    settings = settings or Settings.from_env()
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
    return server
