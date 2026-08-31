"""The `core` toolset: points CRUD (upsert/get/delete/scroll/count)."""

from __future__ import annotations

from typing import Annotated, Any

from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    CountResult,
    Filter,
    PointStruct,
    Record,
    UpdateResult,
)

from mcp_qdrant.tools.errors import call_qdrant
from mcp_qdrant.tools.points_shared import build_points_selector
from mcp_qdrant.tools.registry import ToolRegistry

_UPSERT_ANNOTATIONS = ToolAnnotations(
    title="Upsert Qdrant points",
    # Not purely additive per MCP spec: upserting an existing id replaces its
    # payload/vector, so this is destructive rather than read-only-adjacent.
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)
_GET_ANNOTATIONS = ToolAnnotations(
    title="Get Qdrant points by id",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_DELETE_ANNOTATIONS = ToolAnnotations(
    title="Delete Qdrant points",
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)
_SCROLL_ANNOTATIONS = ToolAnnotations(
    title="Scroll Qdrant points",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_COUNT_ANNOTATIONS = ToolAnnotations(
    title="Count Qdrant points",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)


class PointInput(BaseModel):
    """A point to upsert: a plain id + vector + payload — never `Document`,
    `Image`, or `InferenceObject` (qdrant-client's server-side embedding
    inference variants), which would contradict this server's principle of
    never generating embeddings itself."""

    id: int | str
    vector: list[float]
    payload: dict[str, Any] | None = None


class PointsGetResult(BaseModel):
    points: list[Record]


class PointsScrollResult(BaseModel):
    points: list[Record]
    next_page_offset: int | str | None


def register(registry: ToolRegistry, client: AsyncQdrantClient) -> None:
    async def qdrant_points_upsert(
        collection_name: str, points: Annotated[list[PointInput], Field(min_length=1)]
    ) -> UpdateResult:
        """Insert or replace points (id + vector + payload) in a collection.

        Fails with a clear error if the collection doesn't exist.

        Example: {"collection_name": "docs", "points": [
            {"id": 1, "vector": [0.1, 0.2, 0.3, 0.4], "payload": {"city": "ny"}}
        ]}
        """
        structs = [PointStruct(id=p.id, vector=p.vector, payload=p.payload) for p in points]
        return await call_qdrant(lambda: client.upsert(collection_name, points=structs))

    async def qdrant_points_get(
        collection_name: str,
        ids: Annotated[list[int | str], Field(min_length=1)],
        with_payload: bool = True,
        with_vectors: bool = False,
    ) -> PointsGetResult:
        """Retrieve points by id; unknown ids are simply omitted, not an error.

        Fails only if the collection itself doesn't exist.

        Example: {"collection_name": "docs", "ids": [1, 2]}
        """
        records = await call_qdrant(
            lambda: client.retrieve(
                collection_name, ids=ids, with_payload=with_payload, with_vectors=with_vectors
            )
        )
        return PointsGetResult(points=records)

    async def qdrant_points_delete(
        collection_name: str,
        ids: list[int | str] | None = None,
        points_filter: Filter | None = None,
    ) -> UpdateResult:
        """Delete points by id list or by payload filter — exactly one of the two.

        Deleting an id that doesn't exist is not an error (Qdrant treats it as
        a no-op); this only fails if the collection itself is missing, or if
        you provide zero or both selectors.

        Example (by id): {"collection_name": "docs", "ids": [1, 2]}
        Example (by filter): {"collection_name": "docs", "points_filter": {
            "must": [{"key": "city", "match": {"value": "ny"}}]
        }}
        """
        selector = build_points_selector(ids, points_filter)
        return await call_qdrant(lambda: client.delete(collection_name, points_selector=selector))

    async def qdrant_points_scroll(
        collection_name: str,
        scroll_filter: Filter | None = None,
        limit: Annotated[int, Field(gt=0)] = 10,
        offset: int | str | None = None,
        with_payload: bool = True,
        with_vectors: bool = False,
    ) -> PointsScrollResult:
        """Page through all points in a collection, optionally filtered.

        Pass the returned `next_page_offset` as `offset` to fetch the next
        page; `null` means there are no more pages.

        Example: {"collection_name": "docs", "limit": 50}
        """
        records, next_offset = await call_qdrant(
            lambda: client.scroll(
                collection_name,
                scroll_filter=scroll_filter,
                limit=limit,
                offset=offset,
                with_payload=with_payload,
                with_vectors=with_vectors,
            )
        )
        # The REST client only ever returns int/str/UUID/None here (never the
        # gRPC-only PointId protobuf variant, since this server never opts
        # into prefer_grpc) — stringify defensively rather than assume.
        next_offset_value: int | str | None
        if next_offset is None or isinstance(next_offset, int | str):
            next_offset_value = next_offset
        else:
            next_offset_value = str(next_offset)
        return PointsScrollResult(points=records, next_page_offset=next_offset_value)

    async def qdrant_points_count(
        collection_name: str, count_filter: Filter | None = None, exact: bool = True
    ) -> CountResult:
        """Count points in a collection, optionally matching a filter.

        Example: {"collection_name": "docs"}
        """
        return await call_qdrant(
            lambda: client.count(collection_name, count_filter=count_filter, exact=exact)
        )

    registry.register(qdrant_points_upsert, toolset="core", annotations=_UPSERT_ANNOTATIONS)
    registry.register(qdrant_points_get, toolset="core", annotations=_GET_ANNOTATIONS)
    registry.register(qdrant_points_delete, toolset="core", annotations=_DELETE_ANNOTATIONS)
    registry.register(qdrant_points_scroll, toolset="core", annotations=_SCROLL_ANNOTATIONS)
    registry.register(qdrant_points_count, toolset="core", annotations=_COUNT_ANNOTATIONS)
