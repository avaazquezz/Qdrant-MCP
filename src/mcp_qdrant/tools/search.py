"""The `search` toolset (Fase 2): batch/grouped queries, recommend, discover,
and the pairwise distance matrix — everything the unified Query API covers
beyond Fase 1's single-vector `qdrant_query`.

Legacy `search`/`recommend`/`discover` endpoints are deliberately not wrapped
here: `qdrant-client==1.19.0` no longer exposes them (not even in its
low-level REST layer) — they were fully consolidated into `query_points`/
`query_batch_points`/`query_points_groups`, which this module builds on via
`mcp_qdrant.tools.query_shared`.
"""

from __future__ import annotations

from typing import Annotated, Literal

from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    ContextPair,
    DiscoverInput,
    DiscoverQuery,
    Filter,
    GroupsResult,
    OrderBy,
    QueryRequest,
    QueryResponse,
    RecommendInput,
    RecommendQuery,
    RecommendStrategy,
    SearchMatrixOffsetsResponse,
    SearchMatrixPairsResponse,
    SearchParams,
    VectorInput,
)

from mcp_qdrant.tools.errors import call_qdrant
from mcp_qdrant.tools.query_shared import (
    ConsistencyInput,
    FormulaInput,
    FusionInput,
    LookupFromInput,
    MmrInput,
    OffsetInput,
    PrefetchInput,
    TimeoutSeconds,
    VectorOrId,
    build_consistency,
    build_lookup_from,
    build_prefetch_list,
    build_query_value,
)
from mcp_qdrant.tools.registry import ToolRegistry

RecommendStrategyName = Literal["average_vector", "best_score", "sum_scores"]

_STRATEGY_BY_NAME: dict[RecommendStrategyName, RecommendStrategy] = {
    "average_vector": RecommendStrategy.AVERAGE_VECTOR,
    "best_score": RecommendStrategy.BEST_SCORE,
    "sum_scores": RecommendStrategy.SUM_SCORES,
}

_QUERY_BATCH_ANNOTATIONS = ToolAnnotations(
    title="Batch-query Qdrant by vector similarity",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_QUERY_GROUPS_ANNOTATIONS = ToolAnnotations(
    title="Query Qdrant grouped by a payload field",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_RECOMMEND_ANNOTATIONS = ToolAnnotations(
    title="Recommend Qdrant points from positive/negative examples",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_RECOMMEND_BATCH_ANNOTATIONS = ToolAnnotations(
    title="Batch-recommend Qdrant points",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_RECOMMEND_GROUPS_ANNOTATIONS = ToolAnnotations(
    title="Recommend Qdrant points grouped by a payload field",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_DISCOVER_ANNOTATIONS = ToolAnnotations(
    title="Discover Qdrant points via target + context",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_DISCOVER_BATCH_ANNOTATIONS = ToolAnnotations(
    title="Batch-discover Qdrant points",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_DISTANCE_MATRIX_PAIRS_ANNOTATIONS = ToolAnnotations(
    title="Pairwise distance matrix between sampled points",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_DISTANCE_MATRIX_OFFSETS_ANNOTATIONS = ToolAnnotations(
    title="Pairwise distance matrix (offset-encoded) between sampled points",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)


class QuerySpec(BaseModel):
    """One item of a `qdrant_query_batch` call — same shape as
    `qdrant_query`'s parameters, minus `collection_name`, `timeout_seconds` and
    `consistency` (those apply to the whole batch)."""

    query_vector: VectorOrId | None = None
    fusion: FusionInput | None = None
    prefetch: list[PrefetchInput] | None = None
    mmr: MmrInput | None = None
    formula: FormulaInput | None = None
    order_by: OrderBy | str | None = None
    sample: Literal["random"] | None = None
    using: str | None = None
    lookup_from: LookupFromInput | None = None
    query_filter: Filter | None = None
    search_params: SearchParams | None = None
    score_threshold: float | None = None
    limit: Annotated[int, Field(gt=0)] = 10
    offset: OffsetInput | None = None
    with_payload: bool = True
    with_vectors: bool = False

    def to_request(self) -> QueryRequest:
        return QueryRequest(
            query=build_query_value(
                self.query_vector,
                self.fusion,
                mmr=self.mmr,
                formula=self.formula,
                order_by=self.order_by,
                sample=self.sample,
            ),
            using=self.using,
            prefetch=build_prefetch_list(self.prefetch),
            filter=self.query_filter,
            params=self.search_params,
            score_threshold=self.score_threshold,
            lookup_from=build_lookup_from(self.lookup_from),
            limit=self.limit,
            offset=self.offset,
            with_payload=self.with_payload,
            with_vector=self.with_vectors,
        )


class ContextPairInput(BaseModel):
    positive: VectorOrId
    negative: VectorOrId


class RecommendSpec(BaseModel):
    """One item of a `qdrant_recommend_batch` call — same shape as
    `qdrant_recommend`'s parameters, minus `collection_name`."""

    positive: list[VectorOrId] | None = None
    negative: list[VectorOrId] | None = None
    strategy: RecommendStrategyName | None = None
    using: str | None = None
    lookup_from: LookupFromInput | None = None
    prefetch: list[PrefetchInput] | None = None
    query_filter: Filter | None = None
    search_params: SearchParams | None = None
    score_threshold: float | None = None
    limit: Annotated[int, Field(gt=0)] = 10
    offset: OffsetInput | None = None
    with_payload: bool = True
    with_vectors: bool = False

    def to_request(self) -> QueryRequest:
        return QueryRequest(
            query=_build_recommend_query(self.positive, self.negative, self.strategy),
            using=self.using,
            prefetch=build_prefetch_list(self.prefetch),
            filter=self.query_filter,
            params=self.search_params,
            score_threshold=self.score_threshold,
            lookup_from=build_lookup_from(self.lookup_from),
            limit=self.limit,
            offset=self.offset,
            with_payload=self.with_payload,
            with_vector=self.with_vectors,
        )


class DiscoverSpec(BaseModel):
    """One item of a `qdrant_discover_batch` call — same shape as
    `qdrant_discover`'s parameters, minus `collection_name`."""

    target: VectorOrId
    context: Annotated[list[ContextPairInput], Field(min_length=1)]
    using: str | None = None
    lookup_from: LookupFromInput | None = None
    prefetch: list[PrefetchInput] | None = None
    query_filter: Filter | None = None
    search_params: SearchParams | None = None
    score_threshold: float | None = None
    limit: Annotated[int, Field(gt=0)] = 10
    offset: OffsetInput | None = None
    with_payload: bool = True
    with_vectors: bool = False

    def to_request(self) -> QueryRequest:
        return QueryRequest(
            query=_build_discover_query(self.target, self.context),
            using=self.using,
            prefetch=build_prefetch_list(self.prefetch),
            filter=self.query_filter,
            params=self.search_params,
            score_threshold=self.score_threshold,
            lookup_from=build_lookup_from(self.lookup_from),
            limit=self.limit,
            offset=self.offset,
            with_payload=self.with_payload,
            with_vector=self.with_vectors,
        )


def _build_recommend_query(
    positive: list[VectorOrId] | None,
    negative: list[VectorOrId] | None,
    strategy: RecommendStrategyName | None,
) -> RecommendQuery:
    # list is invariant in mypy: list[VectorOrId] isn't assignable to
    # RecommendInput's list[VectorInput] even though every VectorOrId member
    # is also a VectorInput member — rebuild with the wider element type.
    positive_examples: list[VectorInput] | None = list(positive) if positive is not None else None
    negative_examples: list[VectorInput] | None = list(negative) if negative is not None else None
    return RecommendQuery(
        recommend=RecommendInput(
            positive=positive_examples,
            negative=negative_examples,
            strategy=_STRATEGY_BY_NAME[strategy] if strategy is not None else None,
        )
    )


def _build_discover_query(target: VectorOrId, context: list[ContextPairInput]) -> DiscoverQuery:
    pairs = [ContextPair(positive=c.positive, negative=c.negative) for c in context]
    return DiscoverQuery(discover=DiscoverInput(target=target, context=pairs))


def register(registry: ToolRegistry, client: AsyncQdrantClient) -> None:
    async def qdrant_query_batch(
        collection_name: str,
        queries: Annotated[list[QuerySpec], Field(min_length=1)],
        timeout_seconds: TimeoutSeconds | None = None,
        consistency: ConsistencyInput | None = None,
    ) -> list[QueryResponse]:
        """Run multiple independent queries against one collection in a
        single round trip — each item takes every query mode and tuning
        parameter of `qdrant_query` (plain vector, fusion over prefetch, MMR,
        formula, order_by, sample, search_params, score_threshold, offset);
        `timeout_seconds` and `consistency` apply to the whole batch.

        Example: {"collection_name": "docs", "queries": [
            {"query_vector": [0.1, 0.2, 0.3, 0.4], "limit": 5},
            {"query_vector": [0.5, 0.5, 0.5, 0.5], "limit": 5}
        ]}
        """
        requests = [q.to_request() for q in queries]
        return await call_qdrant(
            lambda: client.query_batch_points(
                collection_name,
                requests=requests,
                consistency=build_consistency(consistency),
                timeout=timeout_seconds,
            )
        )

    async def qdrant_query_groups(
        collection_name: str,
        group_by: str,
        query_vector: VectorOrId | None = None,
        fusion: FusionInput | None = None,
        prefetch: list[PrefetchInput] | None = None,
        mmr: MmrInput | None = None,
        formula: FormulaInput | None = None,
        order_by: OrderBy | str | None = None,
        sample: Literal["random"] | None = None,
        using: str | None = None,
        lookup_from: LookupFromInput | None = None,
        query_filter: Filter | None = None,
        search_params: SearchParams | None = None,
        score_threshold: float | None = None,
        limit: Annotated[int, Field(gt=0)] = 10,
        group_size: Annotated[int, Field(gt=0)] = 3,
        with_payload: bool = True,
        with_vectors: bool = False,
        with_lookup: str | None = None,
        timeout_seconds: TimeoutSeconds | None = None,
        consistency: ConsistencyInput | None = None,
    ) -> GroupsResult:
        """Vector query grouped by a payload field, up to `group_size` hits
        per group — e.g. the best-matching chunks per source document. Takes
        every query mode and tuning parameter of `qdrant_query` except
        `offset` (groups have no paging).

        Example: {"collection_name": "docs", "group_by": "document_id",
            "query_vector": [0.1, 0.2, 0.3, 0.4], "group_size": 2}
        """
        query = build_query_value(
            query_vector, fusion, mmr=mmr, formula=formula, order_by=order_by, sample=sample
        )
        return await call_qdrant(
            lambda: client.query_points_groups(
                collection_name,
                group_by=group_by,
                query=query,
                using=using,
                prefetch=build_prefetch_list(prefetch),
                query_filter=query_filter,
                search_params=search_params,
                score_threshold=score_threshold,
                lookup_from=build_lookup_from(lookup_from),
                limit=limit,
                group_size=group_size,
                with_payload=with_payload,
                with_vectors=with_vectors,
                with_lookup=with_lookup,
                timeout=timeout_seconds,
                consistency=build_consistency(consistency),
            )
        )

    async def qdrant_recommend(
        collection_name: str,
        positive: list[VectorOrId] | None = None,
        negative: list[VectorOrId] | None = None,
        strategy: RecommendStrategyName | None = None,
        using: str | None = None,
        lookup_from: LookupFromInput | None = None,
        prefetch: list[PrefetchInput] | None = None,
        query_filter: Filter | None = None,
        search_params: SearchParams | None = None,
        score_threshold: float | None = None,
        limit: Annotated[int, Field(gt=0)] = 10,
        offset: OffsetInput | None = None,
        with_payload: bool = True,
        with_vectors: bool = False,
        timeout_seconds: TimeoutSeconds | None = None,
        consistency: ConsistencyInput | None = None,
    ) -> QueryResponse:
        """Find points similar to a set of positive examples and dissimilar
        to a set of negative ones (vectors or point ids) — Qdrant's
        recommendation API. Requires at least one of `positive`/`negative`;
        the server rejects an empty request with a clear error. Examples may
        be dense, multi- or sparse vectors, matching `using`.

        Takes the same tuning parameters as `qdrant_query`: `search_params`,
        `score_threshold`, `offset`, `timeout_seconds`, `consistency`.

        Example: {"collection_name": "docs", "positive": [1, 2], "negative": [7]}
        """
        return await call_qdrant(
            lambda: client.query_points(
                collection_name,
                query=_build_recommend_query(positive, negative, strategy),
                using=using,
                prefetch=build_prefetch_list(prefetch),
                query_filter=query_filter,
                search_params=search_params,
                score_threshold=score_threshold,
                lookup_from=build_lookup_from(lookup_from),
                limit=limit,
                offset=offset,
                with_payload=with_payload,
                with_vectors=with_vectors,
                timeout=timeout_seconds,
                consistency=build_consistency(consistency),
            )
        )

    async def qdrant_recommend_batch(
        collection_name: str,
        requests: Annotated[list[RecommendSpec], Field(min_length=1)],
        timeout_seconds: TimeoutSeconds | None = None,
        consistency: ConsistencyInput | None = None,
    ) -> list[QueryResponse]:
        """Run multiple independent recommend queries against one
        collection in a single round trip. Each item takes the tuning
        parameters of `qdrant_recommend`; `timeout_seconds` and `consistency`
        apply to the whole batch.

        Example: {"collection_name": "docs", "requests": [
            {"positive": [1], "negative": [7]},
            {"positive": [2, 3]}
        ]}
        """
        built = [r.to_request() for r in requests]
        return await call_qdrant(
            lambda: client.query_batch_points(
                collection_name,
                requests=built,
                consistency=build_consistency(consistency),
                timeout=timeout_seconds,
            )
        )

    async def qdrant_recommend_groups(
        collection_name: str,
        group_by: str,
        positive: list[VectorOrId] | None = None,
        negative: list[VectorOrId] | None = None,
        strategy: RecommendStrategyName | None = None,
        using: str | None = None,
        lookup_from: LookupFromInput | None = None,
        prefetch: list[PrefetchInput] | None = None,
        query_filter: Filter | None = None,
        search_params: SearchParams | None = None,
        score_threshold: float | None = None,
        limit: Annotated[int, Field(gt=0)] = 10,
        group_size: Annotated[int, Field(gt=0)] = 3,
        with_payload: bool = True,
        with_vectors: bool = False,
        with_lookup: str | None = None,
        timeout_seconds: TimeoutSeconds | None = None,
        consistency: ConsistencyInput | None = None,
    ) -> GroupsResult:
        """Recommend query grouped by a payload field, up to `group_size`
        hits per group. Takes the tuning parameters of `qdrant_recommend`
        except `offset` (groups have no paging).

        Example: {"collection_name": "docs", "group_by": "document_id",
            "positive": [1, 2], "group_size": 2}
        """
        return await call_qdrant(
            lambda: client.query_points_groups(
                collection_name,
                group_by=group_by,
                query=_build_recommend_query(positive, negative, strategy),
                using=using,
                prefetch=build_prefetch_list(prefetch),
                query_filter=query_filter,
                search_params=search_params,
                score_threshold=score_threshold,
                lookup_from=build_lookup_from(lookup_from),
                limit=limit,
                group_size=group_size,
                with_payload=with_payload,
                with_vectors=with_vectors,
                with_lookup=with_lookup,
                timeout=timeout_seconds,
                consistency=build_consistency(consistency),
            )
        )

    async def qdrant_discover(
        collection_name: str,
        target: VectorOrId,
        context: Annotated[list[ContextPairInput], Field(min_length=1)],
        using: str | None = None,
        lookup_from: LookupFromInput | None = None,
        prefetch: list[PrefetchInput] | None = None,
        query_filter: Filter | None = None,
        search_params: SearchParams | None = None,
        score_threshold: float | None = None,
        limit: Annotated[int, Field(gt=0)] = 10,
        offset: OffsetInput | None = None,
        with_payload: bool = True,
        with_vectors: bool = False,
        timeout_seconds: TimeoutSeconds | None = None,
        consistency: ConsistencyInput | None = None,
    ) -> QueryResponse:
        """Rank points by how well they fit a target within positive/negative
        context pairs (vectors or point ids) — Qdrant's discovery search, a
        finer-grained alternative to recommend. The target and context may be
        dense, multi- or sparse vectors, matching `using`.

        Takes the same tuning parameters as `qdrant_query`: `search_params`,
        `score_threshold`, `offset`, `timeout_seconds`, `consistency`.

        Example: {"collection_name": "docs", "target": 1, "context": [
            {"positive": 2, "negative": 7}
        ]}
        """
        return await call_qdrant(
            lambda: client.query_points(
                collection_name,
                query=_build_discover_query(target, context),
                using=using,
                prefetch=build_prefetch_list(prefetch),
                query_filter=query_filter,
                search_params=search_params,
                score_threshold=score_threshold,
                lookup_from=build_lookup_from(lookup_from),
                limit=limit,
                offset=offset,
                with_payload=with_payload,
                with_vectors=with_vectors,
                timeout=timeout_seconds,
                consistency=build_consistency(consistency),
            )
        )

    async def qdrant_discover_batch(
        collection_name: str,
        requests: Annotated[list[DiscoverSpec], Field(min_length=1)],
        timeout_seconds: TimeoutSeconds | None = None,
        consistency: ConsistencyInput | None = None,
    ) -> list[QueryResponse]:
        """Run multiple independent discover queries against one collection
        in a single round trip. Each item takes the tuning parameters of
        `qdrant_discover`; `timeout_seconds` and `consistency` apply to the
        whole batch.

        Example: {"collection_name": "docs", "requests": [
            {"target": 1, "context": [{"positive": 2, "negative": 7}]}
        ]}
        """
        built = [r.to_request() for r in requests]
        return await call_qdrant(
            lambda: client.query_batch_points(
                collection_name,
                requests=built,
                consistency=build_consistency(consistency),
                timeout=timeout_seconds,
            )
        )

    async def qdrant_distance_matrix_pairs(
        collection_name: str,
        query_filter: Filter | None = None,
        limit: Annotated[int, Field(gt=0)] = 3,
        sample: Annotated[int, Field(gt=0)] = 10,
        using: str | None = None,
    ) -> SearchMatrixPairsResponse:
        """Pairwise distance matrix between a random sample of points: for
        each of `sample` points, its `limit` closest neighbors among that
        same sample — returned as a flat list of (a, b, score) pairs.

        Example: {"collection_name": "docs", "sample": 20, "limit": 5}
        """
        return await call_qdrant(
            lambda: client.search_matrix_pairs(
                collection_name, query_filter=query_filter, limit=limit, sample=sample, using=using
            )
        )

    async def qdrant_distance_matrix_offsets(
        collection_name: str,
        query_filter: Filter | None = None,
        limit: Annotated[int, Field(gt=0)] = 3,
        sample: Annotated[int, Field(gt=0)] = 10,
        using: str | None = None,
    ) -> SearchMatrixOffsetsResponse:
        """Same distance matrix as `qdrant_distance_matrix_pairs`, in a
        column-oriented shape (offsets into a shared id list + a parallel
        score array) — more compact for large samples.

        Example: {"collection_name": "docs", "sample": 20, "limit": 5}
        """
        return await call_qdrant(
            lambda: client.search_matrix_offsets(
                collection_name, query_filter=query_filter, limit=limit, sample=sample, using=using
            )
        )

    registry.register(qdrant_query_batch, toolset="search", annotations=_QUERY_BATCH_ANNOTATIONS)
    registry.register(qdrant_query_groups, toolset="search", annotations=_QUERY_GROUPS_ANNOTATIONS)
    registry.register(qdrant_recommend, toolset="search", annotations=_RECOMMEND_ANNOTATIONS)
    registry.register(
        qdrant_recommend_batch, toolset="search", annotations=_RECOMMEND_BATCH_ANNOTATIONS
    )
    registry.register(
        qdrant_recommend_groups, toolset="search", annotations=_RECOMMEND_GROUPS_ANNOTATIONS
    )
    registry.register(qdrant_discover, toolset="search", annotations=_DISCOVER_ANNOTATIONS)
    registry.register(
        qdrant_discover_batch, toolset="search", annotations=_DISCOVER_BATCH_ANNOTATIONS
    )
    registry.register(
        qdrant_distance_matrix_pairs,
        toolset="search",
        annotations=_DISTANCE_MATRIX_PAIRS_ANNOTATIONS,
    )
    registry.register(
        qdrant_distance_matrix_offsets,
        toolset="search",
        annotations=_DISTANCE_MATRIX_OFFSETS_ANNOTATIONS,
    )
