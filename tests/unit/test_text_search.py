"""Unit tests for text instead of vectors (Fase 18): the collection's text contract, `query_text`
and `bm25_query` in the query tools, `text` in upserts, and the text options of collection
create/update. Mocked client; fastembed replaced by a fake that records its calls."""

from __future__ import annotations

import sys
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    CollectionConfig,
    CollectionInfo,
    CollectionParams,
    CollectionStatus,
    Distance,
    FusionQuery,
    HnswConfig,
    MultiVectorComparator,
    MultiVectorConfig,
    OptimizersConfig,
    OptimizersStatusOneOf,
    QueryResponse,
    SnowballParams,
    TextIndexParams,
    TextQuery,
    UpdateResult,
    UpdateStatus,
    VectorParams,
)

from mcp_qdrant import embeddings
from mcp_qdrant.tools import collections as collections_tools
from mcp_qdrant.tools import points as points_tools
from mcp_qdrant.tools import query as query_tools
from mcp_qdrant.tools import search as search_tools
from mcp_qdrant.tools.registry import ToolRegistry

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CONTRACT = {"mcp_qdrant": {"text_field": "body", "models": {"dense": MODEL}}}


def _info(metadata: dict[str, Any] | None = None, vectors: Any = None) -> CollectionInfo:
    return CollectionInfo(
        status=CollectionStatus.GREEN,
        optimizer_status=OptimizersStatusOneOf.OK,
        segments_count=1,
        points_count=0,
        config=CollectionConfig(
            params=CollectionParams(vectors=vectors),
            hnsw_config=HnswConfig(m=16, ef_construct=100, full_scan_threshold=10000),
            optimizer_config=OptimizersConfig(default_segment_number=0, flush_interval_sec=5),
            metadata=metadata,
        ),
        payload_schema={},
    )


def _client(metadata: dict[str, Any] | None = CONTRACT, vectors: Any = None) -> AsyncMock:
    mock = AsyncMock()
    mock.get_collection.return_value = _info(metadata, vectors)
    mock.query_points.return_value = QueryResponse(points=[])
    mock.query_batch_points.return_value = [QueryResponse(points=[])]
    mock.upsert.return_value = UpdateResult(operation_id=1, status=UpdateStatus.COMPLETED)
    mock.create_collection.return_value = True
    mock.update_collection.return_value = True
    return mock


def _server(mock: AsyncMock) -> MCPServer[None]:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("core", "search"), read_only=False)
    for module in (collections_tools, points_tools, query_tools, search_tools):
        module.register(registry, cast(AsyncQdrantClient, mock))
    return server


@pytest.fixture
def embedded(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, list[str], bool]]:
    """Replace fastembed: each text becomes [len(text), is_query]; the calls are recorded."""
    calls: list[tuple[str, list[str], bool]] = []

    async def fake_embed(model: str, texts: Any, *, is_query: bool) -> list[list[float]]:
        calls.append((model, list(texts), is_query))
        return [[float(len(t)), float(is_query)] for t in texts]

    monkeypatch.setattr(embeddings, "embed", fake_embed)
    monkeypatch.setattr(embeddings, "model_info", lambda model: (MODEL, 384))
    return calls


async def _ok(server: MCPServer[None], tool: str, args: dict[str, Any]) -> Any:
    result = await server.call_tool(tool, args)
    assert isinstance(result, CallToolResult) and not result.is_error, result
    return result.structured_content


# --- embeddings module -----------------------------------------------------------------


def test_missing_extra_says_how_to_install(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "fastembed", None)  # makes `import fastembed` fail
    embeddings._supported.cache_clear()
    try:
        with pytest.raises(ToolError, match=r"mcp-qdrant\[embeddings\]"):
            embeddings.model_info(MODEL)
    finally:
        embeddings._supported.cache_clear()


def test_unknown_model_lists_the_supported_ones() -> None:
    with pytest.raises(ToolError, match="BAAI/bge-small-en-v1.5"):
        embeddings.model_info("nope/model")
    assert embeddings.model_info(MODEL.upper()) == (MODEL, 384)  # canonical name back


# --- query_text / bm25_query -----------------------------------------------------------


async def test_query_text_is_embedded_as_a_query_with_the_declared_model(
    embedded: list[tuple[str, list[str], bool]],
) -> None:
    mock = _client()
    await _ok(_server(mock), "qdrant_query", {"collection_name": "docs", "query_text": "casa"})
    assert embedded == [(MODEL, ["casa"], True)]
    _, kwargs = mock.query_points.call_args
    assert kwargs["query"] == [4.0, 1.0]
    assert kwargs["using"] == "dense"  # the only declared vector, picked without `using`


@pytest.mark.parametrize(
    ("metadata", "args", "error"),
    [
        (None, {}, "declares no text model"),
        ({"mcp_qdrant": {"models": {}}}, {}, "declares no text model"),
        (CONTRACT, {"using": "sparse"}, "'sparse' of 'docs' has no declared text model"),
        (
            {"mcp_qdrant": {"models": {"a": MODEL, "b": MODEL}}},
            {},
            r"several vectors \(\['a', 'b'\]\): set `using`",
        ),
        ({"mcp_qdrant": {"models": "oops"}}, {}, "malformed `mcp_qdrant` metadata"),
        (CONTRACT, {"query_vector": [0.1, 0.2]}, "only one of `query_vector` or `query_text`"),
    ],
)
async def test_query_text_fails_clearly_without_a_usable_model(
    embedded: list[tuple[str, list[str], bool]],
    metadata: dict[str, Any] | None,
    args: dict[str, Any],
    error: str,
) -> None:
    mock = _client(metadata)
    with pytest.raises(ToolError, match=error):
        await _server(mock).call_tool(
            "qdrant_query", {"collection_name": "docs", "query_text": "casa", **args}
        )
    mock.query_points.assert_not_called()


async def test_bm25_query_builds_a_text_query_on_the_declared_text_field() -> None:
    mock = _client()
    await _ok(_server(mock), "qdrant_query", {"collection_name": "docs", "bm25_query": "vivienda"})
    _, kwargs = mock.query_points.call_args
    assert kwargs["query"] == TextQuery.model_validate({"text": {"query": "vivienda"}})
    assert kwargs["using"] == "body"


async def test_bm25_query_needs_using_when_the_collection_declares_nothing() -> None:
    mock = _client(metadata=None)
    with pytest.raises(ToolError, match="`bm25_query` needs `using`"):
        await _server(mock).call_tool(
            "qdrant_query", {"collection_name": "docs", "bm25_query": "x"}
        )
    await _ok(
        _server(mock), "qdrant_query", {"collection_name": "docs", "bm25_query": "x", "using": "t"}
    )
    assert mock.query_points.call_args.kwargs["using"] == "t"


async def test_hybrid_prefetch_resolves_every_stage_reading_the_contract_once(
    embedded: list[tuple[str, list[str], bool]],
) -> None:
    mock = _client()
    await _ok(
        _server(mock),
        "qdrant_query",
        {
            "collection_name": "docs",
            "fusion": "rrf",
            "prefetch": [
                {"query_text": "casa", "limit": 20},
                {"fusion": "rrf", "prefetch": [{"bm25_query": "casa"}, {"query_text": "piso"}]},
            ],
        },
    )
    mock.get_collection.assert_awaited_once()
    assert [texts for _, texts, _ in embedded] == [["casa"], ["piso"]]
    _, kwargs = mock.query_points.call_args
    assert isinstance(kwargs["query"], FusionQuery)
    semantic, nested = kwargs["prefetch"]
    assert (semantic.query, semantic.using) == ([4.0, 1.0], "dense")
    bm25, piso = nested.prefetch
    assert isinstance(bm25.query, TextQuery) and bm25.using == "body"
    assert (piso.query, piso.using) == ([4.0, 1.0], "dense")


async def test_plain_vector_queries_never_read_the_contract() -> None:
    mock = _client()
    await _ok(_server(mock), "qdrant_query", {"collection_name": "docs", "query_vector": [0.1]})
    mock.get_collection.assert_not_called()


async def test_query_batch_and_groups_take_the_text_modes(
    embedded: list[tuple[str, list[str], bool]],
) -> None:
    mock = _client()
    mock.query_points_groups.return_value = {"groups": []}
    server = _server(mock)
    await _ok(
        server,
        "qdrant_query_batch",
        {"collection_name": "docs", "queries": [{"query_text": "casa"}, {"bm25_query": "casa"}]},
    )
    semantic, bm25 = mock.query_batch_points.call_args.kwargs["requests"]
    assert (semantic.query, semantic.using) == ([4.0, 1.0], "dense")
    assert isinstance(bm25.query, TextQuery) and bm25.using == "body"

    await server.call_tool(
        "qdrant_query_groups", {"collection_name": "docs", "group_by": "doc", "query_text": "casa"}
    )
    assert mock.query_points_groups.call_args.kwargs["using"] == "dense"


async def test_query_text_in_a_recommend_prefetch_is_refused_not_ignored() -> None:
    mock = _client()
    with pytest.raises(ToolError, match="only supported by qdrant_query"):
        await _server(mock).call_tool(
            "qdrant_recommend",
            {"collection_name": "docs", "positive": [1], "prefetch": [{"query_text": "x"}]},
        )


# --- text in upserts -------------------------------------------------------------------


async def test_upsert_text_embeds_passages_and_stores_the_text_in_input_order(
    embedded: list[tuple[str, list[str], bool]],
) -> None:
    mock = _client()
    await _ok(
        _server(mock),
        "qdrant_points_upsert",
        {
            "collection_name": "docs",
            "points": [
                {"id": 1, "text": "hola", "payload": {"year": 2026}},
                {"id": 2, "vector": {"dense": [0.5, 0.5]}},
                {"id": 3, "text": "adiós"},
            ],
        },
    )
    assert embedded == [(MODEL, ["hola", "adiós"], False)]  # passages, one batch per model
    points = mock.upsert.call_args.kwargs["points"]
    assert [p.id for p in points] == [1, 2, 3]
    assert points[0].vector == {"dense": [4.0, 0.0]}
    assert points[0].payload == {"year": 2026, "body": "hola"}
    assert points[2].payload == {"body": "adiós"}


async def test_upsert_text_into_the_unnamed_vector_sends_a_plain_vector(
    embedded: list[tuple[str, list[str], bool]],
) -> None:
    mock = _client({"mcp_qdrant": {"models": {"": MODEL}}})
    await _ok(
        _server(mock),
        "qdrant_points_upsert",
        {"collection_name": "docs", "points": [{"id": 1, "text": "hola"}]},
    )
    [point] = mock.upsert.call_args.kwargs["points"]
    assert point.vector == [4.0, 0.0] and point.payload == {"text": "hola"}


async def test_upsert_text_into_a_keyword_only_collection_only_stores_it(
    embedded: list[tuple[str, list[str], bool]],
) -> None:
    mock = _client({"mcp_qdrant": {"models": {}}})
    await _ok(
        _server(mock),
        "qdrant_points_upsert",
        {"collection_name": "docs", "points": [{"id": 1, "text": "hola"}]},
    )
    [point] = mock.upsert.call_args.kwargs["points"]
    assert point.vector == {} and point.payload == {"text": "hola"}
    assert embedded == []


@pytest.mark.parametrize(
    ("metadata", "point", "error"),
    [
        (CONTRACT, {"id": 1, "text": "a", "vector": [0.1]}, "exactly one of `vector` or `text`"),
        (CONTRACT, {"id": 1}, "exactly one of `vector` or `text`"),
        (None, {"id": 1, "text": "a"}, "declares no text setup"),
    ],
)
async def test_upsert_text_fails_clearly(
    embedded: list[tuple[str, list[str], bool]],
    metadata: dict[str, Any] | None,
    point: dict[str, Any],
    error: str,
) -> None:
    mock = _client(metadata)
    with pytest.raises(ToolError, match=error):
        await _server(mock).call_tool(
            "qdrant_points_upsert", {"collection_name": "docs", "points": [point]}
        )
    mock.upsert.assert_not_called()


# --- collection create / update --------------------------------------------------------


async def test_create_with_text_model_and_language(
    embedded: list[tuple[str, list[str], bool]],
) -> None:
    mock = _client()
    await _ok(
        _server(mock),
        "qdrant_collection_create",
        {
            "collection_name": "notes",
            "text_model": MODEL.lower(),
            "text_language": "spanish",
            "metadata": {"owner": "adri"},
        },
    )
    kwargs = mock.create_collection.call_args.kwargs
    assert kwargs["vectors_config"] == {"dense": VectorParams(size=384, distance=Distance.COSINE)}
    assert kwargs["metadata"] == {
        "owner": "adri",
        "mcp_qdrant": {"text_field": "text", "models": {"dense": MODEL}},
    }
    index = mock.create_payload_index.call_args.kwargs
    assert index["field_name"] == "text"
    schema = index["field_schema"]
    assert isinstance(schema, TextIndexParams) and schema.scoring is True
    assert isinstance(schema.stemmer, SnowballParams) and schema.stemmer.language == "spanish"
    assert schema.stopwords == "spanish" and schema.ascii_folding is True


async def test_create_keyword_only_collection_has_no_vectors() -> None:
    mock = _client()
    await _ok(
        _server(mock),
        "qdrant_collection_create",
        {"collection_name": "notes", "text_language": "english", "text_field": "body"},
    )
    kwargs = mock.create_collection.call_args.kwargs
    assert kwargs["vectors_config"] == {}
    assert kwargs["metadata"] == {"mcp_qdrant": {"text_field": "body", "models": {}}}


@pytest.mark.parametrize(
    ("args", "error"),
    [
        ({"vector_size": 4, "text_model": MODEL}, "exactly one of `vector_size`, `vectors`"),
        ({}, "exactly one of `vector_size`, `vectors`"),
        (
            {"text_model": MODEL, "metadata": {"mcp_qdrant": {}}},
            "is written by `text_model`/`text_language`",
        ),
    ],
)
async def test_create_text_options_fail_clearly(
    embedded: list[tuple[str, list[str], bool]], args: dict[str, Any], error: str
) -> None:
    mock = _client()
    with pytest.raises(ToolError, match=error):
        await _server(mock).call_tool(
            "qdrant_collection_create", {"collection_name": "notes", **args}
        )
    mock.create_collection.assert_not_called()


async def test_create_reports_a_failed_bm25_index_after_creating_the_collection() -> None:
    mock = _client()
    mock.create_payload_index.side_effect = ValueError("boom")
    with pytest.raises(ToolError, match="was created, but its BM25 index on 'text' failed"):
        await _server(mock).call_tool(
            "qdrant_collection_create", {"collection_name": "notes", "text_language": "spanish"}
        )


async def test_update_declares_a_model_keeping_the_rest_of_the_contract(
    embedded: list[tuple[str, list[str], bool]],
) -> None:
    contract = {"mcp_qdrant": {"text_field": "body", "models": {"other": MODEL}}}
    mock = _client(contract, vectors={"dense": VectorParams(size=384, distance=Distance.COSINE)})
    await _ok(
        _server(mock),
        "qdrant_collection_update",
        {"collection_name": "docs", "text_models": {"dense": MODEL}},
    )
    assert mock.update_collection.call_args.kwargs["metadata"] == {
        "mcp_qdrant": {"text_field": "body", "models": {"other": MODEL, "dense": MODEL}}
    }


@pytest.mark.parametrize(
    ("vectors", "using", "error"),
    [
        (
            {"dense": VectorParams(size=768, distance=Distance.COSINE)},
            "dense",
            "holds 768-dimensional",
        ),
        (
            {"dense": VectorParams(size=384, distance=Distance.COSINE)},
            "nope",
            "no single dense vector",
        ),
        (VectorParams(size=384, distance=Distance.COSINE), "dense", "no single dense vector"),
        (
            {
                "dense": VectorParams(
                    size=384,
                    distance=Distance.COSINE,
                    multivector_config=MultiVectorConfig(comparator=MultiVectorComparator.MAX_SIM),
                )
            },
            "dense",
            "no single dense vector",
        ),
    ],
)
async def test_update_refuses_a_model_that_cant_have_made_the_vectors(
    embedded: list[tuple[str, list[str], bool]], vectors: Any, using: str, error: str
) -> None:
    mock = _client(None, vectors=vectors)
    with pytest.raises(ToolError, match=error):
        await _server(mock).call_tool(
            "qdrant_collection_update", {"collection_name": "docs", "text_models": {using: MODEL}}
        )
    mock.update_collection.assert_not_called()


async def test_update_declares_the_unnamed_vector_as_empty_name(
    embedded: list[tuple[str, list[str], bool]],
) -> None:
    mock = _client(None, vectors=VectorParams(size=384, distance=Distance.COSINE))
    await _ok(
        _server(mock),
        "qdrant_collection_update",
        {"collection_name": "docs", "text_models": {"": MODEL}},
    )
    assert mock.update_collection.call_args.kwargs["metadata"] == {
        "mcp_qdrant": {"text_field": "text", "models": {"": MODEL}}
    }


async def test_embed_reports_a_failed_download_or_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(model: str, texts: list[str], is_query: bool) -> list[list[float]]:
        raise OSError("connection reset while downloading")

    monkeypatch.setattr(embeddings, "_embed_sync", broken)
    with pytest.raises(ToolError, match="Embedding with 'm' failed: connection reset"):
        await embeddings.embed("m", ["x"], is_query=True)


async def test_embed_passes_its_own_errors_through_unwrapped() -> None:
    with pytest.raises(ToolError, match="is not a text embedding model") as excinfo:
        await embeddings.embed("nope/model", ["x"], is_query=True)
    assert "Embedding with" not in str(excinfo.value)


async def test_query_text_with_an_explicit_declared_vector(
    embedded: list[tuple[str, list[str], bool]],
) -> None:
    mock = _client({"mcp_qdrant": {"models": {"a": MODEL, "b": MODEL}}})
    await _ok(
        _server(mock), "qdrant_query", {"collection_name": "docs", "query_text": "x", "using": "b"}
    )
    assert mock.query_points.call_args.kwargs["using"] == "b"
