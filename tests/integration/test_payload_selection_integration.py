"""Pins what `with_payload` as a list of keys does on a real Qdrant (stated in
`schemas.WithPayloadInput`): nested keys come back in their structure, a key a point lacks is
just absent."""

from __future__ import annotations

import os
import uuid

import pytest
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from mcp_qdrant.config import Settings
from mcp_qdrant.server import build_server

pytestmark = pytest.mark.integration


async def test_payload_key_selection_on_a_real_qdrant() -> None:
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    client = AsyncQdrantClient(url=url)
    name = f"mcp-test-{uuid.uuid4().hex[:8]}"
    server = build_server(Settings(qdrant_url=url))
    await client.create_collection(
        name, vectors_config=VectorParams(size=2, distance=Distance.COSINE)
    )
    payload = {"title": "T", "text": "long " * 50, "meta": {"author": "A", "year": 2026}}
    await client.upsert(name, [PointStruct(id=1, vector=[1.0, 0.0], payload=payload)], wait=True)
    try:
        result = await server.call_tool(
            "qdrant_query",
            {
                "collection_name": name,
                "query_vector": [1.0, 0.0],
                "with_payload": ["title", "meta.author", "missing"],
            },
        )
        assert isinstance(result, CallToolResult) and result.structured_content is not None
        [point] = result.structured_content["points"]
        assert point["payload"] == {"title": "T", "meta": {"author": "A"}}
    finally:
        await client.delete_collection(name)
        await client.close()
