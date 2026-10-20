"""Real-Qdrant checks for the problems an independent review found and reproduced:
the guard against filters that select every point, `payload_schema_infer` on awkward
indexes/keys, and the honest description of batch updates."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    Distance,
    IntegerIndexParams,
    IntegerIndexType,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from mcp_qdrant.tools import composites as composites_tools
from mcp_qdrant.tools import payload as payload_tools
from mcp_qdrant.tools import points as points_tools
from mcp_qdrant.tools import vectors as vectors_tools
from mcp_qdrant.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration


@pytest.fixture
async def env() -> AsyncIterator[tuple[MCPServer[None], AsyncQdrantClient, str]]:
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    client = AsyncQdrantClient(url=url, timeout=10)
    name = f"mcp-test-{uuid.uuid4().hex[:8]}"

    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core", "payload", "admin"), read_only=False)
    for module in (points_tools, payload_tools, vectors_tools, composites_tools):
        module.register(registry, client)

    await client.create_collection(
        name, vectors_config=VectorParams(size=2, distance=Distance.COSINE)
    )
    await client.upsert(
        name,
        points=[
            PointStruct(
                id=i,
                vector=[1.0, 0.0],
                payload={"city": "ny" if i % 2 else "sf", "n": i, "my key": i, "k[]": i},
            )
            for i in (1, 2, 3, 4)
        ],
    )
    try:
        yield server, client, name
    finally:
        await client.delete_collection(name)
        await client.close()


async def _call(server: MCPServer[None], tool: str, **args: Any) -> dict[str, Any]:
    result = await server.call_tool(tool, args)
    assert isinstance(result, CallToolResult)
    content: dict[str, Any] | None = result.structured_content
    assert content is not None
    return content


@pytest.mark.parametrize(
    "empty", [{}, {"must": []}, {"should": []}, {"must_not": []}, {"must": None}]
)
async def test_an_empty_filter_no_longer_wipes_the_collection(
    env: tuple[MCPServer[None], AsyncQdrantClient, str], empty: dict[str, Any]
) -> None:
    server, client, name = env

    for tool, extra in (
        ("qdrant_points_delete", {}),
        ("qdrant_payload_clear", {}),
        ("qdrant_payload_set", {"payload": {"touched": True}}),
    ):
        with pytest.raises(ToolError, match="no conditions"):
            await server.call_tool(tool, {"collection_name": name, "points_filter": empty, **extra})

    assert (await client.count(name)).count == 4
    first = (await client.retrieve(name, ids=[1]))[0]
    assert first.payload is not None and "touched" not in first.payload


async def test_a_batch_with_an_empty_filter_sends_nothing_not_even_its_valid_operations(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    server, client, name = env

    with pytest.raises(ToolError, match=r"operations\[1\]\.delete\.filter"):
        await server.call_tool(
            "qdrant_points_batch_update",
            {
                "collection_name": name,
                "operations": [
                    {"upsert": {"points": [{"id": 99, "vector": [1.0, 0.0]}]}},
                    {"delete": {"filter": {"must": []}}},
                ],
            },
        )

    assert (await client.count(name)).count == 4
    assert await client.retrieve(name, ids=[99]) == []


async def test_a_filter_with_a_condition_still_deletes_exactly_what_it_matches(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    server, client, name = env

    await _call(
        server,
        "qdrant_points_delete",
        collection_name=name,
        points_filter={"must": {"key": "city", "match": {"value": "ny"}}},
    )

    assert {p.id for p in (await client.scroll(name, limit=10))[0]} == {2, 4}


async def test_a_batch_is_not_all_or_nothing_as_the_tool_now_says(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    """Pins what the `qdrant_points_batch_update` description warns about. If a future
    Qdrant makes batches atomic, this fails and the description should be revisited."""
    server, client, name = env

    with pytest.raises(ToolError):
        await server.call_tool(
            "qdrant_points_batch_update",
            {
                "collection_name": name,
                "operations": [
                    {"upsert": {"points": [{"id": 50, "vector": [1.0, 0.0]}]}},
                    {"upsert": {"points": [{"id": 51, "vector": [1.0, 0.0, 0.0]}]}},  # wrong size
                ],
            },
        )

    assert [p.id for p in await client.retrieve(name, ids=[50, 51])] == [50]  # the first stayed


async def test_schema_infer_survives_a_range_only_integer_index(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    server, client, name = env
    await client.create_payload_index(
        name,
        "n",
        IntegerIndexParams(type=IntegerIndexType.INTEGER, lookup=False, range=True),
    )
    await client.create_payload_index(name, "city", PayloadSchemaType.KEYWORD)

    profile = await _call(server, "qdrant_payload_schema_infer", collection_name=name)

    fields = {f["key"]: f for f in profile["fields"]}
    assert fields["n"]["indexed"] is True and fields["n"]["top_values"] is None
    assert {v["value"] for v in fields["city"]["top_values"]} == {"ny", "sf"}


async def test_schema_infer_emits_keys_that_work_as_filter_keys_and_index_keys(
    env: tuple[MCPServer[None], AsyncQdrantClient, str],
) -> None:
    server, client, name = env
    await client.create_payload_index(name, '"my key"', PayloadSchemaType.INTEGER)

    profile = await _call(server, "qdrant_payload_schema_infer", collection_name=name)

    fields = {f["key"]: f for f in profile["fields"]}
    assert {'"my key"', '"k[]"', "city", "n"} <= set(fields)
    assert fields['"my key"']["indexed"] is True  # matched to the index Qdrant reports
    assert profile["indexed_but_unseen"] == []

    # The emitted keys are usable exactly as printed, in a real filter.
    for key in ('"my key"', '"k[]"'):
        counted = await _call(
            server,
            "qdrant_points_count",
            collection_name=name,
            count_filter={"must": [{"key": key, "range": {"gte": 1}}]},
        )
        assert counted["count"] == 4, key
