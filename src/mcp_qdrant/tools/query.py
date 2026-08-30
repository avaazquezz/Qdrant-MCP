"""The `core` toolset: vector similarity search (the modern unified Query API)."""

from __future__ import annotations

from typing import Annotated

from mcp_types import ToolAnnotations
from pydantic import Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Filter, QueryResponse

from mcp_qdrant.tools.errors import call_qdrant
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
        query_vector: Annotated[list[float], Field(min_length=1)],
        query_filter: Filter | None = None,
        limit: Annotated[int, Field(gt=0)] = 10,
        with_payload: bool = True,
        with_vectors: bool = False,
    ) -> QueryResponse:
        """Vector similarity search with an optional payload filter and limit.

        Scope: a single unnamed vector, no hybrid search (prefetch/fusion) —
        that lands in Fase 2. Fails with a clear error if the collection
        doesn't exist.

        Example: {"collection_name": "docs", "query_vector": [0.1, 0.2, 0.3, 0.4], "limit": 5}
        """
        return await call_qdrant(
            lambda: client.query_points(
                collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=with_payload,
                with_vectors=with_vectors,
            )
        )

    registry.register(qdrant_query, toolset="core", annotations=_QUERY_ANNOTATIONS)
