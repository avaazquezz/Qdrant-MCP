"""CLI entrypoint: the `mcp-qdrant` console script."""

from __future__ import annotations

from mcp_qdrant.config import Settings
from mcp_qdrant.logging_setup import configure_logging
from mcp_qdrant.server import build_server


def main() -> int:
    # Order matters: logging must be configured before MCPServer() exists, so
    # our stderr handler wins over the SDK's own internal logging configuration
    # (a no-op once the root logger already has handlers).
    configure_logging()
    settings = Settings.from_env()
    server = build_server(settings)
    server.run(transport=settings.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
