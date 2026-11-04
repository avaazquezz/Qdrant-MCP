"""The text block of a tool result is the compact JSON of its structured content.

claude.ai and Desktop's local servers hand the model the text block, not `structuredContent`
(measured 2026-11-04); the SDK's `indent=2` doubled what they read. Uses the real embedded
client on a temp dir — no server needed."""

from __future__ import annotations

import json
from pathlib import Path

from mcp_types import CallToolResult, TextContent
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from mcp_qdrant.server import CompactTextMCPServer
from mcp_qdrant.tools import points as points_tools
from mcp_qdrant.tools.registry import ToolRegistry


async def test_text_block_is_the_compact_json_of_the_structured_content(tmp_path: Path) -> None:
    client = AsyncQdrantClient(path=str(tmp_path))
    await client.create_collection(
        "docs", vectors_config=VectorParams(size=2, distance=Distance.COSINE)
    )
    await client.upsert(
        "docs",
        [PointStruct(id=1, vector=[0.1, 0.2], payload={"title": "España", "tags": ["a", "b"]})],
    )
    server = CompactTextMCPServer(name="test-server")
    points_tools.register(ToolRegistry(server, enabled_toolsets=("core",), read_only=False), client)

    result = await server.call_tool("qdrant_points_scroll", {"collection_name": "docs"})

    assert isinstance(result, CallToolResult) and result.structured_content is not None
    assert len(result.content) == 1 and isinstance(result.content[0], TextContent)
    text = result.content[0].text
    assert json.loads(text) == result.structured_content
    assert text == json.dumps(result.structured_content, separators=(",", ":"), ensure_ascii=False)
    assert "España" in text  # not \u-escaped: escapes would cost more than the indentation saved
    await client.close()
