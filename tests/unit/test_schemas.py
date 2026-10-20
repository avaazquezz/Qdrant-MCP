"""The compact input schemas (`mcp_qdrant.tools.schemas`) must stay honest:
they advertise less than Qdrant's own models, never something different.

Three guarantees are tested here, plus the size budget that makes the whole
exercise stick:
- what a client sees accepts and rejects the same samples as the real model;
- the hand-written grammar can't silently drift from the installed `qdrant-client`;
- every `$ref` in every advertised tool schema resolves.
"""

from __future__ import annotations

import json
import typing
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from qdrant_client.http import models as qm

from mcp_qdrant.config import ALL_TOOLSETS, Settings
from mcp_qdrant.server import build_server
from mcp_qdrant.tools.payload import PayloadIndexSchema
from mcp_qdrant.tools.schemas import (
    BATCH_OPERATION_NAMES,
    BATCH_OPERATIONS_DESCRIPTION,
    FILTER_DESCRIPTION,
    CollectionParamsDiffInput,
    FilterInput,
    HnswConfigDiffInput,
    OptimizersConfigDiffInput,
    QuantizationConfigInput,
    SearchParamsInput,
    SparseVectorParamsMapInput,
    StrictModeConfigInput,
    VectorParamsDiffMapInput,
    VectorParamsMapInput,
    slim_schema,
)
from mcp_qdrant.tools.vectors import BatchOperation

# --- slim_schema -------------------------------------------------------------------


class _Inner(BaseModel):
    """Inner model docstring."""

    size: int = Field(description="how big")


class _Outer(BaseModel):
    """Outer model docstring."""

    # Fields that happen to be called like schema keywords must survive.
    title: str | None = None
    description: str | None = Field(None, description="the description field")
    inner: _Inner | None = None
    sizes: dict[str, _Inner] | None = None


class _Node(BaseModel):
    children: list[_Node] = []


def _prose(node: Any, in_fields: bool = False) -> list[str]:
    """Every `title`/`description` string that sits on a schema node."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if not in_fields and key in ("title", "description") and isinstance(value, str):
                found.append(value)
            found += _prose(value, in_fields=not in_fields and key in ("properties", "$defs"))
    elif isinstance(node, list):
        for item in node:
            found += _prose(item)
    return found


def test_slim_schema_inlines_refs_and_removes_all_prose() -> None:
    schema = slim_schema(_Outer)

    assert "$defs" not in schema and "$ref" not in json.dumps(schema)
    assert _prose(schema) == []
    assert schema["properties"]["inner"]["anyOf"][0]["properties"]["size"] == {"type": "integer"}


def test_slim_schema_keeps_fields_named_like_schema_keywords() -> None:
    assert set(slim_schema(_Outer)["properties"]) == {"title", "description", "inner", "sizes"}


def test_slim_schema_drops_null_defaults_but_keeps_real_ones_and_constraints() -> None:
    class Model(BaseModel):
        a: int | None = None
        b: int = Field(5, ge=1)

    props = slim_schema(Model)["properties"]
    assert "default" not in props["a"]
    assert props["b"]["default"] == 5 and props["b"]["minimum"] == 1


def test_slim_schema_survives_a_recursive_model_instead_of_looping() -> None:
    schema = slim_schema(_Node)  # must terminate

    # The model refers to itself: the first reference is cut to a bare object.
    assert schema["properties"]["children"]["items"] == {"type": "object"}


def test_slim_schema_works_on_unions_and_mappings() -> None:
    assert slim_schema(dict[str, _Inner])["additionalProperties"]["properties"]["size"] == {
        "type": "integer"
    }
    assert len(slim_schema(_Inner | _Node)["anyOf"]) == 2


# --- what the client sees accepts/rejects like the real model ------------------------


def _advertised(annotated: Any) -> Draft202012Validator:
    return Draft202012Validator(TypeAdapter(annotated).json_schema())


FILTER_OK: list[dict[str, Any]] = [
    {},
    {"must": [{"key": "city", "match": {"value": "ny"}}]},
    {"must": {"key": "city", "match": {"value": "ny"}}},  # a single condition, not a list
    {
        "should": [{"key": "price", "range": {"gte": 1, "lt": 5}}],
        "must_not": [{"is_null": {"key": "x"}}],
    },
    {"min_should": {"conditions": [{"key": "a", "match": {"value": 1}}], "min_count": 1}},
    {
        "must": [
            {
                "nested": {
                    "key": "items",
                    "filter": {"must": [{"key": "sku", "match": {"value": "s"}}]},
                }
            },
            {"has_id": [1, 2]},
            {"key": "tags", "match": {"any": ["a", "b"]}},
            {"must_not": [{"key": "city", "match": {"value": "x"}}]},  # a nested filter
        ]
    },
]
# Explicit nulls for unset optional fields: what Qdrant's own clients send, and what the real
# model accepts. The compact schema must not forbid them (found by an independent review).
FILTER_OK += [
    {"must": None},
    {"should": None, "must_not": None, "min_should": None},
    {"must": [{"key": "a", "match": {"value": 1}}], "should": None},
]
FILTER_BAD: list[Any] = [{"bogus": []}, {"must": "x"}, {"min_should": {"conditions": []}}, [], "x"]


@pytest.mark.parametrize("sample", FILTER_OK)
def test_filter_schema_accepts_what_qdrants_filter_accepts(sample: dict[str, Any]) -> None:
    assert _advertised(FilterInput).is_valid(sample)
    assert isinstance(TypeAdapter(FilterInput).validate_python(sample), qm.Filter)


@pytest.mark.parametrize("sample", FILTER_BAD)
def test_filter_schema_rejects_what_qdrants_filter_rejects(sample: Any) -> None:
    assert not _advertised(FilterInput).is_valid(sample)
    with pytest.raises(ValidationError):
        TypeAdapter(FilterInput).validate_python(sample)


SEARCH_PARAMS_OK: list[dict[str, Any]] = [
    {},
    {"exact": True},
    {
        "hnsw_ef": 64,
        "indexed_only": False,
        "quantization": {"ignore": True, "rescore": True, "oversampling": 2.0},
        "acorn": {"enable": True, "max_selectivity": 0.4},
    },
]


SEARCH_PARAMS_OK += [
    {"hnsw_ef": None},
    {"quantization": None},
    {"quantization": {"ignore": None, "rescore": None, "oversampling": None}},
    {"acorn": None},
    {"acorn": {"enable": None, "max_selectivity": None}},
    {"idf": None},
    {"idf": "global"},  # IdfScope
    {"idf": {"corpus": {"must": [{"key": "lang", "match": {"value": "en"}}]}}},  # IdfCorpusParams
]


@pytest.mark.parametrize("sample", SEARCH_PARAMS_OK)
def test_search_params_schema_accepts_what_qdrant_accepts(sample: dict[str, Any]) -> None:
    assert _advertised(SearchParamsInput).is_valid(sample)
    TypeAdapter(SearchParamsInput).validate_python(sample)


@pytest.mark.parametrize(
    "sample",
    [
        {"hnsw_ef": "wide"},
        {"bogus": 1},
        {"exact": "yes please"},
        {"idf": "local"},  # IdfScope only has `global`
        {"quantization": {"bogus": True}},
    ],
)
def test_search_params_schema_rejects_what_qdrant_rejects(sample: dict[str, Any]) -> None:
    assert not _advertised(SearchParamsInput).is_valid(sample)
    with pytest.raises(ValidationError):
        TypeAdapter(SearchParamsInput).validate_python(sample)


# One valid operation per kind, in the shapes Qdrant documents.
BATCH_OK: list[dict[str, Any]] = [
    {"upsert": {"points": [{"id": 1, "vector": [0.1, 0.2], "payload": {"a": 1}}]}},
    {"upsert": {"batch": {"ids": [1], "vectors": [[0.1, 0.2]]}}},
    {"delete": {"points": [1, 2]}},
    {"delete": {"filter": {"must": [{"key": "a", "match": {"value": 1}}]}}},
    {"set_payload": {"payload": {"a": 1}, "points": [1]}},
    {"overwrite_payload": {"payload": {"a": 1}, "points": [1]}},
    {"delete_payload": {"keys": ["a"], "points": [1]}},
    {"clear_payload": {"points": [1]}},
    {"update_vectors": {"points": [{"id": 1, "vector": [0.1, 0.2]}]}},
    {"delete_vectors": {"points": [1], "vector": ["dense"]}},
]


def _batch_validator() -> Draft202012Validator:
    from mcp_qdrant.tools.schemas import BatchOperationsSchema

    schema = TypeAdapter(
        typing.Annotated[list[BatchOperation], BatchOperationsSchema]
    ).json_schema()
    return Draft202012Validator(schema)


@pytest.mark.parametrize("operation", BATCH_OK)
def test_batch_operations_schema_accepts_every_documented_operation(
    operation: dict[str, Any],
) -> None:
    assert _batch_validator().is_valid([operation])
    TypeAdapter(list[BatchOperation]).validate_python([operation])


@pytest.mark.parametrize(
    "operations",
    [[], [{"unknown_op": {}}], [{"upsert": {}, "delete": {}}], [{}], "upsert"],
)
def test_batch_operations_schema_rejects_malformed_lists(operations: Any) -> None:
    assert not _batch_validator().is_valid(operations)


def test_batch_operation_names_match_the_installed_models() -> None:
    models: list[type[BaseModel]] = [
        qm.UpsertOperation,
        qm.DeleteOperation,
        qm.SetPayloadOperation,
        qm.OverwritePayloadOperation,
        qm.DeletePayloadOperation,
        qm.ClearPayloadOperation,
        qm.UpdateVectorsOperation,
        qm.DeleteVectorsOperation,
    ]
    assert sorted(BATCH_OPERATION_NAMES) == sorted(next(iter(m.model_fields)) for m in models)
    assert set(typing.get_args(BatchOperation)) == set(models)
    for name in BATCH_OPERATION_NAMES:
        assert f"`{name}`" in BATCH_OPERATIONS_DESCRIPTION


# --- the hand-written grammar can't drift from the installed client -------------------


def _json_name(model: type[BaseModel], field: str) -> str:
    return model.model_fields[field].alias or field


def test_the_filter_description_names_every_condition_the_installed_client_knows() -> None:
    expected: set[str] = set(qm.Filter.model_fields)
    for member in typing.get_args(qm.Condition):
        if member is not qm.Filter:
            expected |= {_json_name(member, f) for f in member.model_fields}
    for member in typing.get_args(qm.Match):
        expected |= {_json_name(member, f) for f in member.model_fields}
    expected |= set(qm.Range.model_fields)  # lt/lte/gt/gte
    expected |= set(qm.Slice.model_fields) | set(qm.MinShould.model_fields)
    expected |= {"center", "radius", "top_left", "bottom_right", "exterior", "interiors"}

    missing = sorted(name for name in expected if name not in FILTER_DESCRIPTION)
    assert missing == [], (
        f"qdrant-client has condition fields the compact Filter schema no longer mentions: "
        f"{missing}. Update FILTER_DESCRIPTION in mcp_qdrant/tools/schemas.py."
    )


def test_the_compact_filter_lists_the_same_top_level_keys_as_the_model() -> None:
    advertised = TypeAdapter(FilterInput).json_schema()
    assert set(advertised["properties"]) == set(qm.Filter.model_fields)


def test_the_compact_search_params_list_the_same_keys_as_the_model() -> None:
    advertised = TypeAdapter(SearchParamsInput).json_schema()
    assert set(advertised["properties"]) == set(qm.SearchParams.model_fields)

    def inner(name: str) -> set[str]:
        # every optional field is `anyOf [<schema>, null]`
        (schema,) = [
            s for s in advertised["properties"][name]["anyOf"] if s.get("type") == "object"
        ]
        return set(schema["properties"])

    assert inner("quantization") == set(qm.QuantizationSearchParams.model_fields)
    assert inner("acorn") == set(qm.AcornSearchParams.model_fields)


# --- generated schemas keep the structure of the model they came from ----------------


@pytest.mark.parametrize(
    ("annotated", "model"),
    [
        (HnswConfigDiffInput, qm.HnswConfigDiff),
        (OptimizersConfigDiffInput, qm.OptimizersConfigDiff),
        (StrictModeConfigInput, qm.StrictModeConfig),
        (CollectionParamsDiffInput, qm.CollectionParamsDiff),
    ],
)
def test_slimmed_config_models_keep_every_field(annotated: Any, model: type[BaseModel]) -> None:
    advertised = TypeAdapter(annotated).json_schema()
    assert set(advertised["properties"]) == {_json_name(model, f) for f in model.model_fields}
    assert _prose(advertised) == []


def test_slimmed_config_models_accept_real_values() -> None:
    samples: list[tuple[Any, Any]] = [
        (HnswConfigDiffInput, {"m": 0, "payload_m": 16, "ef_construct": 100}),
        (OptimizersConfigDiffInput, {"indexing_threshold": 5000, "default_segment_number": 2}),
        (StrictModeConfigInput, {"enabled": True, "max_query_limit": 100}),
        (CollectionParamsDiffInput, {"on_disk_payload": True, "replication_factor": 2}),
        (VectorParamsMapInput, {"dense": {"size": 4, "distance": "Cosine"}}),
        (VectorParamsDiffMapInput, {"dense": {"on_disk": True}}),
        (SparseVectorParamsMapInput, {"sparse": {}}),
        (
            QuantizationConfigInput,
            {"scalar": {"type": "int8", "quantile": 0.99, "always_ram": True}},
        ),
        (QuantizationConfigInput, {"binary": {"always_ram": True}}),
        (PayloadIndexSchema, "keyword"),
        (PayloadIndexSchema, {"type": "keyword", "is_tenant": True}),
        (PayloadIndexSchema, {"type": "text", "tokenizer": "word", "min_token_len": 2}),
    ]
    for annotated, sample in samples:
        validator = _advertised(annotated)
        assert validator.is_valid(sample), (annotated, sample)
        TypeAdapter(annotated).validate_python(sample)


def test_slimmed_config_models_reject_what_the_real_model_rejects() -> None:
    for annotated, bad in [
        (HnswConfigDiffInput, {"m": "many"}),
        (HnswConfigDiffInput, {"bogus": 1}),
        (VectorParamsMapInput, {"dense": {"size": 4}}),  # distance is required
        (PayloadIndexSchema, "not-a-type"),
    ]:
        assert not _advertised(annotated).is_valid(bad), (annotated, bad)
        with pytest.raises(ValidationError):
            TypeAdapter(annotated).validate_python(bad)


# --- every advertised tool schema is well-formed ---------------------------------------


def _all_tools() -> Any:
    import asyncio

    settings = Settings.from_env({"QDRANT_MCP_TOOLSETS": ",".join(ALL_TOOLSETS)})
    return asyncio.run(build_server(settings).list_tools())


def _refs(node: Any) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        found += [v for k, v in node.items() if k == "$ref" and isinstance(v, str)]
        for value in node.values():
            found += _refs(value)
    elif isinstance(node, list):
        for item in node:
            found += _refs(item)
    return found


def test_every_ref_in_every_advertised_input_schema_resolves() -> None:
    for tool in _all_tools():
        defs = tool.input_schema.get("$defs", {})
        for ref in _refs(tool.input_schema):
            assert ref.startswith("#/$defs/"), (tool.name, ref)
            assert ref.removeprefix("#/$defs/") in defs, (tool.name, ref)


def test_every_advertised_input_schema_is_itself_valid_json_schema() -> None:
    for tool in _all_tools():
        Draft202012Validator.check_schema(tool.input_schema)


# --- size budget -------------------------------------------------------------------------
#
# The MCP client loads every enabled tool's input schema into the model's context on
# every conversation. Before Fase 15 the default `core` toolset was 150 KB of input
# schemas and the full catalog 571 KB; these budgets keep it from creeping back. If a
# change legitimately needs more, raise the number deliberately and say why in the PR.

CORE_BUDGET_BYTES = 50_000  # measured: ~44 KB
CATALOG_BUDGET_BYTES = 180_000  # measured: ~160 KB
SINGLE_TOOL_BUDGET_BYTES = 15_000  # measured: largest ~13 KB


def _schema_bytes(tool: Any) -> int:
    return len(json.dumps(tool.input_schema))


def test_the_default_toolset_stays_within_its_schema_budget() -> None:
    import asyncio

    tools = asyncio.run(build_server(Settings.from_env({})).list_tools())
    total = sum(_schema_bytes(t) for t in tools)
    assert total <= CORE_BUDGET_BYTES, (
        f"`core` input schemas are {total} bytes (budget {CORE_BUDGET_BYTES}): "
        "that is context loaded into every conversation."
    )


def test_the_whole_catalog_stays_within_its_schema_budget() -> None:
    total = sum(_schema_bytes(t) for t in _all_tools())
    assert total <= CATALOG_BUDGET_BYTES, f"{total} bytes (budget {CATALOG_BUDGET_BYTES})"


def test_no_single_tool_schema_balloons() -> None:
    too_big = {
        t.name: _schema_bytes(t)
        for t in _all_tools()
        if _schema_bytes(t) > SINGLE_TOOL_BUDGET_BYTES
    }
    assert too_big == {}, f"over {SINGLE_TOOL_BUDGET_BYTES} bytes: {too_big}"
