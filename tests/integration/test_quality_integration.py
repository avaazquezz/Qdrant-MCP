"""`qdrant_search_quality_eval` on a real Qdrant with a built HNSW index and scalar
quantization: the exact variant is the ground truth, so it must score recall 1.0."""

from __future__ import annotations

import asyncio
import os
import random
import uuid
from typing import Any

import pytest
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    CollectionStatus,
    Distance,
    MultiVectorComparator,
    MultiVectorConfig,
    OptimizersConfigDiff,
    PointStruct,
    ScalarQuantization,
    ScalarQuantizationConfig,
    ScalarType,
    VectorParams,
)

from mcp_qdrant.config import ALL_TOOLSETS, Settings
from mcp_qdrant.server import build_server

pytestmark = pytest.mark.integration

URL = os.environ.get("QDRANT_URL", "http://localhost:6333")


async def _eval(args: dict[str, Any]) -> dict[str, Any]:
    server = build_server(Settings(qdrant_url=URL, toolsets=ALL_TOOLSETS))
    result = await server.call_tool("qdrant_search_quality_eval", args)
    assert isinstance(result, CallToolResult) and result.structured_content is not None
    report: dict[str, Any] = result.structured_content
    return report


async def test_quality_eval_on_an_indexed_quantized_collection() -> None:
    client = AsyncQdrantClient(url=URL, timeout=60)
    name = f"mcp-test-{uuid.uuid4().hex[:8]}"
    rnd = random.Random(7)
    await client.create_collection(
        name,
        vectors_config=VectorParams(size=32, distance=Distance.COSINE),
        optimizers_config=OptimizersConfigDiff(indexing_threshold=10),
        quantization_config=ScalarQuantization(
            scalar=ScalarQuantizationConfig(type=ScalarType.INT8, always_ram=True)
        ),
    )
    points = [PointStruct(id=i, vector=[rnd.random() for _ in range(32)]) for i in range(3000)]
    try:
        for start in range(0, len(points), 1000):
            await client.upsert(name, points[start : start + 1000], wait=True)
        for _ in range(120):
            info = await client.get_collection(name)
            if info.status == CollectionStatus.GREEN and info.indexed_vectors_count:
                break
            await asyncio.sleep(0.5)

        report = await _eval(
            {"collection_name": name, "sample": 10, "variants": [{}, {"exact": True}]}
        )
        default, exact = report["variants"]
        assert report["queries"] == 10 and report["indexed_vectors_count"] > 0
        assert exact["search_params"] == {"exact": True} and exact["recall_mean"] == 1.0
        assert 0.0 <= default["recall_min"] <= default["recall_mean"] <= 1.0
        assert report["notes"] == []
    finally:
        await client.delete_collection(name)
        await client.close()


async def test_quality_eval_on_a_small_multivector_collection() -> None:
    client = AsyncQdrantClient(url=URL)
    name = f"mcp-test-{uuid.uuid4().hex[:8]}"
    rnd = random.Random(3)
    multi = MultiVectorConfig(comparator=MultiVectorComparator.MAX_SIM)
    await client.create_collection(
        name,
        vectors_config={
            "colbert": VectorParams(size=8, distance=Distance.COSINE, multivector_config=multi)
        },
    )
    points = [
        PointStruct(id=i, vector={"colbert": [[rnd.random() for _ in range(8)] for _ in range(3)]})
        for i in range(50)
    ]
    try:
        await client.upsert(name, points, wait=True)
        report = await _eval({"collection_name": name, "sample": 5})
        assert report["using"] == "colbert" and report["queries"] == 5
        assert report["variants"][0]["recall_mean"] == 1.0  # no index yet: exact by construction
        assert any("by construction" in note for note in report["notes"])
    finally:
        await client.delete_collection(name)
        await client.close()
