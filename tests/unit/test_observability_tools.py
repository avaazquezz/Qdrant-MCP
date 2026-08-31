"""Unit tests for the `observability` toolset: mocked client, no real network."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock

import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    CollectionsTelemetry,
    InlineResponse2001,
    InlineResponse2002,
    InlineResponse2005,
    QuotaConfig,
    QuotaStatus,
    QuotaUsage,
    TelemetryData,
)

from mcp_qdrant.tools import observability as observability_tools
from mcp_qdrant.tools.observability import MetricsUrlInfo
from mcp_qdrant.tools.registry import ToolRegistry


def _build(
    client: AsyncQdrantClient, qdrant_url: str | None = "http://localhost:6333"
) -> MCPServer[None]:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("observability",), read_only=False)
    observability_tools.register(registry, client, qdrant_url)
    return server


def _telemetry() -> TelemetryData:
    return TelemetryData(
        id="node-1", collections=CollectionsTelemetry(number_of_collections=2, collections=None)
    )


def _quota_status() -> QuotaStatus:
    return QuotaStatus(
        config=QuotaConfig(enabled=True, max_resident_memory_percent=90),
        usage=QuotaUsage(resident_memory_percent=10, disk_usage_percent=20),
    )


async def test_telemetry_returns_data() -> None:
    mock = AsyncMock()
    mock.http.service_api.telemetry.return_value = InlineResponse2002(
        result=_telemetry(), status="ok", time=0.001
    )
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_telemetry", {})
    assert isinstance(result, CallToolResult)
    payload = TelemetryData.model_validate(result.structured_content)
    assert payload.id == "node-1"
    mock.http.service_api.telemetry.assert_awaited_once()


async def test_metrics_prometheus_returns_url() -> None:
    server = _build(cast(AsyncQdrantClient, AsyncMock()), qdrant_url="http://localhost:6333")

    result = await server.call_tool("qdrant_metrics_prometheus", {})
    assert isinstance(result, CallToolResult)
    payload = MetricsUrlInfo.model_validate(result.structured_content)
    assert payload.url == "http://localhost:6333/metrics"


async def test_metrics_prometheus_without_qdrant_url_raises_tool_error() -> None:
    server = _build(cast(AsyncQdrantClient, AsyncMock()), qdrant_url=None)

    with pytest.raises(ToolError, match="QDRANT_URL"):
        await server.call_tool("qdrant_metrics_prometheus", {})


async def test_quotas_get_returns_status() -> None:
    mock = AsyncMock()
    mock.http.quotas_api.get_quotas.return_value = InlineResponse2005(
        result=_quota_status(), status="ok", time=0.001
    )
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_quotas_get", {})
    assert isinstance(result, CallToolResult)
    payload = QuotaStatus.model_validate(result.structured_content)
    assert payload.config.enabled is True


async def test_quotas_set_builds_quota_config_and_returns_true() -> None:
    mock = AsyncMock()
    mock.http.quotas_api.update_quotas.return_value = InlineResponse2001(
        result=True, status="ok", time=0.001
    )
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool(
        "qdrant_quotas_set", {"enabled": True, "max_resident_memory_percent": 85}
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False

    _, kwargs = mock.http.quotas_api.update_quotas.call_args
    quota_config = kwargs["quota_config"]
    assert isinstance(quota_config, QuotaConfig)
    assert quota_config.enabled is True
    assert quota_config.max_resident_memory_percent == 85
    assert quota_config.max_disk_usage_percent is None


async def test_issues_list_returns_raw_result() -> None:
    mock = AsyncMock()
    mock.http.beta_api.get_issues.return_value = {
        "result": {"issues": [{"id": "x"}]},
        "status": "ok",
        "time": 0.0,
    }
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_issues_list", {})
    assert isinstance(result, CallToolResult)
    assert result.structured_content == {"issues": [{"id": "x"}]}


async def test_issues_clear_returns_true() -> None:
    mock = AsyncMock()
    mock.http.beta_api.clear_issues.return_value = InlineResponse2001(
        result=True, status="ok", time=0.001
    )
    server = _build(cast(AsyncQdrantClient, mock))

    result = await server.call_tool("qdrant_issues_clear", {})
    assert isinstance(result, CallToolResult)
    assert result.structured_content == {"result": True}
