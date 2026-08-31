"""Confirms the Fase 2 search toolset works against a real Qdrant instance.

These tools are read-only, so the DoD doesn't strictly require integration
coverage — but `qdrant-client==1.19.0` (pinned) is newer than the Qdrant
server CI pins (`v1.13.6`), and a mock can't prove a query-type object the
client builds is one the server actually understands. One test per real
risk (hybrid fusion, batching, grouping, recommend, discover, distance
matrix), not one per tool.
"""

from __future__ import annotations

import os
import uuid

import pytest
from mcp.server import MCPServer
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from mcp_qdrant.tools import query as query_tools
from mcp_qdrant.tools import search as search_tools
from mcp_qdrant.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration


async def test_search_toolset_against_real_qdrant() -> None:
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    client = AsyncQdrantClient(url=url, timeout=10)
    collection_name = f"mcp-test-{uuid.uuid4().hex[:8]}"

    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core", "search"), read_only=False)
    query_tools.register(registry, client)
    search_tools.register(registry, client)

    try:
        await client.create_collection(
            collection_name, vectors_config=VectorParams(size=4, distance=Distance.COSINE)
        )
        await client.upsert(
            collection_name,
            points=[
                PointStruct(id=1, vector=[1.0, 0.0, 0.0, 0.0], payload={"doc": "a"}),
                PointStruct(id=2, vector=[0.9, 0.1, 0.0, 0.0], payload={"doc": "a"}),
                PointStruct(id=3, vector=[0.0, 1.0, 0.0, 0.0], payload={"doc": "b"}),
                PointStruct(id=4, vector=[0.0, 0.9, 0.1, 0.0], payload={"doc": "b"}),
            ],
        )

        # 1. Hybrid search: fusion + prefetch (RRF over two retrieval stages).
        hybrid_result = await server.call_tool(
            "qdrant_query",
            {
                "collection_name": collection_name,
                "fusion": "rrf",
                "prefetch": [
                    {"query_vector": [1.0, 0.0, 0.0, 0.0], "limit": 10},
                    {"query_vector": [0.9, 0.1, 0.0, 0.0], "limit": 10},
                ],
                "limit": 4,
            },
        )
        assert isinstance(hybrid_result, CallToolResult)
        assert hybrid_result.is_error is False
        assert len(hybrid_result.structured_content["points"]) > 0

        # 2. Batch: two independent queries in one round trip.
        batch_result = await server.call_tool(
            "qdrant_query_batch",
            {
                "collection_name": collection_name,
                "queries": [
                    {"query_vector": [1.0, 0.0, 0.0, 0.0], "limit": 1},
                    {"query_vector": [0.0, 1.0, 0.0, 0.0], "limit": 1},
                ],
            },
        )
        assert isinstance(batch_result, CallToolResult)
        assert batch_result.is_error is False
        # A bare list return is wrapped as {"result": [...]} in structured_content.
        assert len(batch_result.structured_content["result"]) == 2

        # 3. Groups: best hit per `doc` payload field.
        groups_result = await server.call_tool(
            "qdrant_query_groups",
            {
                "collection_name": collection_name,
                "group_by": "doc",
                "query_vector": [1.0, 0.0, 0.0, 0.0],
                "group_size": 1,
            },
        )
        assert isinstance(groups_result, CallToolResult)
        assert groups_result.is_error is False
        assert len(groups_result.structured_content["groups"]) == 2

        # 4. Recommend: closer to point 1, further from point 3.
        recommend_result = await server.call_tool(
            "qdrant_recommend",
            {"collection_name": collection_name, "positive": [1], "negative": [3], "limit": 2},
        )
        assert isinstance(recommend_result, CallToolResult)
        assert recommend_result.is_error is False
        top_id = recommend_result.structured_content["points"][0]["id"]
        assert top_id in (1, 2)

        # 5. Discover: target point 1 within a positive/negative context pair.
        discover_result = await server.call_tool(
            "qdrant_discover",
            {
                "collection_name": collection_name,
                "target": 1,
                "context": [{"positive": 2, "negative": 3}],
                "limit": 2,
            },
        )
        assert isinstance(discover_result, CallToolResult)
        assert discover_result.is_error is False
        assert len(discover_result.structured_content["points"]) > 0

        # 6. Distance matrix: pairwise similarity across a sample of points.
        matrix_result = await server.call_tool(
            "qdrant_distance_matrix_pairs",
            {"collection_name": collection_name, "sample": 4, "limit": 2},
        )
        assert isinstance(matrix_result, CallToolResult)
        assert matrix_result.is_error is False
        assert len(matrix_result.structured_content["pairs"]) > 0
    finally:
        await client.delete_collection(collection_name)
        await client.close()
