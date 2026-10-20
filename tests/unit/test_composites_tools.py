"""Unit tests for the composite `admin` tools (`qdrant_collection_copy`,
`qdrant_payload_schema_infer`): mocked client, no real network."""

from __future__ import annotations

import json
from collections.abc import Callable
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
    CollectionInfo,
    CollectionsAliasesResponse,
    FacetResponse,
    FacetValueHit,
    FieldCondition,
    Filter,
    IntegerIndexParams,
    IntegerIndexType,
    MatchValue,
    PayloadIndexInfo,
    PayloadSchemaType,
    QueryResponse,
    Record,
    SampleQuery,
    ScoredPoint,
    SparseVector,
    UpdateResult,
    UpdateStatus,
)

from mcp_qdrant.tools import composites as composites_tools
from mcp_qdrant.tools.composites import (
    CollectionCopyResult,
    PayloadSchemaProfile,
    _segment,
    _walk,
)
from mcp_qdrant.tools.registry import ToolRegistry


def _build(client: AsyncQdrantClient, *, read_only: bool = False) -> MCPServer[None]:
    server: MCPServer[None] = MCPServer(name="test-server")
    registry = ToolRegistry(server, enabled_toolsets=("admin",), read_only=read_only)
    composites_tools.register(registry, client)
    return server


def _qdrant_error(status: int, message: str) -> UnexpectedResponse:
    return UnexpectedResponse(
        status_code=status,
        reason_phrase="Error",
        content=json.dumps({"status": {"error": message}}).encode(),
        headers=httpx.Headers({}),
    )


def _record(point_id: int) -> Record:
    return Record(
        id=point_id,
        payload={"n": point_id},
        vector={"dense": [float(point_id), 0.0], "sparse": SparseVector(indices=[1], values=[1.0])},
    )


def _copy_mock(*pages: tuple[list[Record], int | None]) -> AsyncMock:
    mock = AsyncMock()
    mock.get_aliases.return_value = CollectionsAliasesResponse(aliases=[])
    mock.collection_exists.return_value = True
    mock.scroll.side_effect = list(pages)
    mock.upsert.return_value = UpdateResult(operation_id=1, status=UpdateStatus.COMPLETED)
    return mock


async def _copy(server: MCPServer[None], **args: Any) -> CollectionCopyResult:
    arguments = {"source_collection": "src", "target_collection": "dst", **args}
    result = await server.call_tool("qdrant_collection_copy", arguments)
    assert isinstance(result, CallToolResult)
    return CollectionCopyResult.model_validate(result.structured_content)


async def test_copy_single_page_preserves_every_vector_and_the_payload() -> None:
    mock = _copy_mock(([_record(1), _record(2)], None))
    server = _build(cast(AsyncQdrantClient, mock))

    result = await _copy(server)

    assert result == CollectionCopyResult(copied=2, next_offset=None, done=True)
    _, scroll_kwargs = mock.scroll.call_args
    assert scroll_kwargs["with_vectors"] is True
    assert scroll_kwargs["with_payload"] is True
    args, upsert_kwargs = mock.upsert.call_args
    assert args == ("dst",)
    first = upsert_kwargs["points"][0]
    assert first.id == 1
    assert first.payload == {"n": 1}
    assert first.vector["sparse"] == SparseVector(indices=[1], values=[1.0])
    assert first.vector["dense"] == [1.0, 0.0]


async def test_copy_follows_scroll_offsets_across_pages() -> None:
    mock = _copy_mock(([_record(1), _record(2)], 3), ([_record(3)], None))
    server = _build(cast(AsyncQdrantClient, mock))

    result = await _copy(server, batch_size=2)

    assert result == CollectionCopyResult(copied=3, next_offset=None, done=True)
    assert [c.kwargs["offset"] for c in mock.scroll.call_args_list] == [None, 3]
    assert mock.upsert.await_count == 2


async def test_copy_stops_at_max_points_and_reports_where_to_resume() -> None:
    mock = _copy_mock(([_record(1), _record(2)], 3), ([_record(3)], 4))
    server = _build(cast(AsyncQdrantClient, mock))

    result = await _copy(server, batch_size=2, max_points=3)

    assert result == CollectionCopyResult(copied=3, next_offset=4, done=False)
    # The last page is shrunk so a call never copies more than max_points.
    assert [c.kwargs["limit"] for c in mock.scroll.call_args_list] == [2, 1]


async def test_copy_starts_from_the_given_offset_and_forwards_the_filter() -> None:
    mock = _copy_mock(([_record(7)], None))
    server = _build(cast(AsyncQdrantClient, mock))

    await _copy(
        server,
        offset=7,
        copy_filter={"must": [{"key": "city", "match": {"value": "ny"}}]},
    )

    _, kwargs = mock.scroll.call_args
    assert kwargs["offset"] == 7
    assert kwargs["scroll_filter"] == Filter(
        must=[FieldCondition(key="city", match=MatchValue(value="ny"))]
    )


async def test_copy_of_an_empty_source_writes_nothing() -> None:
    mock = _copy_mock(([], None))
    server = _build(cast(AsyncQdrantClient, mock))

    result = await _copy(server)

    assert result == CollectionCopyResult(copied=0, next_offset=None, done=True)
    mock.upsert.assert_not_awaited()


async def test_copy_treats_an_empty_page_as_the_end_even_with_a_next_offset() -> None:
    mock = _copy_mock(([], 5))
    server = _build(cast(AsyncQdrantClient, mock))

    result = await _copy(server)

    assert result == CollectionCopyResult(copied=0, next_offset=None, done=True)
    assert mock.scroll.await_count == 1


async def test_copy_onto_the_same_name_is_refused_before_touching_anything() -> None:
    mock = _copy_mock()
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError, match="same collection"):
        await _copy(server, target_collection="src")
    mock.scroll.assert_not_awaited()
    mock.upsert.assert_not_awaited()


async def test_copy_between_an_alias_and_its_collection_is_refused() -> None:
    mock = _copy_mock()
    mock.get_aliases.return_value = CollectionsAliasesResponse(
        aliases=[AliasDescription(alias_name="live", collection_name="docs")]
    )
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError, match="same collection"):
        await _copy(server, source_collection="live", target_collection="docs")
    mock.upsert.assert_not_awaited()


async def test_copy_between_an_alias_and_a_different_collection_is_allowed() -> None:
    mock = _copy_mock(([_record(1)], None))
    mock.get_aliases.return_value = CollectionsAliasesResponse(
        aliases=[AliasDescription(alias_name="live", collection_name="docs_v1")]
    )
    server = _build(cast(AsyncQdrantClient, mock))

    result = await _copy(server, source_collection="live", target_collection="docs_v2")

    assert result.copied == 1


async def test_copy_requires_the_target_to_exist() -> None:
    mock = _copy_mock()
    mock.collection_exists.side_effect = lambda name: name != "dst"
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError, match="create it first"):
        await _copy(server)
    mock.scroll.assert_not_awaited()


async def test_copy_requires_the_source_to_exist_and_says_so_plainly() -> None:
    mock = _copy_mock()
    mock.collection_exists.side_effect = lambda name: name != "src"
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError) as excinfo:
        await _copy(server)

    assert "Source collection `src` doesn't exist" in str(excinfo.value)
    assert "Copy stopped" not in str(excinfo.value)  # not a mid-copy failure
    mock.scroll.assert_not_awaited()


async def test_copy_failure_on_the_first_batch_says_to_start_over_not_offset_none() -> None:
    mock = _copy_mock(([_record(1)], None))
    mock.upsert.side_effect = _qdrant_error(400, "Wrong input: Vector dimension error")
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError) as excinfo:
        await _copy(server)

    message = str(excinfo.value)
    assert "after 0 points; start over (no offset)" in message
    assert "None" not in message  # no Python repr leaking into a message for a model


async def test_copy_failure_quotes_a_string_offset_the_way_it_must_be_sent_back() -> None:
    mock = _copy_mock(([_record(1)], None))
    mock.upsert.side_effect = _qdrant_error(400, "boom")
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError, match=r'resume with offset="3f2b-uuid"'):
        await _copy(server, offset="3f2b-uuid")


async def test_copy_failure_reports_progress_and_the_offset_to_resume_from() -> None:
    mock = _copy_mock(([_record(1), _record(2)], 3), ([_record(3)], None))
    mock.upsert.side_effect = [
        UpdateResult(operation_id=1, status=UpdateStatus.COMPLETED),
        _qdrant_error(400, "Wrong input: Vector dimension error"),
    ]
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError) as excinfo:
        await _copy(server, batch_size=2)

    message = str(excinfo.value)
    assert "after 2 points" in message
    assert "offset=3" in message
    assert "Vector dimension error" in message


async def test_copy_of_a_missing_source_surfaces_qdrants_message() -> None:
    mock = _copy_mock()
    mock.scroll.side_effect = _qdrant_error(404, "Not found: Collection `src` doesn't exist!")
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError, match="doesn't exist"):
        await _copy(server)


@pytest.mark.parametrize(
    "args",
    [{"batch_size": 0}, {"batch_size": 251}, {"max_points": 0}, {"max_points": 100_001}],
)
async def test_copy_rejects_out_of_range_sizes(args: dict[str, int]) -> None:
    mock = _copy_mock()
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError):
        await _copy(server, **args)
    mock.scroll.assert_not_awaited()


async def test_read_only_mode_keeps_schema_inference_but_drops_copy() -> None:
    server = _build(cast(AsyncQdrantClient, AsyncMock()), read_only=True)

    assert {t.name for t in await server.list_tools()} == {"qdrant_payload_schema_infer"}


# --- payload key flattening -------------------------------------------------


def _flatten(payload: dict[str, Any]) -> dict[str, tuple[list[str], bool]]:
    seen: dict[str, tuple[set[str], bool]] = {}
    _walk(payload, "", seen)
    return {key: (sorted(types), is_array) for key, (types, is_array) in seen.items()}


def test_walk_scalar_types_distinguish_bool_from_int() -> None:
    assert _flatten({"a": 1, "b": 1.5, "c": "x", "d": True, "e": None}) == {
        "a": (["integer"], False),
        "b": (["float"], False),
        "c": (["string"], False),
        "d": (["boolean"], False),
        "e": (["null"], False),
    }


def test_walk_nested_objects_use_dotted_keys() -> None:
    assert _flatten({"meta": {"owner": "x", "deep": {"k": 1}}}) == {
        "meta.owner": (["string"], False),
        "meta.deep.k": (["integer"], False),
    }


def test_walk_array_of_scalars_keeps_the_bare_key_and_is_flagged_as_array() -> None:
    assert _flatten({"tags": ["a", "b"], "scores": [1, 2.5]}) == {
        "tags": (["string"], True),
        "scores": (["float", "integer"], True),
    }


def test_walk_array_of_objects_uses_the_bracket_syntax_filters_expect() -> None:
    assert _flatten({"items": [{"sku": "s1", "qty": 2}, {"sku": "s2", "tax": {"rate": 0.2}}]}) == {
        "items[].sku": (["string"], False),
        "items[].qty": (["integer"], False),
        "items[].tax.rate": (["float"], False),
    }


def test_walk_empty_and_nested_arrays_do_not_crash() -> None:
    assert _flatten({"empty": [], "grid": [[1, 2], [3]], "empty_obj": {}}) == {
        "empty": ([], True),
        "grid": (["array"], True),
    }


def test_walk_mixed_types_under_one_key_are_all_reported() -> None:
    seen: dict[str, tuple[set[str], bool]] = {}
    _walk({"v": 1}, "", seen)
    _walk({"v": "one"}, "", seen)
    assert sorted(seen["v"][0]) == ["integer", "string"]


# --- the schema inference tool ----------------------------------------------


def _sample(*payloads: dict[str, Any] | None) -> QueryResponse:
    return QueryResponse(
        points=[
            ScoredPoint(id=i, version=0, score=1.0, payload=payload)
            for i, payload in enumerate(payloads, start=1)
        ]
    )


def _infer_mock(
    make_collection_info: Callable[..., CollectionInfo],
    sample: QueryResponse,
    *,
    schema: dict[str, PayloadSchemaType] | None = None,
    points_count: int = 10,
) -> AsyncMock:
    info = make_collection_info(points_count=points_count)
    info.payload_schema = {
        key: PayloadIndexInfo(data_type=data_type, points=points_count)
        for key, data_type in (schema or {}).items()
    }
    mock = AsyncMock()
    mock.get_collection.return_value = info
    mock.query_points.return_value = sample
    mock.facet.return_value = FacetResponse(
        hits=[FacetValueHit(value="ny", count=6), FacetValueHit(value="sf", count=4)]
    )
    return mock


async def _infer(server: MCPServer[None], **args: Any) -> PayloadSchemaProfile:
    result = await server.call_tool(
        "qdrant_payload_schema_infer", {"collection_name": "docs", **args}
    )
    assert isinstance(result, CallToolResult)
    return PayloadSchemaProfile.model_validate(result.structured_content)


async def test_schema_infer_reports_types_presence_and_index_per_key(
    make_collection_info: Callable[..., CollectionInfo],
) -> None:
    mock = _infer_mock(
        make_collection_info,
        _sample(
            {"city": "ny", "price": 1.5, "tags": ["a"]},
            {"city": "sf", "price": 2.5},
            {"city": "ny"},
        ),
        schema={"city": PayloadSchemaType.KEYWORD, "price": PayloadSchemaType.FLOAT},
    )
    server = _build(cast(AsyncQdrantClient, mock))

    profile = await _infer(server)

    assert profile.sampled == 3
    assert profile.collection_points == 10
    assert [f.key for f in profile.fields] == ["city", "price", "tags"]  # most common first
    city, price, tags = profile.fields
    assert (city.types, city.present_in, city.indexed, city.index_type) == (
        ["string"],
        3,
        True,
        "keyword",
    )
    assert (price.types, price.present_in, price.index_type) == (["float"], 2, "float")
    assert (tags.is_array, tags.indexed, tags.index_type) == (True, False, None)


async def test_schema_infer_adds_top_values_only_for_facetable_index_types(
    make_collection_info: Callable[..., CollectionInfo],
) -> None:
    mock = _infer_mock(
        make_collection_info,
        _sample({"city": "ny", "price": 1.5, "note": "x"}),
        schema={"city": PayloadSchemaType.KEYWORD, "price": PayloadSchemaType.FLOAT},
    )
    server = _build(cast(AsyncQdrantClient, mock))

    profile = await _infer(server, top_values=2)

    by_key = {f.key: f for f in profile.fields}
    assert by_key["city"].top_values is not None
    assert [(v.value, v.count) for v in by_key["city"].top_values] == [("ny", 6), ("sf", 4)]
    assert by_key["price"].top_values is None  # float index: Qdrant can't facet on it
    assert by_key["note"].top_values is None  # not indexed
    mock.facet.assert_awaited_once_with("docs", key="city", limit=2)


async def test_schema_infer_top_values_zero_skips_every_facet_call(
    make_collection_info: Callable[..., CollectionInfo],
) -> None:
    mock = _infer_mock(
        make_collection_info,
        _sample({"city": "ny"}),
        schema={"city": PayloadSchemaType.KEYWORD},
    )
    server = _build(cast(AsyncQdrantClient, mock))

    profile = await _infer(server, top_values=0)

    assert profile.fields[0].top_values is None
    mock.facet.assert_not_awaited()


async def test_schema_infer_lists_indexed_keys_no_sampled_point_has(
    make_collection_info: Callable[..., CollectionInfo],
) -> None:
    mock = _infer_mock(
        make_collection_info,
        _sample({"city": "ny"}),
        schema={"city": PayloadSchemaType.KEYWORD, "legacy": PayloadSchemaType.INTEGER},
    )
    server = _build(cast(AsyncQdrantClient, mock))

    profile = await _infer(server)

    assert profile.indexed_but_unseen == ["legacy"]


async def test_schema_infer_truncates_to_max_fields_keeping_the_most_common(
    make_collection_info: Callable[..., CollectionInfo],
) -> None:
    mock = _infer_mock(
        make_collection_info,
        _sample({"a": 1, "b": 1, "c": 1}, {"a": 1, "b": 1}, {"a": 1}),
    )
    server = _build(cast(AsyncQdrantClient, mock))

    profile = await _infer(server, max_fields=2)

    assert [f.key for f in profile.fields] == ["a", "b"]
    assert profile.fields_truncated is True


async def test_schema_infer_samples_randomly_and_forwards_size_and_filter(
    make_collection_info: Callable[..., CollectionInfo],
) -> None:
    mock = _infer_mock(make_collection_info, _sample({"city": "ny"}))
    server = _build(cast(AsyncQdrantClient, mock))

    await _infer(
        server,
        sample_size=50,
        sample_filter={"must": [{"key": "city", "match": {"value": "ny"}}]},
    )

    _, kwargs = mock.query_points.call_args
    assert isinstance(kwargs["query"], SampleQuery)
    assert kwargs["limit"] == 50
    assert kwargs["with_payload"] is True
    assert kwargs["with_vectors"] is False
    assert kwargs["query_filter"] == Filter(
        must=[FieldCondition(key="city", match=MatchValue(value="ny"))]
    )


async def test_schema_infer_handles_points_without_payload_and_an_empty_sample(
    make_collection_info: Callable[..., CollectionInfo],
) -> None:
    mock = _infer_mock(make_collection_info, _sample(None, {}), points_count=2)
    server = _build(cast(AsyncQdrantClient, mock))

    profile = await _infer(server)

    assert profile.sampled == 2
    assert profile.fields == []

    mock.query_points.return_value = QueryResponse(points=[])
    assert (await _infer(server)).sampled == 0


async def test_schema_infer_missing_collection_raises(
    make_collection_info: Callable[..., CollectionInfo],
) -> None:
    mock = _infer_mock(make_collection_info, _sample())
    mock.get_collection.side_effect = _qdrant_error(
        404, "Not found: Collection `docs` doesn't exist!"
    )
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError, match="doesn't exist"):
        await _infer(server)


@pytest.mark.parametrize(
    "args",
    [
        {"sample_size": 0},
        {"sample_size": 1001},
        {"top_values": -1},
        {"top_values": 51},
        {"max_fields": 0},
    ],
)
async def test_schema_infer_rejects_out_of_range_arguments(
    args: dict[str, int], make_collection_info: Callable[..., CollectionInfo]
) -> None:
    mock = _infer_mock(make_collection_info, _sample())
    server = _build(cast(AsyncQdrantClient, mock))

    with pytest.raises(ToolError):
        await _infer(server, **args)
    mock.get_collection.assert_not_awaited()


# --- keys Qdrant can parse ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("city", "city"),
        ("x-y_z", "x-y_z"),
        ("über", "über"),
        ("1abc", "1abc"),
        ("my key", '"my key"'),
        ("user@email", '"user@email"'),
        ("a/b", '"a/b"'),
        ("a:b", '"a:b"'),
        ("a+b", '"a+b"'),
        ("a.b", '"a.b"'),  # a literal dot in a key, not a nested path
        ("k[]", '"k[]"'),  # a literal key, not an array path
        ("🔥", '"🔥"'),
        ("", '""'),
    ],
)
def test_segment_quotes_exactly_what_qdrants_filter_syntax_needs_quoted(
    name: str, expected: str
) -> None:
    assert _segment(name) == expected


def test_walk_emits_quoted_segments_inside_nested_and_array_paths() -> None:
    assert _flatten(
        {"my key": 1, "a.b": 2, "meta": {"first name": "x"}, "items": [{"unit price": 3}]}
    ) == {
        '"my key"': (["integer"], False),
        '"a.b"': (["integer"], False),
        'meta."first name"': (["string"], False),
        'items[]."unit price"': (["integer"], False),
    }


def test_a_literal_dotted_key_and_a_nested_path_do_not_collapse_into_one_entry() -> None:
    flattened = _flatten({"a.b": 1, "a": {"b": 2}})

    assert set(flattened) == {'"a.b"', "a.b"}


# --- facet only where Qdrant can facet ----------------------------------------------------


async def test_schema_infer_skips_facet_for_a_range_only_integer_index_instead_of_aborting(
    make_collection_info: Callable[..., CollectionInfo],
) -> None:
    mock = _infer_mock(
        make_collection_info,
        _sample({"n": 1, "city": "ny"}),
        schema={"city": PayloadSchemaType.KEYWORD},
    )
    mock.get_collection.return_value.payload_schema["n"] = PayloadIndexInfo(
        data_type=PayloadSchemaType.INTEGER,
        params=IntegerIndexParams(type=IntegerIndexType.INTEGER, lookup=False, range=True),
        points=10,
    )
    server = _build(cast(AsyncQdrantClient, mock))

    profile = await _infer(server, top_values=3)

    by_key = {f.key: f for f in profile.fields}
    assert by_key["n"].indexed is True and by_key["n"].top_values is None
    assert by_key["city"].top_values is not None  # the facetable one still gets its values
    mock.facet.assert_awaited_once_with("docs", key="city", limit=3)


async def test_schema_infer_still_facets_an_integer_index_with_lookup_on_or_unspecified(
    make_collection_info: Callable[..., CollectionInfo],
) -> None:
    mock = _infer_mock(make_collection_info, _sample({"a": 1, "b": 2}), schema={})
    mock.get_collection.return_value.payload_schema["a"] = PayloadIndexInfo(
        data_type=PayloadSchemaType.INTEGER,
        params=IntegerIndexParams(type=IntegerIndexType.INTEGER, lookup=True, range=False),
        points=10,
    )
    mock.get_collection.return_value.payload_schema["b"] = PayloadIndexInfo(
        data_type=PayloadSchemaType.INTEGER, points=10
    )
    server = _build(cast(AsyncQdrantClient, mock))

    await _infer(server, top_values=3)

    assert {c.kwargs["key"] for c in mock.facet.await_args_list} == {"a", "b"}


async def test_schema_infer_matches_a_quoted_key_to_the_index_qdrant_reports_for_it(
    make_collection_info: Callable[..., CollectionInfo],
) -> None:
    mock = _infer_mock(
        make_collection_info,
        _sample({"my key": 1}),
        schema={'"my key"': PayloadSchemaType.INTEGER},
    )
    server = _build(cast(AsyncQdrantClient, mock))

    profile = await _infer(server, top_values=0)

    (field,) = profile.fields
    assert field.key == '"my key"' and field.indexed is True
    assert profile.indexed_but_unseen == []
