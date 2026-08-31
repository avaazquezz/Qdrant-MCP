"""Confirms the `payload` toolset's batch-update and named-vector tools work
against a real Qdrant instance.

`qdrant_collection_vector_create`/`_delete` are the highest-risk tools in
this phase: verified hands-on that the underlying `create_vector_name`
endpoint 404s on Qdrant v1.13.6/v1.15.1 and only works from a more recent
server (this project's CI floor is v1.19.0 from Fase 3 onward) — a mock
would never catch that mismatch, only a real server does.
"""

from __future__ import annotations

import os
import uuid

import pytest
from mcp.server import MCPServer
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from mcp_qdrant.tools import vectors as vectors_tools
from mcp_qdrant.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration


async def test_vectors_toolset_against_real_qdrant() -> None:
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    client = AsyncQdrantClient(url=url, timeout=10)
    collection_name = f"mcp-test-{uuid.uuid4().hex[:8]}"

    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("payload",), read_only=False)
    vectors_tools.register(registry, client)

    try:
        await client.create_collection(
            collection_name, vectors_config=VectorParams(size=4, distance=Distance.COSINE)
        )
        await client.upsert(
            collection_name, points=[PointStruct(id=1, vector=[1.0, 0.0, 0.0, 0.0])]
        )

        # 1. Add a dense named vector to an already-populated collection.
        dense_result = await server.call_tool(
            "qdrant_collection_vector_create",
            {
                "collection_name": collection_name,
                "vector_name": "extra_dense",
                "vector_kind": "dense",
                "size": 2,
                "distance": "Dot",
            },
        )
        assert isinstance(dense_result, CallToolResult)
        assert dense_result.is_error is False

        # 2. Add a sparse named vector too.
        sparse_result = await server.call_tool(
            "qdrant_collection_vector_create",
            {"collection_name": collection_name, "vector_name": "sparse", "vector_kind": "sparse"},
        )
        assert isinstance(sparse_result, CallToolResult)
        assert sparse_result.is_error is False
        info = await client.get_collection(collection_name)
        assert "extra_dense" in (info.config.params.vectors or {})
        assert "sparse" in (info.config.params.sparse_vectors or {})

        # 3. Batch update: upsert a new point and set payload on the
        # existing one, atomically, in one call.
        batch_result = await server.call_tool(
            "qdrant_points_batch_update",
            {
                "collection_name": collection_name,
                "operations": [
                    {
                        "upsert": {
                            "points": [
                                {
                                    "id": 2,
                                    "vector": {
                                        "": [0.0, 1.0, 0.0, 0.0],
                                        "extra_dense": [1.0, 0.0],
                                    },
                                }
                            ]
                        }
                    },
                    {"set_payload": {"payload": {"city": "ny"}, "points": [1]}},
                ],
            },
        )
        assert isinstance(batch_result, CallToolResult)
        assert batch_result.is_error is False
        record1 = (await client.retrieve(collection_name, ids=[1], with_payload=True))[0]
        assert record1.payload == {"city": "ny"}

        # 4. Update point 2's extra_dense vector directly.
        update_result = await server.call_tool(
            "qdrant_vectors_update",
            {
                "collection_name": collection_name,
                "points": [{"id": 2, "vector": {"extra_dense": [0.5, 0.5]}}],
            },
        )
        assert isinstance(update_result, CallToolResult)
        assert update_result.is_error is False

        # 5. Delete the extra_dense vector from point 2, then remove the
        # named vector from the collection entirely.
        delete_vec_result = await server.call_tool(
            "qdrant_vectors_delete",
            {"collection_name": collection_name, "vector_names": ["extra_dense"], "ids": [2]},
        )
        assert isinstance(delete_vec_result, CallToolResult)
        assert delete_vec_result.is_error is False

        collection_delete_result = await server.call_tool(
            "qdrant_collection_vector_delete",
            {"collection_name": collection_name, "vector_name": "extra_dense"},
        )
        assert isinstance(collection_delete_result, CallToolResult)
        assert collection_delete_result.is_error is False
        info_after = await client.get_collection(collection_name)
        assert "extra_dense" not in (info_after.config.params.vectors or {})
    finally:
        await client.delete_collection(collection_name)
        await client.close()
