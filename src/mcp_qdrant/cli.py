"""CLI entrypoint: the `mcp-qdrant` console script."""

from __future__ import annotations

from mcp_qdrant.config import Settings
from mcp_qdrant.http_auth import SharedSecretMiddleware
from mcp_qdrant.logging_setup import configure_logging
from mcp_qdrant.server import build_server


def main() -> int:
    # Order matters: logging must be configured before MCPServer() exists, so
    # our stderr handler wins over the SDK's own internal logging configuration
    # (a no-op once the root logger already has handlers).
    configure_logging()
    settings = Settings.from_env()
    server = build_server(settings)

    if settings.transport == "streamable-http":
        # server.run(transport="streamable-http") builds and serves its own
        # app with no hook for middleware, so the shared-secret auth check
        # is wired in by building the app ourselves instead.
        import uvicorn

        assert settings.shared_secret is not None  # enforced by Settings validation
        app = server.streamable_http_app(host=settings.http_host)
        app.add_middleware(SharedSecretMiddleware, secret=settings.shared_secret)
        uvicorn.run(app, host=settings.http_host, port=settings.http_port)
    else:
        server.run(transport=settings.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
