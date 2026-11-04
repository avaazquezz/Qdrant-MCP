"""Real Qdrant + real fastembed model: text in, ranked points out (Fase 18). Needs the
`embeddings` extra; the model (0.22 GB) is downloaded on first run and cached in
FASTEMBED_CACHE_PATH (CI caches it between runs)."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from mcp.server import MCPServer
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import CreateAlias, CreateAliasOperation

from mcp_qdrant.config import ALL_TOOLSETS, Settings
from mcp_qdrant.server import build_server

pytestmark = pytest.mark.integration

URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DOCS = {
    1: "El Real Decreto regula las ayudas a la vivienda para jóvenes",
    2: "Orden ministerial sobre subvenciones agrícolas y ganaderas",
    3: "Ley de vivienda: limitación de alquileres en zonas tensionadas",
    4: "Resolución sobre becas universitarias para estudiantes",
}
Env = tuple[MCPServer[None], AsyncQdrantClient, str]


@pytest.fixture
async def env() -> AsyncIterator[Env]:
    client = AsyncQdrantClient(url=URL, timeout=30)
    name = f"mcp-test-{uuid.uuid4().hex[:8]}"
    server = build_server(Settings(qdrant_url=URL, toolsets=ALL_TOOLSETS))
    try:
        yield server, client, name
    finally:
        for collection in (name, f"{name}-ext"):
            await client.delete_collection(collection)
        await client.close()


async def _call(server: MCPServer[None], tool: str, args: dict[str, Any]) -> Any:
    result = await server.call_tool(tool, args)
    assert isinstance(result, CallToolResult) and not result.is_error, result
    return result.structured_content


async def _ids(server: MCPServer[None], args: dict[str, Any]) -> list[Any]:
    return [p["id"] for p in (await _call(server, "qdrant_query", args))["points"]]


async def test_text_collection_semantic_bm25_and_hybrid(env: Env) -> None:
    server, client, name = env
    await _call(
        server,
        "qdrant_collection_create",
        {"collection_name": name, "text_model": MODEL, "text_language": "spanish"},
    )
    points = [{"id": i, "text": text} for i, text in DOCS.items()]
    await _call(server, "qdrant_points_upsert", {"collection_name": name, "points": points})

    stored = (await client.retrieve(name, [1]))[0]
    assert stored.payload == {"text": DOCS[1]}

    # Semantic: no word in common with the documents it should find.
    assert (await _ids(server, {"collection_name": name, "query_text": "becas", "limit": 1})) == [4]
    housing = await _ids(
        server, {"collection_name": name, "query_text": "comprar una casa", "limit": 2}
    )
    assert set(housing) == {1, 3}

    # BM25 with the Spanish stemmer and accent folding: plural and unaccented queries match.
    assert set(await _ids(server, {"collection_name": name, "bm25_query": "viviendas"})) == {1, 3}
    assert (await _ids(server, {"collection_name": name, "bm25_query": "jovenes"})) == [1]

    hybrid = await _ids(
        server,
        {
            "collection_name": name,
            "fusion": "rrf",
            "prefetch": [{"query_text": "alquiler de pisos"}, {"bm25_query": "alquiler"}],
            "limit": 1,
        },
    )
    assert hybrid == [3]


async def test_a_model_declared_afterwards_and_queried_through_an_alias(env: Env) -> None:
    server, client, name = env
    external = f"{name}-ext"
    await _call(
        server, "qdrant_collection_create", {"collection_name": external, "vector_size": 384}
    )
    await _call(
        server,
        "qdrant_collection_update",
        {"collection_name": external, "text_models": {"": MODEL}},
    )
    points = [{"id": i, "text": text} for i, text in DOCS.items()]
    await _call(server, "qdrant_points_upsert", {"collection_name": external, "points": points})

    # get_collection resolves an alias (verified), so the contract follows it: a reindex that
    # switches the alias keeps text queries working.
    await client.update_collection_aliases(
        [CreateAliasOperation(create_alias=CreateAlias(collection_name=external, alias_name=name))]
    )
    assert (await _ids(server, {"collection_name": name, "query_text": "becas", "limit": 1})) == [4]


async def test_keyword_only_collection_stores_text_and_ranks_it(env: Env) -> None:
    server, client, name = env
    await _call(
        server, "qdrant_collection_create", {"collection_name": name, "text_language": "spanish"}
    )
    points = [{"id": i, "text": text} for i, text in DOCS.items()]
    await _call(server, "qdrant_points_upsert", {"collection_name": name, "points": points})
    assert set(await _ids(server, {"collection_name": name, "bm25_query": "ayudas jóvenes"})) == {1}
