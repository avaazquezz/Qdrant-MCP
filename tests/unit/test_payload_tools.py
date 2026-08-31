"""Unit tests for the `payload` toolset (values + indexing): mocked client, no real network."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock

import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    FacetResponse,
    FacetValueHit,
    UpdateResult,
    UpdateStatus,
)

from mcp_qdrant.tools import payload as payload_tools
from mcp_qdrant.tools.registry import ToolRegistry


def _build(client: AsyncQdrantClient) -> MCPServer[None]:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("payload",), read_only=False)
    payload_tools.register(registry, client)
    return server


def _update_ok() -> UpdateResult:
    return UpdateResult(operation_id=1, status=UpdateStatus.COMPLETED)


@pytest.mark.parametrize(
    "tool_name,extra_args,mock_method",
    [
        ("qdrant_payload_set", {"payload": {"city": "ny"}}, "set_payload"),
        ("qdrant_payload_overwrite", {"payload": {"city": "ny"}}, "overwrite_payload"),
        ("qdrant_payload_delete", {"keys": ["city"]}, "delete_payload"),
        ("qdrant_payload_clear", {}, "clear_payload"),
    ],
)
async def test_payload_selector_tools_require_exactly_one_selector(
    tool_name: str, extra_args: dict[str, object], mock_method: str
) -> None:
    server = _build(cast(AsyncQdrantClient, AsyncMock()))

    with pytest.raises(ToolError, match="exactly one"):
        await server.call_tool(tool_name, {"collection_name": "docs", **extra_args})

    with pytest.raises(ToolError, match="exactly one"):
        await server.call_tool(
            tool_name,
            {
                "collection_name": "docs",
                "ids": [1],
                "points_filter": {"must": [{"key": "city", "match": {"value": "ny"}}]},
                **extra_args,
            },
        )


async def test_payload_set_by_ids() -> None:
    mock = AsyncMock()
    mock.set_payload.return_value = _update_ok()
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_payload_set",
        {"collection_name": "docs", "ids": [1], "payload": {"city": "ny"}},
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    mock.set_payload.assert_awaited_once()


async def test_payload_overwrite_by_filter() -> None:
    mock = AsyncMock()
    mock.overwrite_payload.return_value = _update_ok()
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_payload_overwrite",
        {
            "collection_name": "docs",
            "points_filter": {"must": [{"key": "city", "match": {"value": "ny"}}]},
            "payload": {"city": "ny"},
        },
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    mock.overwrite_payload.assert_awaited_once()


async def test_payload_delete_keys() -> None:
    mock = AsyncMock()
    mock.delete_payload.return_value = _update_ok()
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_payload_delete", {"collection_name": "docs", "ids": [1], "keys": ["city"]}
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    _, kwargs = mock.delete_payload.call_args
    assert kwargs["keys"] == ["city"]


async def test_payload_clear() -> None:
    mock = AsyncMock()
    mock.clear_payload.return_value = _update_ok()
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_payload_clear", {"collection_name": "docs", "ids": [1]})
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    mock.clear_payload.assert_awaited_once()


async def test_payload_facet_returns_hits() -> None:
    mock = AsyncMock()
    mock.facet.return_value = FacetResponse(hits=[FacetValueHit(value="ny", count=3)])
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_payload_facet", {"collection_name": "docs", "key": "city"}
    )
    assert isinstance(result, CallToolResult)
    payload = FacetResponse.model_validate(result.structured_content)
    assert payload.hits[0].value == "ny"
    assert payload.hits[0].count == 3


async def test_payload_index_create_simple_schema() -> None:
    mock = AsyncMock()
    mock.create_payload_index.return_value = _update_ok()
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_payload_index_create",
        {"collection_name": "docs", "field_name": "city", "field_schema": "keyword"},
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    _, kwargs = mock.create_payload_index.call_args
    assert kwargs["field_schema"] == "keyword"


async def test_payload_index_create_advanced_schema() -> None:
    mock = AsyncMock()
    mock.create_payload_index.return_value = _update_ok()
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_payload_index_create",
        {
            "collection_name": "docs",
            "field_name": "title",
            "field_schema": {"type": "text", "tokenizer": "word", "lowercase": True},
        },
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    _, kwargs = mock.create_payload_index.call_args
    assert kwargs["field_schema"].tokenizer == "word"


async def test_payload_index_delete() -> None:
    mock = AsyncMock()
    mock.delete_payload_index.return_value = _update_ok()
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_payload_index_delete", {"collection_name": "docs", "field_name": "city"}
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    mock.delete_payload_index.assert_awaited_once()
