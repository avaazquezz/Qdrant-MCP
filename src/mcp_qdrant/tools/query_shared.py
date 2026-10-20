"""Query-construction helpers shared by the `qdrant_query` family: `query.py`'s
`qdrant_query` (toolset `core`) and `search.py`'s `qdrant_query_batch`/`_groups`,
`qdrant_recommend*`, `qdrant_discover*` (toolset `search`). Not a toolset itself —
nothing here calls `ToolRegistry.register`.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from qdrant_client.http.models import (
    Expression,
    Filter,
    FormulaQuery,
    Fusion,
    FusionQuery,
    LookupLocation,
    Mmr,
    NearestQuery,
    OrderBy,
    OrderByQuery,
    Prefetch,
    Query,
    ReadConsistencyType,
    Rrf,
    RrfQuery,
    Sample,
    SampleQuery,
    SearchParams,
    SparseVector,
)

_DenseVector = Annotated[list[float], Field(min_length=1)]
# A query/example vector: a dense vector, a multivector (list of vectors,
# ColBERT-style), a sparse vector ({"indices": [...], "values": [...]}), or a
# point id whose stored vector is reused. Which one is valid depends on the
# named vector selected with `using`. Both list shapes need min_length: an
# empty `[]` would otherwise validate as an empty multivector
# (list[list[float]]) and reach Qdrant as a nonsensical query.
VectorOrId = (
    _DenseVector | Annotated[list[_DenseVector], Field(min_length=1)] | SparseVector | int | str
)
FusionName = Literal["rrf", "dbsf"]
ConsistencyInput = Annotated[int, Field(gt=0)] | Literal["majority", "quorum", "all"]
TimeoutSeconds = Annotated[int, Field(gt=0)]
OffsetInput = Annotated[int, Field(ge=0)]

_FUSION_BY_NAME: dict[FusionName, Fusion] = {"rrf": Fusion.RRF, "dbsf": Fusion.DBSF}

# Parsed once: building this adapter walks a 26-member recursive union.
_EXPRESSION: TypeAdapter[Any] = TypeAdapter(Expression)


class WeightedRrfInput(BaseModel):
    """Reciprocal Rank Fusion with tuning, instead of the plain `"rrf"` name:
    `weights` gives each prefetch stage's ranking a weight (one per stage, in
    order), `k` is the rank-smoothing constant."""

    method: Literal["rrf"] = "rrf"
    k: Annotated[int, Field(gt=0)] | None = None
    weights: Annotated[list[float], Field(min_length=1)] | None = None


FusionInput = FusionName | WeightedRrfInput


class MmrInput(BaseModel):
    """Maximal Marginal Relevance: re-orders the nearest candidates to trade
    relevance for diversity. `diversity` runs 0 (pure relevance) to 1 (most
    diverse). `candidates_limit` is how many nearest candidates it re-ranks; it
    defaults to the query's `limit`, so MMR has nothing to choose from unless
    you set it well above `limit` (verified: `limit` 2 without it returns the
    same two points as a plain query)."""

    diversity: Annotated[float, Field(ge=0, le=1)] | None = None
    candidates_limit: Annotated[int, Field(gt=0)] | None = None


class FormulaInput(BaseModel):
    """A custom scoring formula applied over the results of `prefetch` stages.
    `expression` is typed loosely on purpose (the full grammar is a 35 KB
    recursive schema that would bloat every tool listing); it is validated
    server-side and the grammar is documented on `qdrant_query`. `defaults`
    supplies a value for payload keys a point doesn't have."""

    expression: dict[str, Any] | float | str
    defaults: dict[str, Any] | None = None


class PrefetchInput(BaseModel):
    """One prefetch stage: an independent query narrowing candidates before
    the outer query reranks or fuses them. A stage is either a vector query
    (`query_vector`) or a fusion of its own nested `prefetch` stages
    (`fusion`) — exactly one — which makes multi-stage pipelines possible,
    e.g. fuse dense+sparse, then rerank with a multivector."""

    query_vector: VectorOrId | None = None
    fusion: FusionInput | None = None
    prefetch: list[PrefetchInput] | None = None
    using: str | None = None
    query_filter: Filter | None = None
    search_params: SearchParams | None = None
    score_threshold: float | None = None
    limit: int | None = None


class LookupFromInput(BaseModel):
    """Resolve the query/context vector from a point id in another
    collection instead of passing it inline."""

    collection: str
    vector: str | None = None


def _build_fusion(fusion: FusionInput) -> FusionQuery | RrfQuery:
    if isinstance(fusion, WeightedRrfInput):
        return RrfQuery(rrf=Rrf(k=fusion.k, weights=fusion.weights))
    return FusionQuery(fusion=_FUSION_BY_NAME[fusion])


def _build_formula(formula: FormulaInput) -> FormulaQuery:
    try:
        expression = _EXPRESSION.validate_python(formula.expression)
    except ValidationError as exc:
        # Pydantic reports one error per rejected union member (~100 for this
        # union), which is noise for the caller — say what's expected instead.
        raise ToolError(
            "`formula.expression` is not a valid formula expression. It must be a number, a "
            'variable ("$score" or a payload key), a payload condition, or exactly one '
            "operator object: sum, mult, neg, abs, div, sqrt, pow, exp, log10, ln, "
            "geo_distance, datetime, datetime_key, lin_decay, exp_decay or gauss_decay."
        ) from exc
    return FormulaQuery(formula=expression, defaults=formula.defaults)


def build_query_value(
    query_vector: VectorOrId | None,
    fusion: FusionInput | None,
    *,
    mmr: MmrInput | None = None,
    formula: FormulaInput | None = None,
    order_by: OrderBy | str | None = None,
    sample: Literal["random"] | None = None,
) -> VectorOrId | Query:
    """Exactly one of `query_vector` (a literal vector or point id), `fusion`
    (combine the prefetch stages), `formula` (rescore the prefetch results),
    `order_by` (sort by a payload field) or `sample` (random points) must be
    given. `mmr` modifies a `query_vector` query and is invalid without one."""
    modes = (query_vector, fusion, formula, order_by, sample)
    if sum(mode is not None for mode in modes) != 1:
        raise ToolError(
            "Provide exactly one of `query_vector`, `fusion`, `formula`, `order_by` or "
            "`sample`, not several/none."
        )
    if mmr is not None and query_vector is None:
        raise ToolError("`mmr` only applies to a `query_vector` query.")
    if query_vector is not None:
        if mmr is not None:
            return NearestQuery(
                nearest=query_vector,
                mmr=Mmr(diversity=mmr.diversity, candidates_limit=mmr.candidates_limit),
            )
        return query_vector
    if fusion is not None:
        return _build_fusion(fusion)
    if formula is not None:
        return _build_formula(formula)
    if order_by is not None:
        return OrderByQuery(order_by=order_by)
    return SampleQuery(sample=Sample.RANDOM)


def build_prefetch_list(prefetch: list[PrefetchInput] | None) -> list[Prefetch] | None:
    if prefetch is None:
        return None
    return [
        Prefetch(
            prefetch=build_prefetch_list(p.prefetch),
            query=build_query_value(p.query_vector, p.fusion),
            using=p.using,
            filter=p.query_filter,
            params=p.search_params,
            score_threshold=p.score_threshold,
            limit=p.limit,
        )
        for p in prefetch
    ]


def build_lookup_from(lookup_from: LookupFromInput | None) -> LookupLocation | None:
    if lookup_from is None:
        return None
    return LookupLocation(collection=lookup_from.collection, vector=lookup_from.vector)


def build_consistency(value: ConsistencyInput | None) -> int | ReadConsistencyType | None:
    return ReadConsistencyType(value) if isinstance(value, str) else value
