"""Confirms the `observability` toolset works against a real Qdrant instance.

This is the first toolset whose primary mechanism is the low-level REST API
(`client.http.<api>_api.<method>`) rather than `AsyncQdrantClient`'s
high-level convenience methods — none of telemetry/quotas/issues is wrapped
there. A mock can't prove that path actually works; only a real server can.
"""

from __future__ import annotations

import os

import pytest
from mcp.server import MCPServer
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import QuotaConfig

from mcp_qdrant.tools import observability as observability_tools
from mcp_qdrant.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration


async def test_observability_toolset_against_real_qdrant() -> None:
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    client = AsyncQdrantClient(url=url, timeout=10)

    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("observability",), read_only=False)
    observability_tools.register(registry, client, url)

    try:
        # 1. Telemetry: real server-wide stats come back.
        telemetry_result = await server.call_tool("qdrant_telemetry", {})
        assert isinstance(telemetry_result, CallToolResult)
        assert telemetry_result.is_error is False
        assert "collections" in telemetry_result.structured_content

        # 2. Metrics: the constructed scrape URL, not the metrics content.
        metrics_result = await server.call_tool("qdrant_metrics_prometheus", {})
        assert isinstance(metrics_result, CallToolResult)
        assert metrics_result.structured_content["url"] == f"{url}/metrics"

        # 3. Quotas: set then get confirms the change stuck.
        set_result = await server.call_tool(
            "qdrant_quotas_set", {"enabled": True, "max_resident_memory_percent": 85}
        )
        assert isinstance(set_result, CallToolResult)
        assert set_result.is_error is False

        get_result = await server.call_tool("qdrant_quotas_get", {})
        assert isinstance(get_result, CallToolResult)
        assert get_result.structured_content["config"]["enabled"] is True
        assert get_result.structured_content["config"]["max_resident_memory_percent"] == 85

        # 4. Issues: list (Beta, loose shape) and clear both succeed.
        issues_list_result = await server.call_tool("qdrant_issues_list", {})
        assert isinstance(issues_list_result, CallToolResult)
        assert issues_list_result.is_error is False
        assert "issues" in issues_list_result.structured_content

        issues_clear_result = await server.call_tool("qdrant_issues_clear", {})
        assert isinstance(issues_clear_result, CallToolResult)
        assert issues_clear_result.is_error is False
    finally:
        # Leave quotas as found (disabled) so this test is repeatable against
        # a persistent Qdrant instance, not just a fresh throwaway container.
        await client.http.quotas_api.update_quotas(quota_config=QuotaConfig(enabled=False))
        await client.close()
