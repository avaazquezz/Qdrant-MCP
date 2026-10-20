"""With `QDRANT_LOCAL_PATH` (embedded Qdrant) a few tools cannot work: the local client
refuses them. The caller must get that sentence, not a generic tool failure.

Uses the real embedded client on a temp dir — no server needed."""

from __future__ import annotations

from pathlib import Path

import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, VectorParams

from mcp_qdrant.tools import admin as admin_tools
from mcp_qdrant.tools.registry import ToolRegistry


async def test_admin_tools_the_embedded_client_cannot_serve_explain_why(tmp_path: Path) -> None:
    client = AsyncQdrantClient(path=str(tmp_path))
    await client.create_collection(
        "docs", vectors_config=VectorParams(size=2, distance=Distance.COSINE)
    )
    server: MCPServer[None] = MCPServer(name="test-server")
    admin_tools.register(ToolRegistry(server, enabled_toolsets=("admin",), read_only=False), client)

    for tool in ("qdrant_collection_cluster_info", "qdrant_collection_optimizations"):
        with pytest.raises(ToolError, match="not supported"):
            await server.call_tool(tool, {"collection_name": "docs"})

    await client.close()
