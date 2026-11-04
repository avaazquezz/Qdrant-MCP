"""Launch the server exactly as the `.mcpb` bundle tells Claude Desktop to, and talk to it with a
real MCP client over stdio. Until 2.8.0 the bundle ran `src/mcp_qdrant/cli.py` as a script, which
puts `src/mcp_qdrant/` first on `sys.path`, so this package's own `qdrant_client.py` shadowed the
real `qdrant_client` and the server died on import — unseen since v1.0.0, because only the
manifest's schema was ever checked."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[2]


async def test_the_mcpb_launch_command_serves_tools() -> None:
    config = json.loads((REPO / "manifest.json").read_text())["server"]["mcp_config"]
    args = [arg.replace("${__dirname}", str(REPO)) for arg in config["args"]]
    params = StdioServerParameters(
        command=config["command"],
        args=args,
        env={**os.environ, "QDRANT_URL": os.environ.get("QDRANT_URL", "http://localhost:6333")},
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        assert "qdrant_health_check" in {tool.name for tool in tools.tools}
        result = await session.call_tool("qdrant_health_check", {})
        assert result.structured_content is not None
        assert result.structured_content["ok"] is True
