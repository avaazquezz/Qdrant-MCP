"""Confirms points CRUD and qdrant_query work against a real Qdrant instance."""

from __future__ import annotations

import os
import uuid

import pytest
from mcp.server import MCPServer
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, VectorParams

from mcp_qdrant.tools import points as points_tools
from mcp_qdrant.tools import query as query_tools
from mcp_qdrant.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration


async def test_points_upsert_get_query_delete_roundtrip_real_qdrant() -> None:
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    client = AsyncQdrantClient(url=url, timeout=10)
    collection_name = f"mcp-test-{uuid.uuid4().hex[:8]}"

    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core",), read_only=False)
    points_tools.register(registry, client)
    query_tools.register(registry, client)

    try:
        await client.create_collection(
            collection_name, vectors_config=VectorParams(size=4, distance=Distance.COSINE)
        )

        upsert_result = await server.call_tool(
            "qdrant_points_upsert",
            {
                "collection_name": collection_name,
                "points": [
                    {"id": 1, "vector": [1.0, 0.0, 0.0, 0.0], "payload": {"city": "ny"}},
                    {"id": 2, "vector": [0.0, 1.0, 0.0, 0.0], "payload": {"city": "sf"}},
                ],
            },
        )
        assert isinstance(upsert_result, CallToolResult)
        assert upsert_result.is_error is False

        get_result = await server.call_tool(
            "qdrant_points_get", {"collection_name": collection_name, "ids": [1]}
        )
        assert isinstance(get_result, CallToolResult)
        assert get_result.is_error is False
        assert get_result.structured_content["points"][0]["payload"] == {"city": "ny"}

        query_result = await server.call_tool(
            "qdrant_query",
            {
                "collection_name": collection_name,
                "query_vector": [1.0, 0.0, 0.0, 0.0],
                "limit": 1,
            },
        )
        assert isinstance(query_result, CallToolResult)
        assert query_result.is_error is False
        assert query_result.structured_content["points"][0]["payload"] == {"city": "ny"}

        delete_result = await server.call_tool(
            "qdrant_points_delete", {"collection_name": collection_name, "ids": [1, 2]}
        )
        assert isinstance(delete_result, CallToolResult)
        assert delete_result.is_error is False

        count_result = await server.call_tool(
            "qdrant_points_count", {"collection_name": collection_name}
        )
        assert isinstance(count_result, CallToolResult)
        assert count_result.structured_content["count"] == 0
    finally:
        await client.delete_collection(collection_name)
        await client.close()
