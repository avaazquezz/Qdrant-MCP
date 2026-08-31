"""Confirms collection CRUD tools work against a real Qdrant instance."""

from __future__ import annotations

import os
import uuid

import pytest
from mcp.server import MCPServer
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import CollectionInfo

from mcp_qdrant.tools import collections as collections_tools
from mcp_qdrant.tools.collections import CollectionDeleteResult, CollectionExistsResult
from mcp_qdrant.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration


def _unique_name() -> str:
    return f"mcp-test-{uuid.uuid4().hex[:8]}"


async def test_collection_create_update_delete_roundtrip_real_qdrant() -> None:
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    client = AsyncQdrantClient(url=url, timeout=10)
    collection_name = _unique_name()

    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core",), read_only=False)
    collections_tools.register(registry, client)

    try:
        create_result = await server.call_tool(
            "qdrant_collection_create",
            {"collection_name": collection_name, "vector_size": 4, "distance": "Cosine"},
        )
        assert isinstance(create_result, CallToolResult)
        assert create_result.is_error is False
        info = CollectionInfo.model_validate(create_result.structured_content)
        assert info.status is not None

        exists_result = await server.call_tool(
            "qdrant_collection_exists", {"collection_name": collection_name}
        )
        assert isinstance(exists_result, CallToolResult)
        exists_payload = CollectionExistsResult.model_validate(exists_result.structured_content)
        assert exists_payload.exists is True

        update_result = await server.call_tool(
            "qdrant_collection_update",
            {
                "collection_name": collection_name,
                "optimizers_config": {"indexing_threshold": 10000},
            },
        )
        assert isinstance(update_result, CallToolResult)
        assert update_result.is_error is False

        delete_result = await server.call_tool(
            "qdrant_collection_delete", {"collection_name": collection_name}
        )
        assert isinstance(delete_result, CallToolResult)
        delete_payload = CollectionDeleteResult.model_validate(delete_result.structured_content)
        assert delete_payload.deleted is True

        exists_after_delete = await server.call_tool(
            "qdrant_collection_exists", {"collection_name": collection_name}
        )
        assert isinstance(exists_after_delete, CallToolResult)
        exists_after_payload = CollectionExistsResult.model_validate(
            exists_after_delete.structured_content
        )
        assert exists_after_payload.exists is False
    finally:
        await client.delete_collection(collection_name)
        await client.close()


async def test_collection_create_named_vectors_sparse_and_quantization_real_qdrant() -> None:
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    client = AsyncQdrantClient(url=url, timeout=10)
    collection_name = _unique_name()

    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core",), read_only=False)
    collections_tools.register(registry, client)

    try:
        create_result = await server.call_tool(
            "qdrant_collection_create",
            {
                "collection_name": collection_name,
                "vectors": {"dense": {"size": 4, "distance": "Cosine"}},
                "sparse_vectors": {"sparse": {}},
                "quantization_config": {"scalar": {"type": "int8"}},
                "strict_mode_config": {"enabled": True, "max_query_limit": 100},
            },
        )
        assert isinstance(create_result, CallToolResult)
        assert create_result.is_error is False
        info = CollectionInfo.model_validate(create_result.structured_content)
        assert "dense" in (info.config.params.vectors or {})
        assert "sparse" in (info.config.params.sparse_vectors or {})
        assert info.config.strict_mode_config is not None
        assert info.config.strict_mode_config.enabled is True

        # update_collection can only tweak quantization on a vector that
        # already exists, or toggle the collection-wide setting off again —
        # verified hands-on it cannot add a new named vector.
        update_result = await server.call_tool(
            "qdrant_collection_update",
            {"collection_name": collection_name, "quantization_config": "disabled"},
        )
        assert isinstance(update_result, CallToolResult)
        assert update_result.is_error is False
    finally:
        await client.delete_collection(collection_name)
        await client.close()
