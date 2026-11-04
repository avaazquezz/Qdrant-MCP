"""Unit tests for call_qdrant: real retry behavior and error translation."""

from __future__ import annotations

import httpx
import pytest
from mcp.server.mcpserver.exceptions import ToolError
from qdrant_client.common.client_exceptions import ResourceExhaustedResponse
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from mcp_qdrant.tools.errors import call_qdrant, require_result


async def test_call_qdrant_retries_transport_errors_then_succeeds() -> None:
    attempts = {"n": 0}

    async def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ResponseHandlingException(httpx.ConnectError("refused"))
        return "ok"

    result = await call_qdrant(flaky)

    assert result == "ok"
    assert attempts["n"] == 3


async def test_call_qdrant_translates_unexpected_response_to_tool_error() -> None:
    async def not_found() -> str:
        raise UnexpectedResponse(
            status_code=404,
            reason_phrase="Not Found",
            content=b'{"status":{"error":"Not found: Collection `x` doesn\'t exist!"}}',
            headers=httpx.Headers({}),
        )

    with pytest.raises(ToolError, match="doesn't exist"):
        await call_qdrant(not_found)


async def test_call_qdrant_translates_malformed_response_body() -> None:
    async def bad_body() -> str:
        raise UnexpectedResponse(
            status_code=500,
            reason_phrase="Internal Server Error",
            content=b"not json",
            headers=httpx.Headers({}),
        )

    with pytest.raises(ToolError):
        await call_qdrant(bad_body)


async def test_call_qdrant_translates_exhausted_transport_retries() -> None:
    async def always_down() -> str:
        raise ResponseHandlingException(httpx.ConnectError("refused"))

    with pytest.raises(ToolError):
        await call_qdrant(always_down)


async def test_not_implemented_in_the_embedded_client_becomes_a_tool_error_with_its_message() -> (
    None
):
    """With QDRANT_LOCAL_PATH the embedded client raises NotImplementedError for calls it
    can't emulate (cluster info, optimizer progress). That used to surface as the SDK's
    generic "Error executing tool", hiding the one sentence that explains it."""

    async def local_mode_refuses() -> None:
        raise NotImplementedError("Get optimizations is not supported in the local Qdrant.")

    with pytest.raises(ToolError, match="not supported in the local Qdrant"):
        await call_qdrant(local_mode_refuses)


async def test_not_implemented_is_not_retried() -> None:
    calls = 0

    async def refuses() -> None:
        nonlocal calls
        calls += 1
        raise NotImplementedError("nope")

    with pytest.raises(ToolError):
        await call_qdrant(refuses)

    assert calls == 1


async def test_call_qdrant_does_not_retry_a_request_that_reached_the_server() -> None:
    """A read timeout says nothing about whether Qdrant applied the request, so a
    retry could repeat a write the server already did."""
    attempts = {"n": 0}

    async def slow() -> str:
        attempts["n"] += 1
        raise ResponseHandlingException(httpx.ReadTimeout("timed out"))

    with pytest.raises(ToolError, match="may still have been applied"):
        await call_qdrant(slow)
    assert attempts["n"] == 1


async def test_call_qdrant_says_nothing_was_applied_when_the_connection_never_opened() -> None:
    async def always_down() -> str:
        raise ResponseHandlingException(httpx.ConnectError("refused"))

    with pytest.raises(ToolError, match="nothing was applied"):
        await call_qdrant(always_down)


async def test_call_qdrant_translates_rate_limiting() -> None:
    async def throttled() -> str:
        raise ResourceExhaustedResponse("Too many requests", 7)

    with pytest.raises(ToolError, match="Retry after 7 s"):
        await call_qdrant(throttled)


async def test_call_qdrant_translates_client_side_input_errors() -> None:
    async def rejected() -> str:
        raise ValueError("Collection name can't be `.`")

    with pytest.raises(ToolError, match="can't be"):
        await call_qdrant(rejected)


def test_require_result_raises_a_tool_error_instead_of_asserting() -> None:
    assert require_result(0, "count") == 0  # falsy but present is fine
    with pytest.raises(ToolError, match="expected snapshot"):
        require_result(None, "snapshot")
