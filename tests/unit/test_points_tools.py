"""Unit tests for points CRUD tools: mocked client, no real network."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock

import httpx
import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import (
    CountResult,
    FieldCondition,
    Filter,
    MatchValue,
    Record,
    SparseVector,
    UpdateMode,
    UpdateResult,
    UpdateStatus,
)

from mcp_qdrant.tools import points as points_tools
from mcp_qdrant.tools.points import PointsGetResult, PointsScrollResult
from mcp_qdrant.tools.registry import ToolRegistry


def _build(client: AsyncQdrantClient) -> MCPServer[None]:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core",), read_only=False)
    points_tools.register(registry, client)
    return server


def _not_found() -> UnexpectedResponse:
    return UnexpectedResponse(
        status_code=404,
        reason_phrase="Not Found",
        content=b'{"status":{"error":"Not found: Collection `docs` doesn\'t exist!"}}',
        headers=httpx.Headers({}),
    )


async def test_points_upsert_returns_update_result() -> None:
    mock = AsyncMock()
    mock.upsert.return_value = UpdateResult(operation_id=1, status=UpdateStatus.COMPLETED)
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_points_upsert",
        {
            "collection_name": "docs",
            "points": [{"id": 1, "vector": [0.1, 0.2, 0.3, 0.4], "payload": {"city": "ny"}}],
        },
    )
    assert isinstance(result, CallToolResult)
    payload = UpdateResult.model_validate(result.structured_content)
    assert payload.status == UpdateStatus.COMPLETED
    mock.upsert.assert_awaited_once()


async def test_points_upsert_missing_collection_raises_tool_error() -> None:
    mock = AsyncMock()
    mock.upsert.side_effect = _not_found()
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError, match="doesn't exist"):
        await server.call_tool(
            "qdrant_points_upsert",
            {"collection_name": "docs", "points": [{"id": 1, "vector": [0.1, 0.2]}]},
        )


async def test_points_upsert_accepts_named_dense_sparse_and_multivector() -> None:
    mock = AsyncMock()
    mock.upsert.return_value = UpdateResult(operation_id=1, status=UpdateStatus.COMPLETED)
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_points_upsert",
        {
            "collection_name": "docs",
            "points": [
                {
                    "id": 1,
                    "vector": {
                        "dense": [0.1, 0.2, 0.3, 0.4],
                        "sparse": {"indices": [1, 7], "values": [0.5, 0.2]},
                        "colbert": [[1.0, 0.0], [0.0, 1.0]],
                    },
                }
            ],
        },
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False

    _, kwargs = mock.upsert.call_args
    vector = kwargs["points"][0].vector
    assert vector["dense"] == [0.1, 0.2, 0.3, 0.4]
    assert vector["sparse"] == SparseVector(indices=[1, 7], values=[0.5, 0.2])
    assert vector["colbert"] == [[1.0, 0.0], [0.0, 1.0]]


async def test_points_upsert_accepts_unnamed_multivector() -> None:
    mock = AsyncMock()
    mock.upsert.return_value = UpdateResult(operation_id=1, status=UpdateStatus.COMPLETED)
    server = _build(cast(AsyncQdrantClient, mock))

    await server.call_tool(
        "qdrant_points_upsert",
        {"collection_name": "docs", "points": [{"id": 1, "vector": [[1.0, 0.0], [0.0, 1.0]]}]},
    )

    _, kwargs = mock.upsert.call_args
    assert kwargs["points"][0].vector == [[1.0, 0.0], [0.0, 1.0]]


async def test_points_upsert_forwards_write_options() -> None:
    mock = AsyncMock()
    mock.upsert.return_value = UpdateResult(operation_id=1, status=UpdateStatus.COMPLETED)
    server = _build(cast(AsyncQdrantClient, mock))

    await server.call_tool(
        "qdrant_points_upsert",
        {
            "collection_name": "docs",
            "points": [{"id": 1, "vector": [0.1, 0.2]}],
            "wait": False,
            "update_mode": "insert_only",
            "update_filter": {"must": [{"key": "city", "match": {"value": "ny"}}]},
        },
    )

    _, kwargs = mock.upsert.call_args
    assert kwargs["wait"] is False
    assert kwargs["update_mode"] == UpdateMode.INSERT_ONLY
    assert kwargs["update_filter"] == Filter(
        must=[FieldCondition(key="city", match=MatchValue(value="ny"))]
    )


async def test_points_upsert_defaults_are_unconditional_and_waiting() -> None:
    mock = AsyncMock()
    mock.upsert.return_value = UpdateResult(operation_id=1, status=UpdateStatus.COMPLETED)
    server = _build(cast(AsyncQdrantClient, mock))

    await server.call_tool(
        "qdrant_points_upsert",
        {"collection_name": "docs", "points": [{"id": 1, "vector": [0.1, 0.2]}]},
    )

    _, kwargs = mock.upsert.call_args
    assert kwargs["wait"] is True
    assert kwargs["update_mode"] is None
    assert kwargs["update_filter"] is None


async def test_points_upsert_rejects_unknown_update_mode() -> None:
    mock = AsyncMock()
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError):
        await server.call_tool(
            "qdrant_points_upsert",
            {
                "collection_name": "docs",
                "points": [{"id": 1, "vector": [0.1, 0.2]}],
                "update_mode": "merge",
            },
        )
    mock.upsert.assert_not_awaited()


async def test_points_get_returns_records() -> None:
    mock = AsyncMock()
    mock.retrieve.return_value = [Record(id=1, payload={"city": "ny"}, vector=None)]
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_points_get", {"collection_name": "docs", "ids": [1]})
    assert isinstance(result, CallToolResult)
    payload = PointsGetResult.model_validate(result.structured_content)
    assert payload.points[0].payload == {"city": "ny"}


async def test_points_get_unknown_ids_returns_empty_not_error() -> None:
    mock = AsyncMock()
    mock.retrieve.return_value = []
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_points_get", {"collection_name": "docs", "ids": [999]})
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    payload = PointsGetResult.model_validate(result.structured_content)
    assert payload.points == []


async def test_points_delete_requires_exactly_one_selector() -> None:
    server = _build(cast(AsyncQdrantClient, AsyncMock()))

    with pytest.raises(ToolError, match="exactly one"):
        await server.call_tool("qdrant_points_delete", {"collection_name": "docs"})

    with pytest.raises(ToolError, match="exactly one"):
        await server.call_tool(
            "qdrant_points_delete",
            {
                "collection_name": "docs",
                "ids": [1],
                "points_filter": {"must": [{"key": "city", "match": {"value": "ny"}}]},
            },
        )


async def test_points_delete_by_ids_returns_update_result() -> None:
    mock = AsyncMock()
    mock.delete.return_value = UpdateResult(operation_id=2, status=UpdateStatus.COMPLETED)
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_points_delete", {"collection_name": "docs", "ids": [1, 2]}
    )
    assert isinstance(result, CallToolResult)
    payload = UpdateResult.model_validate(result.structured_content)
    assert payload.status == UpdateStatus.COMPLETED


async def test_points_scroll_returns_points_and_offset() -> None:
    mock = AsyncMock()
    mock.scroll.return_value = ([Record(id=1, payload={}, vector=None)], 2)
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_points_scroll", {"collection_name": "docs"})
    assert isinstance(result, CallToolResult)
    payload = PointsScrollResult.model_validate(result.structured_content)
    assert payload.next_page_offset == 2
    assert len(payload.points) == 1


async def test_points_scroll_no_more_pages_offset_is_none() -> None:
    mock = AsyncMock()
    mock.scroll.return_value = ([], None)
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_points_scroll", {"collection_name": "docs"})
    assert isinstance(result, CallToolResult)
    payload = PointsScrollResult.model_validate(result.structured_content)
    assert payload.next_page_offset is None


async def test_points_count_returns_count_result() -> None:
    mock = AsyncMock()
    mock.count.return_value = CountResult(count=5)
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_points_count", {"collection_name": "docs"})
    assert isinstance(result, CallToolResult)
    payload = CountResult.model_validate(result.structured_content)
    assert payload.count == 5
