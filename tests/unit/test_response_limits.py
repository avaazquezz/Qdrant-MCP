"""QDRANT_MCP_MAX_LIMIT: a tool call can't ask for more results than the cap, and
it fails loudly (rather than clamping) so the model knows to page."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from qdrant_client import AsyncQdrantClient

from mcp_qdrant.config import DEFAULT_MAX_LIMIT, Settings
from mcp_qdrant.server import build_server
from mcp_qdrant.tools import payload as payload_tools
from mcp_qdrant.tools import points as points_tools
from mcp_qdrant.tools import query as query_tools
from mcp_qdrant.tools import search as search_tools
from mcp_qdrant.tools.registry import ToolRegistry

CAP = 50
_DISCOVER = {"target": 1, "context": [{"positive": 2, "negative": 3}]}


def _build(mock: AsyncMock, max_limit: int = CAP) -> MCPServer[None]:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(
        server,
        enabled_toolsets=("core", "search", "payload"),
        read_only=False,
        max_limit=max_limit,
    )
    client = cast(AsyncQdrantClient, mock)
    points_tools.register(registry, client)
    query_tools.register(registry, client)
    search_tools.register(registry, client)
    payload_tools.register(registry, client)
    return server


# (tool, client method it calls, arguments exactly at the cap, arguments one over)
def _cases() -> list[tuple[str, str, dict[str, Any], dict[str, Any]]]:
    def batch(items: str, item: dict[str, Any], tool: str) -> tuple[Any, ...]:
        return (
            tool,
            "query_batch_points",
            {items: [{**item, "limit": 25}, {**item, "limit": 25}]},
            {items: [{**item, "limit": 25}, {**item, "limit": 26}]},
        )

    return [
        (
            "qdrant_query",
            "query_points",
            {"query_vector": [0.1], "limit": 50},
            {"query_vector": [0.1], "limit": 51},
        ),
        ("qdrant_points_scroll", "scroll", {"limit": 50}, {"limit": 51}),
        (
            "qdrant_recommend",
            "query_points",
            {"positive": [1], "limit": 50},
            {"positive": [1], "limit": 51},
        ),
        ("qdrant_discover", "query_points", {**_DISCOVER, "limit": 50}, {**_DISCOVER, "limit": 51}),
        (
            "qdrant_payload_facet",
            "facet",
            {"key": "city", "limit": 50},
            {"key": "city", "limit": 51},
        ),
        (
            "qdrant_query_groups",
            "query_points_groups",
            {"group_by": "d", "query_vector": [0.1], "limit": 10, "group_size": 5},
            {"group_by": "d", "query_vector": [0.1], "limit": 11, "group_size": 5},
        ),
        (
            "qdrant_recommend_groups",
            "query_points_groups",
            {"group_by": "d", "positive": [1], "limit": 10, "group_size": 5},
            {"group_by": "d", "positive": [1], "limit": 11, "group_size": 5},
        ),
        batch("queries", {"query_vector": [0.1]}, "qdrant_query_batch"),
        batch("requests", {"positive": [1]}, "qdrant_recommend_batch"),
        batch("requests", _DISCOVER, "qdrant_discover_batch"),
        (
            "qdrant_distance_matrix_pairs",
            "search_matrix_pairs",
            {"sample": 10, "limit": 5},
            {"sample": 11, "limit": 5},
        ),
        (
            "qdrant_distance_matrix_offsets",
            "search_matrix_offsets",
            {"sample": 10, "limit": 5},
            {"sample": 11, "limit": 5},
        ),
        ("qdrant_points_get", "retrieve", {"ids": list(range(50))}, {"ids": list(range(51))}),
    ]


@pytest.mark.parametrize(("tool", "method", "at_cap", "over_cap"), _cases())
async def test_a_request_over_the_cap_is_refused_before_reaching_qdrant(
    tool: str, method: str, at_cap: dict[str, Any], over_cap: dict[str, Any]
) -> None:
    mock = AsyncMock()
    server = _build(mock)

    with pytest.raises(ToolError, match=f"cap of {CAP} results") as excinfo:
        await server.call_tool(tool, {"collection_name": "docs", **over_cap})

    assert "QDRANT_MCP_MAX_LIMIT" in str(excinfo.value)
    getattr(mock, method).assert_not_awaited()


@pytest.mark.parametrize(("tool", "method", "at_cap", "over_cap"), _cases())
async def test_a_request_exactly_at_the_cap_goes_through(
    tool: str, method: str, at_cap: dict[str, Any], over_cap: dict[str, Any]
) -> None:
    mock = AsyncMock()
    server = _build(mock)

    try:
        await server.call_tool(tool, {"collection_name": "docs", **at_cap})
    except ToolError as exc:
        # The bare AsyncMock return value may not fit the tool's output model; all that
        # matters here is that the cap did not reject the call.
        assert "cap of" not in str(exc)

    getattr(mock, method).assert_awaited_once()


async def test_the_cap_is_configurable_per_server() -> None:
    mock = AsyncMock()
    server = _build(mock, max_limit=5)

    with pytest.raises(ToolError, match="cap of 5 results"):
        await server.call_tool("qdrant_points_scroll", {"collection_name": "docs", "limit": 6})
    mock.scroll.assert_not_awaited()


def test_check_limit_names_what_was_too_large_and_how_to_recover() -> None:
    registry = ToolRegistry(
        MCPServer(name="t"), enabled_toolsets=("core",), read_only=False, max_limit=10
    )
    registry.check_limit(10)  # at the cap: fine

    with pytest.raises(ToolError) as excinfo:
        registry.check_limit(11, "the number of ids")

    message = str(excinfo.value)
    assert "the number of ids is 11" in message
    assert "cap of 10" in message
    assert "page through the rest" in message


async def test_build_server_applies_the_cap_from_settings() -> None:
    server = build_server(Settings.from_env({"QDRANT_MCP_MAX_LIMIT": "5"}))

    with pytest.raises(ToolError, match="cap of 5 results"):
        await server.call_tool(
            "qdrant_query", {"collection_name": "docs", "query_vector": [0.1], "limit": 6}
        )


async def test_the_default_cap_is_one_thousand() -> None:
    assert DEFAULT_MAX_LIMIT == 1000
    server = build_server(Settings.from_env({}))

    with pytest.raises(ToolError, match="cap of 1000 results"):
        await server.call_tool(
            "qdrant_query", {"collection_name": "docs", "query_vector": [0.1], "limit": 1001}
        )


# --- configuration -----------------------------------------------------------------


def test_max_limit_defaults_and_parses_from_the_environment() -> None:
    assert Settings.from_env({}).max_limit == 1000
    assert Settings.from_env({"QDRANT_MCP_MAX_LIMIT": ""}).max_limit == 1000
    assert Settings.from_env({"QDRANT_MCP_MAX_LIMIT": "250"}).max_limit == 250
    assert Settings.from_env({"QDRANT_MCP_MAX_LIMIT": " 250 "}).max_limit == 250


@pytest.mark.parametrize("bad", ["abc", "1.5", "0", "-3"])
def test_an_invalid_max_limit_fails_at_startup_not_on_the_first_call(bad: str) -> None:
    with pytest.raises(ValueError, match="QDRANT_MCP_MAX_LIMIT|greater than 0"):
        Settings.from_env({"QDRANT_MCP_MAX_LIMIT": bad})
