"""Shared AsyncQdrantClient: built once per process in server.py, reused by every tool."""

from __future__ import annotations

import logging

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from mcp_qdrant.config import Settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 10


def build_qdrant_client(settings: Settings) -> AsyncQdrantClient:
    """Build the single shared AsyncQdrantClient for this process.

    Settings already rejects both qdrant_url and qdrant_local_path being set;
    leaving both unset falls back to the client's own localhost:6333 default,
    which matches a Qdrant container run with default ports (e.g. CI).
    """
    return AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        path=settings.qdrant_local_path,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )


@retry(
    retry=retry_if_exception_type(ResponseHandlingException),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    reraise=True,
)
async def ping(client: AsyncQdrantClient) -> int:
    """Cheap read-only connectivity probe: list collections, return the count.

    get_collections() is the lightest authenticated round-trip the API
    offers. Retries only ResponseHandlingException (transport-level failures:
    connection refused, timeout) — an UnexpectedResponse (bad API key, 5xx
    from a reachable server) is not retried, because retrying won't fix it.
    """
    response = await client.get_collections()
    return len(response.collections)
