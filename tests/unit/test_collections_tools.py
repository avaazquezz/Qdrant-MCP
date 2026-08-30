"""Unit tests for collection CRUD tools: mocked client, no real network."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import cast
from unittest.mock import AsyncMock

import httpx
import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import CollectionDescription, CollectionInfo, CollectionsResponse

from mcp_qdrant.tools import collections as collections_tools
from mcp_qdrant.tools.collections import CollectionDeleteResult, CollectionExistsResult
from mcp_qdrant.tools.registry import ToolRegistry


def _build(client: AsyncQdrantClient) -> MCPServer[None]:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core",), read_only=False)
    collections_tools.register(registry, client)
    return server


def _not_found(name: str) -> UnexpectedResponse:
    body = {"status": {"error": f"Not found: Collection `{name}` doesn't exist!"}}
    return UnexpectedResponse(
        status_code=404,
        reason_phrase="Not Found",
        content=json.dumps(body).encode(),
        headers=httpx.Headers({}),
    )


async def test_collection_create_returns_collection_info(
    make_collection_info: Callable[..., CollectionInfo],
) -> None:
    mock = AsyncMock()
    mock.create_collection.return_value = True
    mock.get_collection.return_value = make_collection_info(points_count=0)
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_collection_create", {"collection_name": "docs", "vector_size": 4}
    )
    assert isinstance(result, CallToolResult)
    payload = CollectionInfo.model_validate(result.structured_content)
    assert payload.points_count == 0
    mock.create_collection.assert_awaited_once()
    mock.get_collection.assert_awaited_once_with("docs")


async def test_collection_create_duplicate_raises_tool_error_with_real_message() -> None:
    mock = AsyncMock()
    mock.create_collection.side_effect = UnexpectedResponse(
        status_code=409,
        reason_phrase="Conflict",
        content=b'{"status":{"error":"Wrong input: Collection `docs` already exists!"}}',
        headers=httpx.Headers({}),
    )
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError, match="already exists"):
        await server.call_tool(
            "qdrant_collection_create", {"collection_name": "docs", "vector_size": 4}
        )


async def test_collection_list_returns_collections_response() -> None:
    mock = AsyncMock()
    mock.get_collections.return_value = CollectionsResponse(
        collections=[CollectionDescription(name="docs")]
    )
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_collection_list", {})
    assert isinstance(result, CallToolResult)
    payload = CollectionsResponse.model_validate(result.structured_content)
    assert [c.name for c in payload.collections] == ["docs"]


async def test_collection_info_not_found_raises_tool_error() -> None:
    mock = AsyncMock()
    mock.get_collection.side_effect = _not_found("nope")
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError, match="doesn't exist"):
        await server.call_tool("qdrant_collection_info", {"collection_name": "nope"})


async def test_collection_update_returns_collection_info(
    make_collection_info: Callable[..., CollectionInfo],
) -> None:
    mock = AsyncMock()
    mock.update_collection.return_value = True
    mock.get_collection.return_value = make_collection_info(points_count=3)
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_collection_update",
        {"collection_name": "docs", "optimizers_config": {"indexing_threshold": 10000}},
    )
    assert isinstance(result, CallToolResult)
    payload = CollectionInfo.model_validate(result.structured_content)
    assert payload.points_count == 3


async def test_collection_delete_returns_true_when_deleted() -> None:
    mock = AsyncMock()
    mock.delete_collection.return_value = True
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_collection_delete", {"collection_name": "docs"})
    assert isinstance(result, CallToolResult)
    payload = CollectionDeleteResult.model_validate(result.structured_content)
    assert payload.deleted is True


async def test_collection_delete_returns_false_when_absent_not_error() -> None:
    mock = AsyncMock()
    mock.delete_collection.return_value = False
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_collection_delete", {"collection_name": "nope"})
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    payload = CollectionDeleteResult.model_validate(result.structured_content)
    assert payload.deleted is False


async def test_collection_exists_true() -> None:
    mock = AsyncMock()
    mock.collection_exists.return_value = True
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_collection_exists", {"collection_name": "docs"})
    assert isinstance(result, CallToolResult)
    payload = CollectionExistsResult.model_validate(result.structured_content)
    assert payload.exists is True


async def test_collection_exists_false_not_error() -> None:
    mock = AsyncMock()
    mock.collection_exists.return_value = False
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_collection_exists", {"collection_name": "nope"})
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    payload = CollectionExistsResult.model_validate(result.structured_content)
    assert payload.exists is False
