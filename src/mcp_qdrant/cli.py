"""CLI entrypoint: the `mcp-qdrant` console script."""

from __future__ import annotations

from mcp_qdrant.byo_auth import BYOQdrantMiddleware
from mcp_qdrant.config import Settings
from mcp_qdrant.http_auth import SharedSecretMiddleware
from mcp_qdrant.logging_setup import configure_logging
from mcp_qdrant.qdrant_client_cache import QdrantClientCache
from mcp_qdrant.server import build_server


def main() -> int:
    # Order matters: logging must be configured before MCPServer() exists, so
    # our stderr handler wins over the SDK's own internal logging configuration
    # (a no-op once the root logger already has handlers).
    configure_logging()
    settings = Settings.from_env()
    cache = QdrantClientCache() if settings.byo_qdrant else None
    server = build_server(settings, qdrant_client_cache=cache)

    if settings.transport == "streamable-http":
        # server.run(transport="streamable-http") builds and serves its own
        # app with no hook for middleware, so the auth check(s) are wired in
        # by building the app ourselves instead.
        import uvicorn

        app = server.streamable_http_app(host=settings.http_host)
        if settings.byo_qdrant:
            assert cache is not None
            # add_middleware is LIFO (last added runs first) — BYOQdrantMiddleware
            # is added first so a shared secret, if set, is checked before it
            # spends a DNS resolution on the caller-supplied Qdrant URL.
            app.add_middleware(BYOQdrantMiddleware, cache=cache)
            if settings.shared_secret:
                app.add_middleware(SharedSecretMiddleware, secret=settings.shared_secret)
        else:
            assert settings.shared_secret is not None  # enforced by Settings validation
            app.add_middleware(SharedSecretMiddleware, secret=settings.shared_secret)
        uvicorn.run(app, host=settings.http_host, port=settings.http_port)
    else:
        server.run(transport=settings.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
