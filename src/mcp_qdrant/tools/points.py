"""The `core` toolset: points CRUD (upsert/get/delete/scroll/count)."""

from __future__ import annotations

from typing import Annotated, Any, Literal, cast

from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    CountResult,
    OrderBy,
    PointStruct,
    Record,
    UpdateMode,
    UpdateResult,
    VectorStruct,
)

from mcp_qdrant.tools.errors import call_qdrant
from mcp_qdrant.tools.points_shared import PointVectorValue, build_points_selector, page_offset
from mcp_qdrant.tools.registry import ToolRegistry
from mcp_qdrant.tools.schemas import FilterInput, StrictInput

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


class PointInput(StrictInput):
    """A point to upsert: id + vector(s) + payload. See `PointVectorValue`
    for the accepted vector shapes."""

    id: int | str
    vector: PointVectorValue
    payload: dict[str, Any] | None = None


class PointsGetResult(BaseModel):
    points: list[Record]


class PointsScrollResult(BaseModel):
    points: list[Record]
    next_page_offset: int | str | None


def register(registry: ToolRegistry, client: AsyncQdrantClient) -> None:
    async def qdrant_points_upsert(
        collection_name: str,
        points: Annotated[list[PointInput], Field(min_length=1)],
        wait: bool = True,
        update_mode: Literal["upsert", "insert_only", "update_only"] | None = None,
        update_filter: FilterInput | None = None,
    ) -> UpdateResult:
        """Insert or replace points (id + vector + payload) in a collection.

        `vector` matches the collection's vector config: a plain list for a
        single unnamed vector; a list of lists for an unnamed multivector;
        or a dict keyed by vector name for named vectors, where each value
        is a dense list, a multivector, or a sparse vector
        (`{"indices": [...], "values": [...]}`).

        `update_mode` makes the write conditional: `insert_only` never
        overwrites an existing id, `update_only` never creates a new one
        (default `upsert` does both). `update_filter` only overwrites existing
        points whose current payload matches the filter. `wait=false`
        returns before the write is applied.

        Fails with a clear error if the collection doesn't exist.

        Example: {"collection_name": "docs", "points": [
            {"id": 1, "vector": [0.1, 0.2, 0.3, 0.4], "payload": {"city": "ny"}}
        ]}
        Example (named dense + sparse): {"collection_name": "docs", "points": [
            {"id": 1, "vector": {"dense": [0.1, 0.2, 0.3, 0.4],
                "sparse": {"indices": [1, 7], "values": [0.5, 0.2]}}}
        ]}
        """
        # PointInput.vector is a narrower union than PointStruct.vector (excludes
        # Document/Image/InferenceObject); dict value types are invariant in mypy,
        # so a plain assignment doesn't widen it.
        structs = [
            PointStruct(id=p.id, vector=cast(VectorStruct, p.vector), payload=p.payload)
            for p in points
        ]
        mode = UpdateMode(update_mode) if update_mode is not None else None
        return await call_qdrant(
            lambda: client.upsert(
                collection_name,
                points=structs,
                wait=wait,
                update_mode=mode,
                update_filter=update_filter,
            )
        )

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
        registry.check_limit(len(ids), "the number of ids")
        records = await call_qdrant(
            lambda: client.retrieve(
                collection_name, ids=ids, with_payload=with_payload, with_vectors=with_vectors
            )
        )
        return PointsGetResult(points=records)

    async def qdrant_points_delete(
        collection_name: str,
        ids: list[int | str] | None = None,
        points_filter: FilterInput | None = None,
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
        scroll_filter: FilterInput | None = None,
        limit: Annotated[int, Field(gt=0)] = 10,
        offset: int | str | None = None,
        with_payload: bool = True,
        with_vectors: bool = False,
        order_by: OrderBy | str | None = None,
    ) -> PointsScrollResult:
        """Page through all points in a collection, optionally filtered.

        Pass the returned `next_page_offset` as `offset` to fetch the next
        page; `null` means there are no more pages. `limit` is capped per call
        by the server's QDRANT_MCP_MAX_LIMIT (1000 by default).

        `order_by` sorts by a payload field instead of by id: a key, or
        `{"key": ..., "direction": "asc"|"desc", "start_from": value}`; the key
        needs a payload range index (integer, float or datetime). Paging works
        differently then: `offset` is rejected, and `next_page_offset` is always
        `null` even when more points remain — to continue, repeat the call with
        `start_from` set to the last value you received (points tied on that
        value are returned again, so de-duplicate by id).

        Example: {"collection_name": "docs", "limit": 50}
        Example (newest first): {"collection_name": "docs", "limit": 20,
            "order_by": {"key": "created_at", "direction": "desc"}}
        """
        registry.check_limit(limit)
        records, next_offset = await call_qdrant(
            lambda: client.scroll(
                collection_name,
                scroll_filter=scroll_filter,
                limit=limit,
                offset=offset,
                with_payload=with_payload,
                with_vectors=with_vectors,
                order_by=order_by,
            )
        )
        return PointsScrollResult(points=records, next_page_offset=page_offset(next_offset))

    async def qdrant_points_count(
        collection_name: str, count_filter: FilterInput | None = None, exact: bool = True
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
