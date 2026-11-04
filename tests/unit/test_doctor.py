"""Unit tests for `qdrant_collection_doctor`: mocked client returning real CollectionInfo objects,
one test per rule branch, called through the MCP server like a client would."""

from __future__ import annotations

import json
from typing import Any, cast
from unittest.mock import AsyncMock

import httpx
import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import (
    AliasDescription,
    CollectionConfig,
    CollectionInfo,
    CollectionParams,
    CollectionsAliasesResponse,
    CollectionStatus,
    Datatype,
    Distance,
    HnswConfig,
    KeywordIndexParams,
    KeywordIndexType,
    Memory,
    MultiVectorComparator,
    MultiVectorConfig,
    OptimizersConfig,
    OptimizersStatusOneOf,
    OptimizersStatusOneOf1,
    PayloadIndexInfo,
    PayloadSchemaType,
    ScalarQuantization,
    ScalarQuantizationConfig,
    ScalarType,
    TextIndexParams,
    TextIndexType,
    TextScoringParams,
    TextScoringType,
    VectorParams,
)

from mcp_qdrant.tools import doctor as doctor_tools
from mcp_qdrant.tools.doctor import ALIAS_PLACEHOLDER, MEMORY_HINT_BYTES, DoctorReport
from mcp_qdrant.tools.registry import ToolRegistry

NAME = "docs"
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
ALL_RULES = ["status", "unindexed", "memory", "aliases"]
INT8 = ScalarQuantization(scalar=ScalarQuantizationConfig(type=ScalarType.INT8))
# 1 GiB of float32 at 256 dimensions (1 KiB per vector).
BIG = 1 << 20


def _vec(size: int = 4, **kwargs: Any) -> VectorParams:
    return VectorParams(size=size, distance=Distance.COSINE, **kwargs)


def _info(
    *,
    status: CollectionStatus = CollectionStatus.GREEN,
    optimizer_status: OptimizersStatusOneOf | OptimizersStatusOneOf1 = OptimizersStatusOneOf.OK,
    points: int = 10,
    indexed: int = 10,
    vectors: Any = None,
    replication_factor: int | None = None,
    quantization: ScalarQuantization | None = None,
    indexing_threshold: int = 10000,
    metadata: dict[str, Any] | None = None,
    payload_schema: dict[str, PayloadIndexInfo] | None = None,
) -> CollectionInfo:
    return CollectionInfo(
        status=status,
        optimizer_status=optimizer_status,
        segments_count=1,
        points_count=points,
        indexed_vectors_count=indexed,
        config=CollectionConfig(
            params=CollectionParams(
                vectors=_vec() if vectors is None else vectors,
                replication_factor=replication_factor,
            ),
            hnsw_config=HnswConfig(m=16, ef_construct=100, full_scan_threshold=10000),
            optimizer_config=OptimizersConfig(
                default_segment_number=0,
                flush_interval_sec=5,
                indexing_threshold=indexing_threshold,
            ),
            quantization_config=quantization,
            metadata=metadata,
        ),
        payload_schema=payload_schema or {},
    )


def _client(info: CollectionInfo, aliases: list[AliasDescription] | None = None) -> AsyncMock:
    mock = AsyncMock()
    mock.get_collection.return_value = info
    mock.get_aliases.return_value = CollectionsAliasesResponse(
        aliases=[AliasDescription(alias_name="docs-live", collection_name=NAME)]
        if aliases is None
        else aliases
    )
    return mock


def _server(mock: AsyncMock, *, read_only: bool = False) -> MCPServer[None]:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("admin",), read_only=read_only)
    doctor_tools.register(registry, cast(AsyncQdrantClient, mock))
    return server


async def _report(
    info: CollectionInfo, aliases: list[AliasDescription] | None = None, name: str = NAME
) -> DoctorReport:
    result = await _server(_client(info, aliases)).call_tool(
        "qdrant_collection_doctor", {"collection_name": name}
    )
    assert isinstance(result, CallToolResult) and not result.is_error, result
    return DoctorReport.model_validate(result.structured_content)


def _rules(report: DoctorReport) -> list[str]:
    return [finding.rule for finding in report.findings]


async def test_clean_collection_reports_nothing_but_lists_what_it_checked() -> None:
    report = await _report(_info())

    assert report.findings == []
    assert report.checked == ALL_RULES
    assert (report.collection, report.status, report.points_count) == (NAME, "green", 10)


async def test_read_only_mode_keeps_the_doctor() -> None:
    tools = await _server(AsyncMock(), read_only=True).list_tools()

    assert [tool.name for tool in tools] == ["qdrant_collection_doctor"]
    assert tools[0].annotations is not None and tools[0].annotations.read_only_hint is True


async def test_missing_collection_is_qdrants_own_error() -> None:
    mock = _client(_info())
    mock.get_collection.side_effect = UnexpectedResponse(
        status_code=404,
        reason_phrase="Not Found",
        content=json.dumps({"status": {"error": "Collection `nope` doesn't exist!"}}).encode(),
        headers=httpx.Headers({}),
    )

    with pytest.raises(ToolError, match="Collection `nope` doesn't exist!"):
        await _server(mock).call_tool("qdrant_collection_doctor", {"collection_name": "nope"})


# --- status ------------------------------------------------------------------------------


async def test_yellow_points_to_optimizer_progress() -> None:
    [finding] = (await _report(_info(status=CollectionStatus.YELLOW))).findings

    assert (finding.rule, finding.severity) == ("status", "info")
    assert finding.evidence == {"status": "yellow", "optimizer_status": "ok"}
    assert finding.fix is not None
    assert finding.fix.tool == "qdrant_collection_optimizations"
    assert finding.fix.arguments == {"collection_name": NAME}


async def test_grey_fix_is_an_empty_optimizers_update() -> None:
    [finding] = (await _report(_info(status=CollectionStatus.GREY))).findings

    assert (finding.rule, finding.severity) == ("status", "warning")
    assert finding.fix is not None
    assert finding.fix.tool == "qdrant_collection_update"
    assert finding.fix.arguments == {"collection_name": NAME, "optimizers_config": {}}


async def test_red_carries_the_optimizer_error() -> None:
    info = _info(
        status=CollectionStatus.RED,
        optimizer_status=OptimizersStatusOneOf1(error="No space left on device"),
    )
    [finding] = (await _report(info)).findings

    assert (finding.rule, finding.severity) == ("status", "error")
    assert finding.evidence["optimizer_status"] == {"error": "No space left on device"}
    assert "No space left on device" in finding.finding
    assert finding.fix is not None and finding.fix.tool == "qdrant_collection_optimizations"


# --- unindexed ---------------------------------------------------------------------------


async def test_points_without_a_vector_index_are_flagged_with_the_threshold() -> None:
    [finding] = (await _report(_info(points=500, indexed=0))).findings

    assert (finding.rule, finding.severity, finding.fix) == ("unindexed", "info", None)
    assert finding.evidence == {
        "points_count": 500,
        "indexed_vectors_count": 0,
        "indexing_threshold": 10000,
    }
    assert "10000 KB" in finding.finding


async def test_indexing_threshold_zero_is_reported_as_disabled() -> None:
    [finding] = (await _report(_info(points=500, indexed=0, indexing_threshold=0))).findings

    assert "disabled" in finding.finding


@pytest.mark.parametrize(
    ("points", "indexed", "vectors"),
    [
        (500, 500, None),  # indexed
        (0, 0, None),  # empty collection
        (500, 0, {}),  # no dense vector (sparse only): HNSW doesn't apply
    ],
)
async def test_unindexed_stays_silent(points: int, indexed: int, vectors: Any) -> None:
    report = await _report(_info(points=points, indexed=indexed, vectors=vectors))

    assert "unindexed" not in _rules(report)


# --- memory ------------------------------------------------------------------------------


async def test_large_unquantized_dense_vectors_get_the_int8_hint() -> None:
    info = _info(points=BIG, indexed=BIG, vectors={"dense": _vec(256), "small": _vec(4)})
    [finding] = (await _report(info)).findings

    assert (finding.rule, finding.severity) == ("memory", "info")
    assert finding.evidence["bytes_by_vector"] == {"dense": 1 << 30, "small": BIG * 16}
    assert finding.evidence["total_bytes"] == (1 << 30) + BIG * 16
    assert "qdrant_search_quality_eval" in finding.finding
    assert finding.fix is not None
    assert finding.fix.tool == "qdrant_collection_update"
    # Per vector, never collection-wide: that would also quantize the vectors left out.
    pinned_int8 = {"scalar": {"type": "int8", "memory": "pinned"}}
    assert finding.fix.arguments == {
        "collection_name": NAME,
        "vectors_config": {
            "dense": {"memory": "cold", "quantization_config": pinned_int8},
            "small": {"memory": "cold", "quantization_config": pinned_int8},
        },
    }


async def test_the_memory_fix_leaves_out_the_vectors_the_rule_left_out() -> None:
    multi = MultiVectorConfig(comparator=MultiVectorComparator.MAX_SIM)
    vectors = {
        "big": _vec(256),
        "cold": _vec(256, memory=Memory.COLD),
        "multi": _vec(256, multivector_config=multi),
    }
    [finding] = (await _report(_info(points=BIG, indexed=BIG, vectors=vectors))).findings

    assert finding.fix is not None
    assert set(finding.fix.arguments["vectors_config"]) == {"big"}
    assert "quantization_config" not in finding.fix.arguments


async def test_memory_counts_one_copy_of_the_data_and_the_datatype() -> None:
    # 256 dims x 2 bytes (float16) = half the threshold per copy; a replication factor of 2
    # doesn't double it — on a single node that second replica doesn't even exist (20b review).
    info = _info(
        points=2 * BIG,
        indexed=BIG,
        vectors=_vec(256, datatype=Datatype.FLOAT16),
        replication_factor=2,
    )
    [finding] = (await _report(info)).findings

    assert finding.evidence["bytes_by_vector"] == {"": MEMORY_HINT_BYTES}
    assert finding.evidence["replication_factor"] == 2


async def test_memory_ignores_the_replication_factor() -> None:
    info = _info(points=BIG, indexed=BIG, vectors=_vec(128), replication_factor=2)

    assert "memory" not in _rules(await _report(info))


async def test_memory_under_the_threshold_stays_silent() -> None:
    info = _info(points=BIG - 1, indexed=BIG, vectors=_vec(256))

    assert (await _report(info)).findings == []


@pytest.mark.parametrize(
    "vector",
    [
        _vec(256, memory=Memory.COLD),
        _vec(256, on_disk=True),
        _vec(256, quantization_config=INT8),
        _vec(256, multivector_config=MultiVectorConfig(comparator=MultiVectorComparator.MAX_SIM)),
        # 1 byte per dimension or less: an int8 copy saves nothing (turbo4 would double).
        _vec(1024, datatype=Datatype.UINT8),
        _vec(2048, datatype=Datatype.TURBO4),
    ],
    ids=["cold", "on_disk", "quantized", "multivector", "uint8", "turbo4"],
)
async def test_memory_skips_vectors_that_are_not_big_float_in_ram(vector: VectorParams) -> None:
    info = _info(points=BIG, indexed=BIG, vectors={"v": vector})

    assert "memory" not in _rules(await _report(info))


async def test_memory_skips_a_collection_quantized_as_a_whole() -> None:
    info = _info(points=BIG, indexed=BIG, vectors=_vec(256), quantization=INT8)

    assert "memory" not in _rules(await _report(info))


async def test_memory_tier_overrides_the_deprecated_on_disk_flag() -> None:
    info = _info(points=BIG, indexed=BIG, vectors=_vec(256, on_disk=True, memory=Memory.CACHED))

    assert _rules(await _report(info)) == ["memory"]


# --- aliases -----------------------------------------------------------------------------


async def test_no_alias_suggests_creating_one_with_a_placeholder_name() -> None:
    report = await _report(
        _info(), aliases=[AliasDescription(alias_name="other", collection_name="elsewhere")]
    )
    [finding] = report.findings

    assert (finding.rule, finding.severity) == ("aliases", "info")
    assert ALIAS_PLACEHOLDER in finding.finding
    assert finding.fix is not None
    assert finding.fix.tool == "qdrant_alias_update"
    assert finding.fix.arguments == {
        "operations": [{"create_alias": {"collection_name": NAME, "alias_name": ALIAS_PLACEHOLDER}}]
    }


async def test_diagnosing_through_an_alias_does_not_claim_there_is_none() -> None:
    report = await _report(_info(), name="docs-live")

    assert "aliases" not in _rules(report)


# --- text_contract -----------------------------------------------------------------------


def _bm25_index() -> PayloadIndexInfo:
    # How Qdrant reports an index created with `scoring: true`.
    scoring = TextScoringParams(type=TextScoringType.BM25)
    return PayloadIndexInfo(
        data_type=PayloadSchemaType.TEXT,
        params=TextIndexParams(type=TextIndexType.TEXT, scoring=scoring),
        points=0,
    )


def _contract(models: dict[str, str]) -> dict[str, Any]:
    return {"mcp_qdrant": {"text_field": "body", "models": models}}


async def test_a_sound_text_contract_is_checked_and_clean() -> None:
    info = _info(
        vectors={"dense": _vec(384)},
        metadata=_contract({"dense": MODEL}),
        payload_schema={"body": _bm25_index()},
    )
    report = await _report(info)

    assert report.findings == []
    assert report.checked == [*ALL_RULES, "text_contract"]


@pytest.mark.parametrize("vector", ["gone", "colbert"])
async def test_a_model_declared_on_no_single_dense_vector_is_an_error(vector: str) -> None:
    colbert = _vec(
        384, multivector_config=MultiVectorConfig(comparator=MultiVectorComparator.MAX_SIM)
    )
    info = _info(
        vectors={"dense": _vec(384), "colbert": colbert},
        metadata=_contract({"dense": MODEL, vector: MODEL}),
        payload_schema={"body": _bm25_index()},
    )
    [finding] = (await _report(info)).findings

    assert (finding.rule, finding.severity) == ("text_contract", "error")
    assert finding.evidence["vector"] == vector
    assert finding.fix is not None
    assert finding.fix.tool == "qdrant_collection_update"
    assert finding.fix.arguments == {"collection_name": NAME, "text_models": {vector: None}}


@pytest.mark.parametrize(
    ("schema", "index_type"),
    [
        ({}, None),
        (
            {"body": PayloadIndexInfo(data_type=PayloadSchemaType.TEXT, params=None, points=0)},
            "text",
        ),
        (
            {
                "body": PayloadIndexInfo(
                    data_type=PayloadSchemaType.TEXT,
                    params=TextIndexParams(type=TextIndexType.TEXT),
                    points=0,
                )
            },
            "text",
        ),
        (
            {
                "body": PayloadIndexInfo(
                    data_type=PayloadSchemaType.KEYWORD,
                    params=KeywordIndexParams(type=KeywordIndexType.KEYWORD),
                    points=0,
                )
            },
            "keyword",
        ),
    ],
    ids=["no-index", "plain-text", "text-without-scoring", "keyword"],
)
async def test_a_text_field_without_bm25_suggests_the_index(
    schema: dict[str, PayloadIndexInfo], index_type: str | None
) -> None:
    info = _info(vectors={"": _vec(384)}, metadata=_contract({}), payload_schema=schema)
    [finding] = (await _report(info)).findings

    assert (finding.rule, finding.severity) == ("text_contract", "info")
    assert finding.evidence == {"text_field": "body", "index_type": index_type}
    assert ("replaces the current" in finding.finding) == (index_type is not None)
    assert finding.fix is not None
    assert finding.fix.tool == "qdrant_payload_index_create"
    assert finding.fix.arguments == {
        "collection_name": NAME,
        "field_name": "body",
        "field_schema": {
            "type": "text",
            "tokenizer": "multilingual",
            "lowercase": True,
            "ascii_folding": True,
            "scoring": True,
        },
    }


async def test_malformed_text_metadata_is_a_finding_not_a_failure() -> None:
    info = _info(metadata={"mcp_qdrant": {"models": "not-a-dict"}})
    report = await _report(info)
    [finding] = report.findings

    assert (finding.rule, finding.severity, finding.fix) == ("text_contract", "error", None)
    assert "malformed" in finding.finding
    assert finding.evidence == {"mcp_qdrant": {"models": "not-a-dict"}}
    assert report.checked == [*ALL_RULES, "text_contract"]


async def test_no_text_contract_is_not_checked() -> None:
    report = await _report(_info(metadata={"owner": "team-a"}))

    assert report.checked == ALL_RULES


async def test_an_explicit_null_contract_is_checked_and_reports_nothing() -> None:
    report = await _report(_info(metadata={"mcp_qdrant": None}))

    assert "text_contract" in report.checked
    assert "text_contract" not in _rules(report)
