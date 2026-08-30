"""Tool registration gated by toolset membership and the read-only guard.

Every tool in every toolset (Fase 0's `core` through Fase 6's
`observability`) must register through ToolRegistry.register instead of
calling MCPServer.add_tool directly, so toolset filtering and the read-only
guardrail apply uniformly, with no per-tool opt-in to forget.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from mcp.server import MCPServer
from mcp_types import ToolAnnotations

from mcp_qdrant.config import Toolset

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Wraps one MCPServer instance with toolset filtering and the read-only guard."""

    def __init__(
        self, server: MCPServer[Any], *, enabled_toolsets: tuple[Toolset, ...], read_only: bool
    ) -> None:
        self._server = server
        self._enabled_toolsets = frozenset(enabled_toolsets)
        self._read_only = read_only

    def register(
        self,
        fn: Callable[..., Any],
        *,
        toolset: Toolset,
        annotations: ToolAnnotations,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """Register `fn` as a tool, unless its toolset is disabled or it is a
        destructive tool blocked by QDRANT_MCP_READ_ONLY.

        A skipped tool is simply never added: it never appears in
        tools/list, so a client cannot discover it, let alone call it.
        """
        if toolset not in self._enabled_toolsets:
            logger.debug("Skipping tool %r: toolset %r not enabled", fn.__name__, toolset)
            return
        if self._read_only and annotations.destructive_hint:
            logger.info(
                "Skipping tool %r: destructive_hint=True and QDRANT_MCP_READ_ONLY is set",
                fn.__name__,
            )
            return
        self._server.add_tool(fn, name=name, description=description, annotations=annotations)
