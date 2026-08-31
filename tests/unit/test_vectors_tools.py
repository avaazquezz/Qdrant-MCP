"""Unit tests for the `payload` toolset (batch update + named vectors): mocked client."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock

import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    DenseVectorNameConfig,
    SparseVectorNameConfig,
    UpdateResult,
    UpdateStatus,
    UpsertOperation,
)

from mcp_qdrant.tools import vectors as vectors_tools
from mcp_qdrant.tools.registry import ToolRegistry


def _build(client: AsyncQdrantClient) -> MCPServer[None]:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("payload",), read_only=False)
    vectors_tools.register(registry, client)
    return server


def _update_ok() -> UpdateResult:
    return UpdateResult(operation_id=1, status=UpdateStatus.COMPLETED)


async def test_collection_vector_create_dense() -> None:
    mock = AsyncMock()
    mock.create_vector_name.return_value = _update_ok()
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_collection_vector_create",
        {
            "collection_name": "docs",
            "vector_name": "dense",
            "vector_kind": "dense",
            "size": 4,
            "distance": "Cosine",
        },
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    _, kwargs = mock.create_vector_name.call_args
    assert isinstance(kwargs["vector_name_config"], DenseVectorNameConfig)
    assert kwargs["vector_name_config"].dense.size == 4


async def test_collection_vector_create_dense_requires_size_and_distance() -> None:
    server = _build(cast(AsyncQdrantClient, AsyncMock()))

    with pytest.raises(ToolError, match="requires both"):
        await server.call_tool(
            "qdrant_collection_vector_create",
            {"collection_name": "docs", "vector_name": "dense", "vector_kind": "dense"},
        )


async def test_collection_vector_create_sparse() -> None:
    mock = AsyncMock()
    mock.create_vector_name.return_value = _update_ok()
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_collection_vector_create",
        {"collection_name": "docs", "vector_name": "sparse", "vector_kind": "sparse"},
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    _, kwargs = mock.create_vector_name.call_args
    assert isinstance(kwargs["vector_name_config"], SparseVectorNameConfig)


async def test_collection_vector_create_sparse_rejects_size_and_distance() -> None:
    server = _build(cast(AsyncQdrantClient, AsyncMock()))

    with pytest.raises(ToolError, match="does not take"):
        await server.call_tool(
            "qdrant_collection_vector_create",
            {
                "collection_name": "docs",
                "vector_name": "sparse",
                "vector_kind": "sparse",
                "size": 4,
                "distance": "Cosine",
            },
        )


async def test_collection_vector_delete() -> None:
    mock = AsyncMock()
    mock.delete_vector_name.return_value = _update_ok()
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_collection_vector_delete", {"collection_name": "docs", "vector_name": "sparse"}
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    mock.delete_vector_name.assert_awaited_once_with("docs", vector_name="sparse")


async def test_points_batch_update_builds_operations() -> None:
    mock = AsyncMock()
    mock.batch_update_points.return_value = [_update_ok(), _update_ok()]
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_points_batch_update",
        {
            "collection_name": "docs",
            "operations": [
                {"upsert": {"points": [{"id": 1, "vector": [0.1, 0.2, 0.3, 0.4]}]}},
                {"delete_payload": {"keys": ["city"], "points": [1]}},
            ],
        },
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    _, kwargs = mock.batch_update_points.call_args
    operations = kwargs["update_operations"]
    assert len(operations) == 2
    assert isinstance(operations[0], UpsertOperation)


async def test_vectors_update() -> None:
    mock = AsyncMock()
    mock.update_vectors.return_value = _update_ok()
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_vectors_update",
        {"collection_name": "docs", "points": [{"id": 1, "vector": [0.1, 0.2, 0.3, 0.4]}]},
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    _, kwargs = mock.update_vectors.call_args
    assert kwargs["points"][0].id == 1


async def test_vectors_delete_requires_exactly_one_selector() -> None:
    server = _build(cast(AsyncQdrantClient, AsyncMock()))

    with pytest.raises(ToolError, match="exactly one"):
        await server.call_tool(
            "qdrant_vectors_delete", {"collection_name": "docs", "vector_names": ["sparse"]}
        )


async def test_vectors_delete_by_ids() -> None:
    mock = AsyncMock()
    mock.delete_vectors.return_value = _update_ok()
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_vectors_delete",
        {"collection_name": "docs", "vector_names": ["sparse"], "ids": [1]},
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    _, kwargs = mock.delete_vectors.call_args
    assert kwargs["vectors"] == ["sparse"]
