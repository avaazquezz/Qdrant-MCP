"""Unit tests for the context diet (Fase 19): `with_payload` as a list of keys in every tool
that returns points, and the generated `title`s stripped from the advertised input schemas."""

from __future__ import annotations

import asyncio
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import QueryResponse

from mcp_qdrant.config import ALL_TOOLSETS, Settings
from mcp_qdrant.server import build_server
from mcp_qdrant.tools import points as points_tools
from mcp_qdrant.tools import query as query_tools
from mcp_qdrant.tools import search as search_tools
from mcp_qdrant.tools.registry import ToolRegistry

FIELDS = ["title", "meta.author"]


def _server() -> tuple[MCPServer[None], AsyncMock]:
    mock = AsyncMock()
    mock.query_points.return_value = QueryResponse(points=[])
    mock.query_batch_points.return_value = [QueryResponse(points=[])]
    mock.retrieve.return_value = []
    mock.scroll.return_value = ([], None)
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core", "search"), read_only=False)
    for module in (points_tools, query_tools, search_tools):
        module.register(registry, cast(AsyncQdrantClient, mock))
    return server, mock


@pytest.mark.parametrize(
    ("tool", "args", "method"),
    [
        ("qdrant_query", {"query_vector": [0.1]}, "query_points"),
        ("qdrant_points_get", {"ids": [1]}, "retrieve"),
        ("qdrant_points_scroll", {}, "scroll"),
        ("qdrant_recommend", {"positive": [1]}, "query_points"),
    ],
)
async def test_a_list_of_keys_reaches_qdrant(tool: str, args: dict[str, Any], method: str) -> None:
    server, mock = _server()
    await server.call_tool(tool, {"collection_name": "docs", "with_payload": FIELDS, **args})
    assert getattr(mock, method).call_args.kwargs["with_payload"] == FIELDS


async def test_batch_items_take_a_list_of_keys_too() -> None:
    server, mock = _server()
    await server.call_tool(
        "qdrant_query_batch",
        {"collection_name": "docs", "queries": [{"query_vector": [0.1], "with_payload": FIELDS}]},
    )
    [request] = mock.query_batch_points.call_args.kwargs["requests"]
    assert request.with_payload == FIELDS


async def test_an_empty_list_is_refused_as_ambiguous() -> None:
    server, mock = _server()
    with pytest.raises(ToolError, match="with_payload"):
        await server.call_tool(
            "qdrant_query", {"collection_name": "docs", "query_vector": [0.1], "with_payload": []}
        )
    mock.query_points.assert_not_called()


def test_our_input_models_advertise_no_generated_titles() -> None:
    """~12 KB of the catalog was titles like "Query Vector" for `query_vector`."""
    tools = asyncio.run(build_server(Settings(toolsets=ALL_TOOLSETS)).list_tools())
    titled = [
        (tool.name, name, field)
        for tool in tools
        for name, definition in tool.input_schema.get("$defs", {}).items()
        if name.endswith(("Input", "Spec"))
        for field, prop in definition.get("properties", {}).items()
        if "title" in prop
    ]
    assert titled == []
