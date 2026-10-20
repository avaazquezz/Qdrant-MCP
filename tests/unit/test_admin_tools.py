"""Unit tests for the `admin` toolset: mocked client, no real network."""

from __future__ import annotations

import json
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import (
    AliasDescription,
    CollectionClusterInfo,
    CollectionsAliasesResponse,
    CreateAlias,
    CreateAliasOperation,
    DeleteAlias,
    DeleteAliasOperation,
    LocalShardInfo,
    OptimizationsResponse,
    OptimizationsSummary,
    RenameAlias,
    RenameAliasOperation,
    ReplicaState,
)

from mcp_qdrant.tools import admin as admin_tools
from mcp_qdrant.tools.registry import ToolRegistry


def _build(client: AsyncQdrantClient, *, read_only: bool = False) -> MCPServer[None]:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("admin",), read_only=read_only)
    admin_tools.register(registry, client)
    return server


def _not_found(name: str = "docs") -> UnexpectedResponse:
    body = {"status": {"error": f"Not found: Collection `{name}` doesn't exist!"}}
    return UnexpectedResponse(
        status_code=404,
        reason_phrase="Not Found",
        content=json.dumps(body).encode(),
        headers=httpx.Headers({}),
    )


async def test_alias_list_returns_every_alias() -> None:
    mock = AsyncMock()
    mock.get_aliases.return_value = CollectionsAliasesResponse(
        aliases=[AliasDescription(alias_name="docs", collection_name="docs_v2")]
    )
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_alias_list", {})
    assert isinstance(result, CallToolResult)
    payload = CollectionsAliasesResponse.model_validate(result.structured_content)
    assert payload.aliases[0].collection_name == "docs_v2"


async def test_collection_aliases_forwards_name_and_missing_collection_raises() -> None:
    mock = AsyncMock()
    mock.get_collection_aliases.return_value = CollectionsAliasesResponse(aliases=[])
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_collection_aliases", {"collection_name": "docs"})
    assert isinstance(result, CallToolResult)
    assert CollectionsAliasesResponse.model_validate(result.structured_content).aliases == []
    mock.get_collection_aliases.assert_awaited_once_with("docs")

    mock.get_collection_aliases.side_effect = _not_found()
    with pytest.raises(ToolError, match="doesn't exist"):
        await server.call_tool("qdrant_collection_aliases", {"collection_name": "docs"})


async def test_alias_update_builds_each_operation_kind_in_order() -> None:
    mock = AsyncMock()
    mock.update_collection_aliases.return_value = True
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_alias_update",
        {
            "operations": [
                {"create_alias": {"collection_name": "docs_v2", "alias_name": "docs"}},
                {"rename_alias": {"old_alias_name": "docs", "new_alias_name": "docs_old"}},
                {"delete_alias": {"alias_name": "docs_old"}},
            ]
        },
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False

    (operations,), _ = mock.update_collection_aliases.call_args
    assert operations == [
        CreateAliasOperation(
            create_alias=CreateAlias(collection_name="docs_v2", alias_name="docs")
        ),
        RenameAliasOperation(
            rename_alias=RenameAlias(old_alias_name="docs", new_alias_name="docs_old")
        ),
        DeleteAliasOperation(delete_alias=DeleteAlias(alias_name="docs_old")),
    ]


async def test_alias_update_requires_at_least_one_operation() -> None:
    mock = AsyncMock()
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError):
        await server.call_tool("qdrant_alias_update", {"operations": []})
    mock.update_collection_aliases.assert_not_awaited()


async def test_alias_update_rejects_an_operation_of_unknown_kind() -> None:
    mock = AsyncMock()
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError):
        await server.call_tool("qdrant_alias_update", {"operations": [{"drop_alias": {}}]})
    mock.update_collection_aliases.assert_not_awaited()


async def test_alias_update_surfaces_qdrants_own_error() -> None:
    mock = AsyncMock()
    mock.update_collection_aliases.side_effect = _not_found("nope")
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError, match="nope"):
        await server.call_tool(
            "qdrant_alias_update",
            {"operations": [{"create_alias": {"collection_name": "nope", "alias_name": "x"}}]},
        )


async def test_collection_cluster_info_returns_the_shard_layout() -> None:
    mock = AsyncMock()
    mock.collection_cluster_info.return_value = CollectionClusterInfo(
        peer_id=1,
        shard_count=1,
        local_shards=[
            LocalShardInfo(shard_id=0, points_count=3, state=ReplicaState.ACTIVE),
        ],
        remote_shards=[],
        shard_transfers=[],
    )
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_collection_cluster_info", {"collection_name": "docs"})
    assert isinstance(result, CallToolResult)
    payload = CollectionClusterInfo.model_validate(result.structured_content)
    assert payload.shard_count == 1
    assert payload.local_shards[0].points_count == 3
    mock.collection_cluster_info.assert_awaited_once_with("docs")


async def test_collection_cluster_info_missing_collection_raises() -> None:
    mock = AsyncMock()
    mock.collection_cluster_info.side_effect = _not_found()
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError, match="doesn't exist"):
        await server.call_tool("qdrant_collection_cluster_info", {"collection_name": "docs"})


def _optimizations_client() -> tuple[MagicMock, AsyncMock]:
    """A client whose low-level `collections_api.get_optimizations` returns a
    response envelope, like the real REST layer (the tool must unwrap `.result`)."""
    envelope = MagicMock()
    envelope.result = OptimizationsResponse(
        summary=OptimizationsSummary(
            queued_optimizations=0, queued_segments=0, queued_points=0, idle_segments=1
        ),
        running=[],
    )
    get_optimizations = AsyncMock(return_value=envelope)
    client = MagicMock()
    client.http.collections_api.get_optimizations = get_optimizations
    return client, get_optimizations


async def test_collection_optimizations_unwraps_the_response_envelope() -> None:
    client, get_optimizations = _optimizations_client()
    server = _build(cast(AsyncQdrantClient, client))

    result = await server.call_tool("qdrant_collection_optimizations", {"collection_name": "docs"})
    assert isinstance(result, CallToolResult)
    payload = OptimizationsResponse.model_validate(result.structured_content)
    assert payload.summary.idle_segments == 1

    _, kwargs = get_optimizations.call_args
    assert kwargs["_with"] is None
    assert kwargs["completed_limit"] is None


async def test_collection_optimizations_joins_include_into_the_with_selector() -> None:
    client, get_optimizations = _optimizations_client()
    server = _build(cast(AsyncQdrantClient, client))

    await server.call_tool(
        "qdrant_collection_optimizations",
        {
            "collection_name": "docs",
            "include": ["queued", "completed", "idle_segments"],
            "completed_limit": 5,
        },
    )

    args, kwargs = get_optimizations.call_args
    assert args == ("docs",)
    assert kwargs["_with"] == "queued,completed,idle_segments"
    assert kwargs["completed_limit"] == 5


async def test_collection_optimizations_rejects_unknown_detail_and_bad_limit() -> None:
    client, get_optimizations = _optimizations_client()
    server = _build(cast(AsyncQdrantClient, client))

    with pytest.raises(ToolError):
        await server.call_tool(
            "qdrant_collection_optimizations", {"collection_name": "docs", "include": ["bogus"]}
        )
    with pytest.raises(ToolError):
        await server.call_tool(
            "qdrant_collection_optimizations", {"collection_name": "docs", "completed_limit": 0}
        )
    get_optimizations.assert_not_awaited()


async def test_collection_optimizations_missing_collection_raises() -> None:
    client, get_optimizations = _optimizations_client()
    get_optimizations.side_effect = _not_found()
    server = _build(cast(AsyncQdrantClient, client))

    with pytest.raises(ToolError, match="doesn't exist"):
        await server.call_tool("qdrant_collection_optimizations", {"collection_name": "docs"})


async def test_read_only_mode_removes_the_mutating_alias_tool_only() -> None:
    server = _build(cast(AsyncQdrantClient, AsyncMock()), read_only=True)

    names = {t.name for t in await server.list_tools()}
    assert "qdrant_alias_update" not in names
    assert names == {
        "qdrant_alias_list",
        "qdrant_collection_aliases",
        "qdrant_collection_cluster_info",
        "qdrant_collection_optimizations",
    }


async def test_admin_tools_are_not_registered_unless_the_toolset_is_enabled() -> None:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core",), read_only=False)
    admin_tools.register(registry, cast(AsyncQdrantClient, AsyncMock()))

    assert await server.list_tools() == []
