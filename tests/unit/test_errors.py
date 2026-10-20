"""Unit tests for call_qdrant: real retry behavior and error translation."""

from __future__ import annotations

import httpx
import pytest
from mcp.server.mcpserver.exceptions import ToolError
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from mcp_qdrant.tools.errors import call_qdrant


async def test_call_qdrant_retries_transport_errors_then_succeeds() -> None:
    attempts = {"n": 0}

    async def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ResponseHandlingException(ConnectionError("refused"))
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
        raise ResponseHandlingException(ConnectionError("refused"))

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
