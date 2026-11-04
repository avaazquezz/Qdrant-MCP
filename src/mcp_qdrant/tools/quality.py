"""The `admin` toolset (Fase 20): measure how good a collection's approximate search is.

`qdrant_search_quality_eval` answers "is my HNSW/quantization setup losing results, and what
does it cost in latency?" with numbers instead of folklore: it takes points the collection
already holds as queries, runs each as an exact (brute-force) search — the ground truth — and as
an approximate search with every `search_params` variant asked for, and reports recall@k and
latency per variant. Deterministic code over data already in Qdrant; no embeddings.
"""

from __future__ import annotations

import math
import statistics
import time
from typing import Annotated, Any

from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    CollectionInfo,
    ExtendedPointId,
    Sample,
    SampleQuery,
    SearchParams,
    VectorParams,
)

from mcp_qdrant.tools.errors import call_qdrant
from mcp_qdrant.tools.registry import ToolRegistry
from mcp_qdrant.tools.schemas import SearchParamsInput

_ANNOTATIONS = ToolAnnotations(
    title="Measure the search quality of a Qdrant collection",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)


class VariantQuality(BaseModel):
    """`recall_*` is null when no query had any other point to find."""

    search_params: dict[str, Any]
    recall_mean: float | None
    recall_min: float | None
    latency_ms_p50: float
    latency_ms_p95: float


class SearchQualityReport(BaseModel):
    collection: str
    using: str | None
    points_count: int | None
    indexed_vectors_count: int | None
    queries: int
    limit: int
    exact_latency_ms_p50: float
    exact_latency_ms_p95: float
    variants: list[VariantQuality]
    notes: list[str]


def _pick_vector(info: CollectionInfo, using: str | None, collection: str) -> str:
    """The dense or multivector vector to evaluate ("" = the unnamed one)."""
    sparse = set(info.config.params.sparse_vectors or {})
    if using is not None and using in sparse:
        raise ToolError(
            f"{using!r} is a sparse vector: sparse search is always exact, so there is no "
            "approximation to measure."
        )
    vectors = info.config.params.vectors
    if isinstance(vectors, VectorParams):
        if using not in (None, ""):
            raise ToolError(f"{collection!r} has a single unnamed vector; omit `using`.")
        return ""
    names = sorted(vectors or {})
    if using is not None:
        if using not in names:
            raise ToolError(f"{collection!r} has no dense vector {using!r}; it has {names}.")
        return using
    if len(names) == 1:
        return names[0]
    raise ToolError(f"{collection!r} has several vectors ({names}): set `using` to one.")


def _p95(values: list[float]) -> float:
    """Nearest-rank 95th percentile: an actual observed value, defined for any n ≥ 1."""
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def _ms(values: list[float]) -> tuple[float, float]:
    return round(statistics.median(values) * 1000, 2), round(_p95(values) * 1000, 2)


def register(registry: ToolRegistry, client: AsyncQdrantClient) -> None:
    async def qdrant_search_quality_eval(
        collection_name: str,
        using: str | None = None,
        sample: Annotated[int, Field(ge=1, le=200)] = 20,
        limit: Annotated[int, Field(ge=1, le=100)] = 10,
        variants: Annotated[list[SearchParamsInput], Field(min_length=1, max_length=5)]
        | None = None,
    ) -> SearchQualityReport:
        """Measure how much a collection's approximate (HNSW, quantized) search loses against
        an exact one, and what each configuration costs in latency — so a tuning change is
        judged by numbers.

        Takes `sample` random points the collection already holds and uses each one's vector
        (the one in `using`; omit it when there's only one) as a query. For each query it runs
        an exact brute-force search — the ground truth — and an approximate search per
        `variants` entry (each a `search_params` object such as `{"hnsw_ef": 128}` or
        `{"quantization": {"rescore": true, "oversampling": 2.0}}`; by default one variant with
        the collection's own settings). The query point itself is left out of both result lists
        without a filter (a filter would switch Qdrant to its filtered-search path and measure
        that instead). Reports, per variant, recall@`limit` (mean and worst query: the share of
        the exact top-`limit` the approximate search also returned) and latency p50/p95.

        Read the numbers with care: points used as their own queries sit inside the data, so
        recall here is usually higher than for real queries; latency is measured by this
        server and includes the round trip to Qdrant. Below the indexing threshold there is no
        HNSW index yet and approximate search is exact, so recall is 1.0 by construction (the
        report says so). Sparse vectors are always searched exactly and are refused.

        Example: {"collection_name": "docs", "variants": [{}, {"hnsw_ef": 32}, {"hnsw_ef": 256}]}
        """
        info = await call_qdrant(lambda: client.get_collection(collection_name))
        vector_name = _pick_vector(info, using, collection_name)
        qdrant_using = vector_name or None
        params_list = variants or [SearchParams()]

        sampled = await call_qdrant(
            lambda: client.query_points(
                collection_name,
                query=SampleQuery(sample=Sample.RANDOM),
                using=qdrant_using,
                limit=sample,
                with_payload=False,
                with_vectors=[vector_name] if vector_name else True,
            )
        )
        queries: list[tuple[ExtendedPointId, Any]] = []
        for point in sampled.points:
            vector = (
                point.vector.get(vector_name) if isinstance(point.vector, dict) else point.vector
            )
            if vector is not None:  # a named vector is optional per point
                queries.append((point.id, vector))
        if not queries:
            raise ToolError(f"{collection_name!r} has no points with this vector to sample.")

        async def timed_search(
            query: Any, self_id: ExtendedPointId, params: SearchParams
        ) -> tuple[list[ExtendedPointId], float]:
            started = time.perf_counter()
            response = await call_qdrant(
                lambda: client.query_points(
                    collection_name,
                    query=query,
                    using=qdrant_using,
                    search_params=params,
                    limit=limit + 1,
                    with_payload=False,
                )
            )
            elapsed = time.perf_counter() - started
            ids = [p.id for p in response.points if p.id != self_id]
            return ids[:limit], elapsed

        exact_times: list[float] = []
        recalls: list[list[float]] = [[] for _ in params_list]
        times: list[list[float]] = [[] for _ in params_list]
        for self_id, vector in queries:
            truth, elapsed = await timed_search(vector, self_id, SearchParams(exact=True))
            exact_times.append(elapsed)
            for index, params in enumerate(params_list):
                found, elapsed = await timed_search(vector, self_id, params)
                times[index].append(elapsed)
                if truth:
                    recalls[index].append(len(set(found) & set(truth)) / len(truth))

        notes = []
        if not info.indexed_vectors_count:
            notes.append(
                "No vector index is built yet (indexed_vectors_count is 0): approximate search "
                "is exact here, so recall is 1.0 by construction."
            )
        if not recalls[0]:
            notes.append("The collection has no other points to find: recall is undefined.")
        exact_p50, exact_p95 = _ms(exact_times)
        return SearchQualityReport(
            collection=collection_name,
            using=qdrant_using,
            points_count=info.points_count,
            indexed_vectors_count=info.indexed_vectors_count,
            queries=len(queries),
            limit=limit,
            exact_latency_ms_p50=exact_p50,
            exact_latency_ms_p95=exact_p95,
            variants=[
                VariantQuality(
                    search_params=params.model_dump(exclude_unset=True),
                    recall_mean=round(statistics.fmean(found), 3) if found else None,
                    recall_min=round(min(found), 3) if found else None,
                    latency_ms_p50=_ms(elapsed)[0],
                    latency_ms_p95=_ms(elapsed)[1],
                )
                for params, found, elapsed in zip(params_list, recalls, times, strict=True)
            ],
            notes=notes,
        )

    registry.register(qdrant_search_quality_eval, toolset="admin", annotations=_ANNOTATIONS)
