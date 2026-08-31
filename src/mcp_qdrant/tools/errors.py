"""Uniform Qdrant-call wrapper for every Fase 1+ tool: retries transport
failures with the same policy as Fase 0's ping, then translates any
surviving UnexpectedResponse/ResponseHandlingException into a ToolError so
the client gets Qdrant's own message instead of the generic "Error
executing tool <name>" a bare crash produces (MCPServer wraps any
uncaught exception in UnexpectedToolError and drops the original message).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from mcp.server.mcpserver.exceptions import ToolError
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from mcp_qdrant.qdrant_client import qdrant_retry


class NoQdrantClientError(RuntimeError):
    """Raised by BYOQdrantClientProxy when no client is bound to this request.

    Defensive fallback only: BYOQdrantMiddleware already rejects a request
    with no usable `Authorization` header before any tool runs, so this
    should never surface in practice.
    """


def _qdrant_error_message(
    exc: UnexpectedResponse | ResponseHandlingException | NoQdrantClientError,
) -> str:
    if isinstance(exc, UnexpectedResponse):
        try:
            return str(exc.structured()["status"]["error"])
        except Exception:
            return str(exc)  # malformed/non-JSON body: fall back to the SDK's own text
    return str(exc)


async def call_qdrant[T](coro_factory: Callable[[], Awaitable[T]]) -> T:
    """Run `coro_factory()` with the shared retry policy; translate a real
    Qdrant error (missing collection, conflict, or transport failure that
    outlasted the retries) into a ToolError carrying Qdrant's own message.

    The retry must wrap a real `async def` (not a lambda passed directly to
    tenacity) — tenacity picks sync vs. async retry behavior based on
    whether the decorated callable itself is a coroutine function, and a
    lambda that merely returns a coroutine does not qualify: tenacity would
    call it once, get back an un-awaited coroutine object (never an
    exception, since constructing a coroutine can't fail), consider that a
    success, and never retry — verified this silently breaks retries.
    """

    @qdrant_retry
    async def _run() -> T:
        return await coro_factory()

    try:
        return await _run()
    except (UnexpectedResponse, ResponseHandlingException, NoQdrantClientError) as exc:
        raise ToolError(_qdrant_error_message(exc)) from exc
