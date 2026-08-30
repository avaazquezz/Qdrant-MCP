"""Unit tests for the shared client's retry policy — no real network."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock

import pytest
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException

from mcp_qdrant.qdrant_client import ping


async def test_ping_retries_transport_errors_then_succeeds() -> None:
    mock = AsyncMock()
    ok_response = AsyncMock(collections=[AsyncMock(), AsyncMock()])
    mock.get_collections.side_effect = [
        ResponseHandlingException(ConnectionError("refused")),
        ResponseHandlingException(ConnectionError("refused")),
        ok_response,
    ]
    client = cast(AsyncQdrantClient, mock)

    count = await ping(client)

    assert count == 2
    assert mock.get_collections.call_count == 3


async def test_ping_does_not_retry_unrelated_errors() -> None:
    mock = AsyncMock()
    mock.get_collections.side_effect = ValueError("not retryable")
    client = cast(AsyncQdrantClient, mock)

    with pytest.raises(ValueError, match="not retryable"):
        await ping(client)

    assert mock.get_collections.call_count == 1
