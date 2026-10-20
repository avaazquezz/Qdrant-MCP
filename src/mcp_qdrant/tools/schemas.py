"""Input types that validate exactly like Qdrant's own models but advertise a
compact JSON Schema.

Why: every tool carries its own copy of the schema of each parameter type, and the
MCP client loads all of them into the model's context. Qdrant's `Filter` alone
expands to ~16 KB of nested conditions (`SearchParams` to ~20 KB, because its `idf`
option embeds a `Filter`), and the configuration models (`StrictModeConfig`,
`OptimizersConfigDiff`, ...) are mostly field-by-field prose. Before this module the
default `core` toolset was 150 KB of input schemas and the full catalog 571 KB.

`WithJsonSchema` replaces only the *advertised* schema. Validation is unchanged: a
tool still receives a real `Filter`/`HnswConfigDiff`/..., and a malformed value still
fails before reaching Qdrant. Two techniques, by type:

- Hand-written (`Filter`, `SearchParams`, batch operations): the types are recursive
  or huge, so the schema is a short summary and the grammar goes in a description. A
  test checks those descriptions against the installed `qdrant-client` models so they
  can't silently drift.
- Generated (`slim_schema`): for plain configuration models, start from the model's
  real schema, inline its `$ref`s and drop only the prose (`title`/`description`).
  Types, enums and constraints are kept, so nothing is written by hand to go stale.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import TypeAdapter, WithJsonSchema
from qdrant_client.http.models import (
    BinaryQuantization,
    CollectionParamsDiff,
    Filter,
    HnswConfigDiff,
    OptimizersConfigDiff,
    ProductQuantization,
    ScalarQuantization,
    SearchParams,
    SparseVectorParams,
    StrictModeConfig,
    VectorParams,
    VectorParamsDiff,
)

# --- generated: strip prose, keep structure -----------------------------------------

_FIELD_MAPPINGS = frozenset({"properties", "patternProperties", "$defs"})


def _inline_refs(node: Any, defs: dict[str, Any], stack: tuple[str, ...]) -> Any:
    """Replace every `#/$defs/X` reference by the definition itself. A cycle (not
    present in the plain configuration models this is used for) degrades to a bare
    object instead of recursing forever."""
    if isinstance(node, list):
        return [_inline_refs(item, defs, stack) for item in node]
    if not isinstance(node, dict):
        return node
    ref = node.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/$defs/"):
        name = ref.removeprefix("#/$defs/")
        if name in stack:
            return {"type": "object"}
        target = _inline_refs(defs[name], defs, (*stack, name))
        siblings = {k: _inline_refs(v, defs, stack) for k, v in node.items() if k != "$ref"}
        return {**target, **siblings}
    return {k: _inline_refs(v, defs, stack) for k, v in node.items()}


def _strip_prose(node: Any, in_fields: bool = False) -> Any:
    """Drop `title`, `description` and `default: null` from schema nodes. Inside a
    `properties`-style mapping the keys are field names (a field may literally be
    called `description`), so those are kept and only their values are recursed."""
    if isinstance(node, list):
        return [_strip_prose(item) for item in node]
    if not isinstance(node, dict):
        return node
    out: dict[str, Any] = {}
    for key, value in node.items():
        if not in_fields:
            if key in ("title", "description") and isinstance(value, str):
                continue
            if key == "default" and value is None:
                continue
        out[key] = _strip_prose(value, in_fields=not in_fields and key in _FIELD_MAPPINGS)
    return out


def slim_schema(tp: Any) -> dict[str, Any]:
    """The JSON Schema of `tp` with refs inlined and prose removed."""
    raw = TypeAdapter(tp).json_schema()
    defs = raw.pop("$defs", {})
    return _strip_prose(_inline_refs(raw, defs, ()))  # type: ignore[no-any-return]


# --- hand-written: Filter and SearchParams ------------------------------------------

FILTER_DESCRIPTION = (
    "Qdrant payload filter. Combine conditions with `must` (all hold), `should` (any "
    "holds), `must_not` (none holds) or `min_should` ({conditions, min_count}); each takes "
    'a list of conditions or a single one. A condition is one of: {"key": k, "match": M} '
    'where M is exactly one of {"value": v}, {"any": [..]}, {"except": [..]}, {"text": s}, '
    '{"text_any": s}, {"phrase": s}, {"prefix": s}; {"key": k, "range": {"lt"|"lte"|"gt"|'
    '"gte": number or datetime}}; {"key": k, "values_count": {"lt"|"lte"|"gt"|"gte": n}}; '
    '{"key": k, "geo_radius": {"center": {"lat", "lon"}, "radius": meters}}; {"key": k, '
    '"geo_bounding_box": {"top_left", "bottom_right"}}; {"key": k, "geo_polygon": '
    '{"exterior", "interiors"}}; {"is_empty": {"key": k}}; {"is_null": {"key": k}}; '
    '{"has_id": [ids]}; {"has_vector": name}; {"slice": {"total": n, "index": i}}; '
    '{"nested": {"key": k, "filter": <filter>}}; or a nested filter. Keys for nested '
    "objects use dots (`a.b`); objects inside arrays use `a[].b`."
)

# Qdrant accepts a list of conditions or a single condition (both validated by the
# real `Filter` model); the advertised schema must allow both, or a client that
# validates arguments against it would reject a legal call.
_CONDITIONS: dict[str, Any] = {
    "anyOf": [
        {"type": "array", "items": {"type": "object"}},
        {"type": "object"},
    ]
}

_FILTER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": FILTER_DESCRIPTION,
    "properties": {
        "must": _CONDITIONS,
        "should": _CONDITIONS,
        "must_not": _CONDITIONS,
        "min_should": {
            "type": "object",
            "properties": {
                "conditions": {"type": "array", "items": {"type": "object"}},
                "min_count": {"type": "integer"},
            },
            "required": ["conditions", "min_count"],
        },
    },
    "additionalProperties": False,
}

_SEARCH_PARAMS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": (
        "Search-time tuning. `hnsw_ef`: beam width of the HNSW search (higher = more "
        "accurate, slower). `exact`: skip the index and brute-force. `indexed_only`: "
        "search only indexed segments. `quantization`: {ignore, rescore, oversampling} "
        "for quantized collections. `acorn`: {enable, max_selectivity} for filtered "
        "searches. `idf`: advanced, for sparse-vector IDF scoring."
    ),
    "properties": {
        "hnsw_ef": {"type": "integer"},
        "exact": {"type": "boolean"},
        "indexed_only": {"type": "boolean"},
        "quantization": {
            "type": "object",
            "properties": {
                "ignore": {"type": "boolean"},
                "rescore": {"type": "boolean"},
                "oversampling": {"type": "number"},
            },
        },
        "acorn": {
            "type": "object",
            "properties": {
                "enable": {"type": "boolean"},
                "max_selectivity": {"type": "number"},
            },
        },
        "idf": {"type": "object"},
    },
    "additionalProperties": False,
}

BATCH_OPERATIONS_DESCRIPTION = (
    "Point operations applied in order. Each item is an object with exactly one key: "
    '`upsert` ({"points": [{id, vector, payload}]} or {"batch": {ids, vectors, '
    'payloads}}), `delete` ({"points": [ids]} or {"filter": <filter>}), `set_payload` '
    "and `overwrite_payload` ({payload, points | filter, key?}), `delete_payload` "
    '({keys, points | filter}), `clear_payload` ({"points": [ids]} or {"filter": '
    '<filter>}), `update_vectors` ({"points": [{id, vector}]}) or `delete_vectors` '
    "({vector: [names], points | filter})."
)

BATCH_OPERATION_NAMES = (
    "upsert",
    "delete",
    "set_payload",
    "overwrite_payload",
    "delete_payload",
    "clear_payload",
    "update_vectors",
    "delete_vectors",
)

_BATCH_OPERATIONS_SCHEMA: dict[str, Any] = {
    "type": "array",
    "minItems": 1,
    "description": BATCH_OPERATIONS_DESCRIPTION,
    "items": {
        "type": "object",
        "minProperties": 1,
        "maxProperties": 1,
        "propertyNames": {"enum": list(BATCH_OPERATION_NAMES)},
    },
}

FilterInput = Annotated[Filter, WithJsonSchema(_FILTER_SCHEMA)]
SearchParamsInput = Annotated[SearchParams, WithJsonSchema(_SEARCH_PARAMS_SCHEMA)]
BatchOperationsSchema = WithJsonSchema(_BATCH_OPERATIONS_SCHEMA)

# --- configuration models ------------------------------------------------------------

_QUANTIZATION = ScalarQuantization | ProductQuantization | BinaryQuantization

VectorParamsMapInput = Annotated[
    dict[str, VectorParams], WithJsonSchema(slim_schema(dict[str, VectorParams]))
]
SparseVectorParamsMapInput = Annotated[
    dict[str, SparseVectorParams], WithJsonSchema(slim_schema(dict[str, SparseVectorParams]))
]
VectorParamsDiffMapInput = Annotated[
    dict[str, VectorParamsDiff], WithJsonSchema(slim_schema(dict[str, VectorParamsDiff]))
]
QuantizationConfigInput = Annotated[_QUANTIZATION, WithJsonSchema(slim_schema(_QUANTIZATION))]
StrictModeConfigInput = Annotated[StrictModeConfig, WithJsonSchema(slim_schema(StrictModeConfig))]
HnswConfigDiffInput = Annotated[HnswConfigDiff, WithJsonSchema(slim_schema(HnswConfigDiff))]
OptimizersConfigDiffInput = Annotated[
    OptimizersConfigDiff, WithJsonSchema(slim_schema(OptimizersConfigDiff))
]
CollectionParamsDiffInput = Annotated[
    CollectionParamsDiff, WithJsonSchema(slim_schema(CollectionParamsDiff))
]
