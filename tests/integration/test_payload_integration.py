"""Confirms the `payload` toolset's value/index tools work against a real Qdrant instance."""

from __future__ import annotations

import os
import uuid

import pytest
from mcp.server import MCPServer
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, FacetResponse, PointStruct, VectorParams

from mcp_qdrant.tools import payload as payload_tools
from mcp_qdrant.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration


async def test_payload_toolset_against_real_qdrant() -> None:
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    client = AsyncQdrantClient(url=url, timeout=10)
    collection_name = f"mcp-test-{uuid.uuid4().hex[:8]}"

    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("payload",), read_only=False)
    payload_tools.register(registry, client)

    try:
        await client.create_collection(
            collection_name, vectors_config=VectorParams(size=4, distance=Distance.COSINE)
        )
        await client.upsert(
            collection_name,
            points=[
                PointStruct(id=1, vector=[1.0, 0.0, 0.0, 0.0], payload={"city": "ny"}),
                PointStruct(id=2, vector=[0.0, 1.0, 0.0, 0.0], payload={"city": "sf"}),
            ],
        )

        # 1. Index creation before filtering by the field (not required by
        # Qdrant, but this is exactly the tool under test).
        index_result = await server.call_tool(
            "qdrant_payload_index_create",
            {"collection_name": collection_name, "field_name": "city", "field_schema": "keyword"},
        )
        assert isinstance(index_result, CallToolResult)
        assert index_result.is_error is False

        # 2. Set: merge a new field into point 1's payload.
        set_result = await server.call_tool(
            "qdrant_payload_set",
            {"collection_name": collection_name, "ids": [1], "payload": {"country": "us"}},
        )
        assert isinstance(set_result, CallToolResult)
        assert set_result.is_error is False
        record = (await client.retrieve(collection_name, ids=[1], with_payload=True))[0]
        assert record.payload == {"city": "ny", "country": "us"}

        # 3. Overwrite: replace point 1's payload entirely.
        overwrite_result = await server.call_tool(
            "qdrant_payload_overwrite",
            {"collection_name": collection_name, "ids": [1], "payload": {"city": "ny"}},
        )
        assert isinstance(overwrite_result, CallToolResult)
        record = (await client.retrieve(collection_name, ids=[1], with_payload=True))[0]
        assert record.payload == {"city": "ny"}

        # 4. Facet: count points per `city`.
        facet_result = await server.call_tool(
            "qdrant_payload_facet", {"collection_name": collection_name, "key": "city"}
        )
        assert isinstance(facet_result, CallToolResult)
        facet_payload = FacetResponse.model_validate(facet_result.structured_content)
        assert {hit.value for hit in facet_payload.hits} == {"ny", "sf"}

        # 5. Delete: remove a specific key by payload filter.
        delete_result = await server.call_tool(
            "qdrant_payload_delete",
            {
                "collection_name": collection_name,
                "points_filter": {"must": [{"key": "city", "match": {"value": "sf"}}]},
                "keys": ["city"],
            },
        )
        assert isinstance(delete_result, CallToolResult)
        assert delete_result.is_error is False
        record2 = (await client.retrieve(collection_name, ids=[2], with_payload=True))[0]
        assert record2.payload == {}

        # 6. Clear: wipe point 1's payload entirely.
        clear_result = await server.call_tool(
            "qdrant_payload_clear", {"collection_name": collection_name, "ids": [1]}
        )
        assert isinstance(clear_result, CallToolResult)
        assert clear_result.is_error is False
        record1 = (await client.retrieve(collection_name, ids=[1], with_payload=True))[0]
        assert record1.payload == {}

        # 7. Index deletion.
        index_delete_result = await server.call_tool(
            "qdrant_payload_index_delete",
            {"collection_name": collection_name, "field_name": "city"},
        )
        assert isinstance(index_delete_result, CallToolResult)
        assert index_delete_result.is_error is False
    finally:
        await client.delete_collection(collection_name)
        await client.close()
