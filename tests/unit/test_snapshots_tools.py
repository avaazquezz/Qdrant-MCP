"""Unit tests for the `snapshots` toolset: mocked client, no real network."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock

import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import SnapshotDescription

from mcp_qdrant.tools import snapshots as snapshots_tools
from mcp_qdrant.tools.registry import ToolRegistry
from mcp_qdrant.tools.snapshots import (
    SnapshotDeleteResult,
    SnapshotDownloadInfo,
    SnapshotRecoverResult,
)


def _build(
    client: AsyncQdrantClient, qdrant_url: str | None = "http://localhost:6333"
) -> MCPServer[None]:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("snapshots",), read_only=False)
    snapshots_tools.register(registry, client, qdrant_url)
    return server


def _desc(name: str = "docs-1.snapshot") -> SnapshotDescription:
    return SnapshotDescription(
        name=name, creation_time="2026-08-31T00:00:00", size=1024, checksum="abc"
    )


async def test_snapshot_create_returns_description() -> None:
    mock = AsyncMock()
    mock.create_snapshot.return_value = _desc()
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_snapshot_create", {"collection_name": "docs"})
    assert isinstance(result, CallToolResult)
    payload = SnapshotDescription.model_validate(result.structured_content)
    assert payload.name == "docs-1.snapshot"


async def test_snapshot_list_returns_descriptions() -> None:
    mock = AsyncMock()
    mock.list_snapshots.return_value = [_desc()]
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_snapshot_list", {"collection_name": "docs"})
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    mock.list_snapshots.assert_awaited_once_with("docs")


async def test_snapshot_delete_returns_true_when_deleted() -> None:
    mock = AsyncMock()
    mock.delete_snapshot.return_value = True
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_snapshot_delete", {"collection_name": "docs", "snapshot_name": "docs-1.snapshot"}
    )
    assert isinstance(result, CallToolResult)
    payload = SnapshotDeleteResult.model_validate(result.structured_content)
    assert payload.deleted is True


async def test_snapshot_delete_returns_false_when_absent_not_error() -> None:
    mock = AsyncMock()
    mock.delete_snapshot.return_value = False
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_snapshot_delete", {"collection_name": "docs", "snapshot_name": "nope"}
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    payload = SnapshotDeleteResult.model_validate(result.structured_content)
    assert payload.deleted is False


async def test_snapshot_recover_returns_true() -> None:
    mock = AsyncMock()
    mock.recover_snapshot.return_value = True
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_snapshot_recover",
        {
            "collection_name": "docs",
            "location": "http://localhost:6333/collections/docs/snapshots/docs-1.snapshot",
        },
    )
    assert isinstance(result, CallToolResult)
    payload = SnapshotRecoverResult.model_validate(result.structured_content)
    assert payload.recovered is True
    _, kwargs = mock.recover_snapshot.call_args
    assert kwargs["location"] == "http://localhost:6333/collections/docs/snapshots/docs-1.snapshot"


async def test_snapshot_download_builds_url() -> None:
    mock = AsyncMock()
    mock.list_snapshots.return_value = [_desc("docs-1.snapshot")]
    server = _build(cast(AsyncQdrantClient, mock), qdrant_url="http://localhost:6333")

    result = await server.call_tool(
        "qdrant_snapshot_download", {"collection_name": "docs", "snapshot_name": "docs-1.snapshot"}
    )
    assert isinstance(result, CallToolResult)
    payload = SnapshotDownloadInfo.model_validate(result.structured_content)
    assert payload.url == "http://localhost:6333/collections/docs/snapshots/docs-1.snapshot"
    assert payload.size == 1024


async def test_snapshot_download_unknown_snapshot_raises_tool_error() -> None:
    mock = AsyncMock()
    mock.list_snapshots.return_value = [_desc("docs-1.snapshot")]
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError, match="not found"):
        await server.call_tool(
            "qdrant_snapshot_download", {"collection_name": "docs", "snapshot_name": "nope"}
        )


async def test_snapshot_download_without_qdrant_url_raises_tool_error() -> None:
    mock = AsyncMock()
    server = _build(cast(AsyncQdrantClient, mock), qdrant_url=None)

    with pytest.raises(ToolError, match="QDRANT_URL"):
        await server.call_tool(
            "qdrant_snapshot_download",
            {"collection_name": "docs", "snapshot_name": "docs-1.snapshot"},
        )


async def test_storage_snapshot_create_returns_description() -> None:
    mock = AsyncMock()
    mock.create_full_snapshot.return_value = _desc("full-1.snapshot")
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_storage_snapshot_create", {})
    assert isinstance(result, CallToolResult)
    payload = SnapshotDescription.model_validate(result.structured_content)
    assert payload.name == "full-1.snapshot"


async def test_storage_snapshot_list_returns_descriptions() -> None:
    mock = AsyncMock()
    mock.list_full_snapshots.return_value = [_desc("full-1.snapshot")]
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_storage_snapshot_list", {})
    assert isinstance(result, CallToolResult)
    assert result.is_error is False


async def test_storage_snapshot_delete_returns_true() -> None:
    mock = AsyncMock()
    mock.delete_full_snapshot.return_value = True
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_storage_snapshot_delete", {"snapshot_name": "full-1.snapshot"}
    )
    assert isinstance(result, CallToolResult)
    payload = SnapshotDeleteResult.model_validate(result.structured_content)
    assert payload.deleted is True


async def test_storage_snapshot_download_builds_url_without_collection_segment() -> None:
    mock = AsyncMock()
    mock.list_full_snapshots.return_value = [_desc("full-1.snapshot")]
    server = _build(cast(AsyncQdrantClient, mock), qdrant_url="http://localhost:6333")

    result = await server.call_tool(
        "qdrant_storage_snapshot_download", {"snapshot_name": "full-1.snapshot"}
    )
    assert isinstance(result, CallToolResult)
    payload = SnapshotDownloadInfo.model_validate(result.structured_content)
    assert payload.url == "http://localhost:6333/snapshots/full-1.snapshot"


async def test_storage_snapshot_download_without_qdrant_url_raises_tool_error() -> None:
    mock = AsyncMock()
    server = _build(cast(AsyncQdrantClient, mock), qdrant_url=None)

    with pytest.raises(ToolError, match="QDRANT_URL"):
        await server.call_tool(
            "qdrant_storage_snapshot_download", {"snapshot_name": "full-1.snapshot"}
        )
