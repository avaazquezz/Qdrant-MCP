"""Uniform Qdrant-call wrapper for every Fase 1+ tool: retries the failures where
the request never reached Qdrant, with the same policy as Fase 0's ping, then
translates whatever survives into a ToolError so the client gets a real message
instead of the generic "Error executing tool <name>" a bare crash produces
(MCPServer wraps any uncaught exception in UnexpectedToolError and drops the
original message).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from mcp.server.mcpserver.exceptions import ToolError
from qdrant_client.common.client_exceptions import QdrantException, ResourceExhaustedResponse
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from mcp_qdrant.qdrant_client import qdrant_retry, request_never_sent


def _qdrant_error_message(exc: Exception) -> str:
    if isinstance(exc, UnexpectedResponse):
        try:
            return str(exc.structured()["status"]["error"])
        except Exception:
            return str(exc)  # malformed/non-JSON body: fall back to the SDK's own text
    if isinstance(exc, ResponseHandlingException):
        if request_never_sent(exc):
            return f"Could not reach Qdrant ({exc.source!r}); nothing was applied."
        # Not retried: a timeout or an unreadable answer says nothing about whether
        # the server did the work, so repeating a write could do it twice.
        return (
            f"The request reached Qdrant but failed before a usable answer came back "
            f"({exc.source!r}). If this call writes, it may still have been applied: check "
            "the current state before repeating it."
        )
    if isinstance(exc, ResourceExhaustedResponse):
        return (
            f"Qdrant is rate-limiting requests: {exc.message}. Retry after {exc.retry_after_s} s."
        )
    return str(exc)


async def call_qdrant[T](coro_factory: Callable[[], Awaitable[T]]) -> T:
    """Run `coro_factory()` with the shared retry policy; translate a real
    Qdrant error (missing collection, conflict, rate limit, transport failure)
    into a ToolError carrying Qdrant's own message.

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
    # NotImplementedError: the embedded client (QDRANT_LOCAL_PATH) raises it for calls it can't
    # emulate, e.g. cluster info and optimizer progress (verified); its message says so plainly.
    # ValueError: qdrant-client rejects some inputs itself before sending (verified on 1.20: a
    # text `Document` for a dense model without fastembed installed); QdrantException covers
    # the 429 with a Retry-After header.
    except (
        UnexpectedResponse,
        ResponseHandlingException,
        QdrantException,
        NotImplementedError,
        ValueError,
    ) as exc:
        raise ToolError(_qdrant_error_message(exc)) from exc


def require_result[T](result: T | None, what: str) -> T:
    """A Qdrant answer the SDK types as optional but a successful call always
    carries; fail with a message instead of an assert (stripped under `-O`, and
    turned into a message-less "Error executing tool" by the MCP SDK)."""
    if result is None:
        raise ToolError(f"Qdrant answered without the expected {what}.")
    return result
