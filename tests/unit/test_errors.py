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
