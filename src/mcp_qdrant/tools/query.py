"""The `core` toolset: vector similarity search (the modern unified Query API)."""

from __future__ import annotations

from typing import Annotated

from mcp_types import ToolAnnotations
from pydantic import Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Filter, QueryResponse

from mcp_qdrant.tools.errors import call_qdrant
from mcp_qdrant.tools.query_shared import (
    FusionName,
    LookupFromInput,
    PrefetchInput,
    build_lookup_from,
    build_prefetch_list,
    build_query_value,
)
from mcp_qdrant.tools.registry import ToolRegistry

_QUERY_ANNOTATIONS = ToolAnnotations(
    title="Query Qdrant by vector similarity",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)


def register(registry: ToolRegistry, client: AsyncQdrantClient) -> None:
    async def qdrant_query(
        collection_name: str,
        query_vector: Annotated[list[float], Field(min_length=1)] | int | str | None = None,
        fusion: FusionName | None = None,
        prefetch: list[PrefetchInput] | None = None,
        using: str | None = None,
        lookup_from: LookupFromInput | None = None,
        query_filter: Filter | None = None,
        limit: Annotated[int, Field(gt=0)] = 10,
        with_payload: bool = True,
        with_vectors: bool = False,
    ) -> QueryResponse:
        """Vector similarity search, with optional hybrid search over
        multiple prefetch stages.

        Pass `query_vector` (a literal vector, or a point id to reuse an
        existing point's vector) for a plain nearest-vector query, or
        `fusion` + 2+ `prefetch` stages to combine multiple retrieval
        strategies via Reciprocal Rank Fusion (`fusion="rrf"`) or
        Distribution-Based Score Fusion (`fusion="dbsf"`) — exactly one of
        `query_vector`/`fusion` is required. `using` selects a named vector;
        `lookup_from` resolves `query_vector` from a point id in another
        collection instead of the current one. Fails with a clear error if
        the collection doesn't exist.

        Example (plain): {"collection_name": "docs", "query_vector": [0.1, 0.2, 0.3, 0.4],
            "limit": 5}
        Example (hybrid): {"collection_name": "docs", "fusion": "rrf", "prefetch": [
            {"query_vector": [0.1, 0.2, 0.3, 0.4], "using": "dense", "limit": 20},
            {"query_vector": [0.5, 0.5], "using": "sparse", "limit": 20}
        ], "limit": 5}
        """
        query = build_query_value(query_vector, fusion)
        return await call_qdrant(
            lambda: client.query_points(
                collection_name,
                query=query,
                using=using,
                prefetch=build_prefetch_list(prefetch),
                query_filter=query_filter,
                lookup_from=build_lookup_from(lookup_from),
                limit=limit,
                with_payload=with_payload,
                with_vectors=with_vectors,
            )
        )

    registry.register(qdrant_query, toolset="core", annotations=_QUERY_ANNOTATIONS)
