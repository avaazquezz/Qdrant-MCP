"""The `core` toolset: search through Qdrant's unified Query API."""

from __future__ import annotations

from typing import Annotated, Literal

from mcp_types import ToolAnnotations
from pydantic import Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Filter, OrderBy, QueryResponse, SearchParams

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

_QUERY_ANNOTATIONS = ToolAnnotations(
    title="Query Qdrant",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)


def register(registry: ToolRegistry, client: AsyncQdrantClient) -> None:
    async def qdrant_query(
        collection_name: str,
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
        offset: OffsetInput | None = None,
        with_payload: bool = True,
        with_vectors: bool = False,
        timeout_seconds: TimeoutSeconds | None = None,
        consistency: ConsistencyInput | None = None,
    ) -> QueryResponse:
        """Search a collection with Qdrant's unified Query API: vector
        similarity, hybrid fusion, multi-stage reranking, MMR diversity,
        payload-based score formulas, ordering by a payload field, or random
        sampling.

        Exactly one query mode is required:
        - `query_vector` — nearest points to a dense vector, a multivector (list
          of vectors), a sparse vector (`{"indices": [...], "values": [...]}`),
          or a point id whose stored vector is reused. It must match the vector
          selected with `using`. Add `mmr` (`diversity` 0..1,
          `candidates_limit`) to re-order the nearest candidates for diversity:
          set `candidates_limit` well above `limit` (it defaults to `limit`,
          which leaves MMR nothing to choose from), and don't page an MMR query
          with `offset` — it is applied inside the `limit` re-ranked results
          (`offset` 1 with `limit` 2 returns one point); raise `limit` instead.
        - `fusion` + 2+ `prefetch` stages — combine retrieval strategies:
          `"rrf"` (Reciprocal Rank Fusion), `"dbsf"` (Distribution-Based Score
          Fusion), or `{"method": "rrf", "weights": [2, 1], "k": 60}` for RRF
          with one weight per stage (a count that doesn't match the stages is
          rejected by Qdrant).
        - `formula` — rescore the results of `prefetch` stages (required: a
          formula without prefetch is rejected). `{"expression": ..., "defaults":
          {...}}`. An expression is a number; a variable (`"$score"` is the
          prefetch score, any other string is a payload key); a payload
          condition (e.g. `{"key": "city", "match": {"value": "sf"}}`, worth 1
          if it matches, else 0); or exactly one operator object: `{"sum":
          [...]}`, `{"mult": [...]}`, `{"neg": e}`, `{"abs": e}`, `{"div":
          {"left": e, "right": e}}`, `{"sqrt": e}`, `{"pow": {"base": e,
          "exponent": e}}`, `{"exp": e}`, `{"ln": e}`, `{"log10": e}`,
          `{"geo_distance": {"origin": {"lat": .., "lon": ..}, "to":
          "payload.key"}}`, `{"datetime": "2026-01-01T00:00:00Z"}`,
          `{"datetime_key": "payload.key"}`, and the decays `{"exp_decay" |
          "gauss_decay" | "lin_decay": {"x": e, "target": e, "scale": number,
          "midpoint": number}}`. A payload key a point lacks needs a value in
          `defaults`, or Qdrant rejects the query.
        - `order_by` — sort by a payload field instead of by similarity: a key
          or `{"key": ..., "direction": "asc"|"desc", "start_from": value}`.
          The key needs a payload range index (integer, float or datetime).
        - `sample: "random"` — random points.

        A `prefetch` stage is itself a `query_vector` query or a `fusion` of
        its own nested `prefetch` stages, so pipelines nest: fuse dense+sparse
        in one stage, then rerank with a multivector. `using` selects a named
        vector; `lookup_from` resolves `query_vector` from a point id in
        another collection.

        Tuning: `search_params` (`hnsw_ef`, `exact` for brute force,
        `quantization`: `ignore`/`rescore`/`oversampling`, `indexed_only`,
        `acorn`), `score_threshold` (drop weaker hits), `limit` + `offset`
        (paging), `timeout_seconds` (server-side), and `consistency` (a replica count, or
        `"majority"`/`"quorum"`/`"all"`; only meaningful on a replicated
        deployment). Fails with a clear error if the collection doesn't exist.

        Example (plain): {"collection_name": "docs", "query_vector": [0.1, 0.2, 0.3, 0.4],
            "limit": 5}
        Example (hybrid): {"collection_name": "docs", "fusion": "rrf", "prefetch": [
            {"query_vector": [0.1, 0.2, 0.3, 0.4], "using": "dense", "limit": 20},
            {"query_vector": {"indices": [1, 7], "values": [0.5, 0.2]}, "using": "sparse",
                "limit": 20}
        ], "limit": 5}
        Example (diverse results): {"collection_name": "docs", "query_vector": [0.1, 0.2, 0.3, 0.4],
            "mmr": {"diversity": 0.5, "candidates_limit": 50}, "limit": 5}
        Example (boost one city): {"collection_name": "docs", "prefetch": [
            {"query_vector": [0.1, 0.2, 0.3, 0.4], "limit": 50}
        ], "formula": {"expression": {"sum": ["$score",
            {"mult": [0.5, {"key": "city", "match": {"value": "sf"}}]}]}}, "limit": 5}
        Example (cheapest first): {"collection_name": "docs", "order_by": {"key": "price",
            "direction": "asc"}, "limit": 5}
        """
        query = build_query_value(
            query_vector, fusion, mmr=mmr, formula=formula, order_by=order_by, sample=sample
        )
        return await call_qdrant(
            lambda: client.query_points(
                collection_name,
                query=query,
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

    registry.register(qdrant_query, toolset="core", annotations=_QUERY_ANNOTATIONS)
