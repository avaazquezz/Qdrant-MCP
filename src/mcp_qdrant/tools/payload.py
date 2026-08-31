"""The `payload` toolset (Fase 3, part 1): payload value CRUD and payload
indexing. See `vectors.py` for the rest of this toolset (batch updates and
named-vector operations).
"""

from __future__ import annotations

from typing import Any

from mcp_types import ToolAnnotations
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    BoolIndexParams,
    DatetimeIndexParams,
    FacetResponse,
    Filter,
    FloatIndexParams,
    GeoIndexParams,
    IntegerIndexParams,
    KeywordIndexParams,
    PayloadSchemaType,
    TextIndexParams,
    UpdateResult,
    UuidIndexParams,
)

from mcp_qdrant.tools.errors import call_qdrant
from mcp_qdrant.tools.points_shared import build_points_selector
from mcp_qdrant.tools.registry import ToolRegistry

PayloadIndexSchema = (
    PayloadSchemaType
    | KeywordIndexParams
    | IntegerIndexParams
    | FloatIndexParams
    | GeoIndexParams
    | TextIndexParams
    | BoolIndexParams
    | DatetimeIndexParams
    | UuidIndexParams
)

_SET_ANNOTATIONS = ToolAnnotations(
    title="Set Qdrant payload fields",
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_OVERWRITE_ANNOTATIONS = ToolAnnotations(
    title="Overwrite Qdrant payload",
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)
_DELETE_ANNOTATIONS = ToolAnnotations(
    title="Delete Qdrant payload keys",
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)
_CLEAR_ANNOTATIONS = ToolAnnotations(
    title="Clear Qdrant payload",
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)
_FACET_ANNOTATIONS = ToolAnnotations(
    title="Facet-count a Qdrant payload field",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_INDEX_CREATE_ANNOTATIONS = ToolAnnotations(
    title="Create a Qdrant payload index",
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_INDEX_DELETE_ANNOTATIONS = ToolAnnotations(
    title="Delete a Qdrant payload index",
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)


def register(registry: ToolRegistry, client: AsyncQdrantClient) -> None:
    async def qdrant_payload_set(
        collection_name: str,
        payload: dict[str, Any],
        ids: list[int | str] | None = None,
        points_filter: Filter | None = None,
        key: str | None = None,
    ) -> UpdateResult:
        """Merge fields into the payload of selected points — exactly one of
        `ids`/`points_filter`. Existing keys not in `payload` are kept.
        `key` sets a nested sub-field (e.g. `"metadata.author"`) instead of
        merging at the payload root.

        Example: {"collection_name": "docs", "ids": [1], "payload": {"city": "ny"}}
        """
        selector = build_points_selector(ids, points_filter)
        return await call_qdrant(
            lambda: client.set_payload(collection_name, payload=payload, points=selector, key=key)
        )

    async def qdrant_payload_overwrite(
        collection_name: str,
        payload: dict[str, Any],
        ids: list[int | str] | None = None,
        points_filter: Filter | None = None,
    ) -> UpdateResult:
        """Replace the entire payload of selected points with `payload` —
        exactly one of `ids`/`points_filter`. Unlike `qdrant_payload_set`,
        existing keys not in `payload` are dropped.

        Example: {"collection_name": "docs", "ids": [1], "payload": {"city": "ny"}}
        """
        selector = build_points_selector(ids, points_filter)
        return await call_qdrant(
            lambda: client.overwrite_payload(collection_name, payload=payload, points=selector)
        )

    async def qdrant_payload_delete(
        collection_name: str,
        keys: list[str],
        ids: list[int | str] | None = None,
        points_filter: Filter | None = None,
    ) -> UpdateResult:
        """Delete specific payload keys from selected points — exactly one
        of `ids`/`points_filter`. Other keys are untouched.

        Example: {"collection_name": "docs", "ids": [1], "keys": ["city"]}
        """
        selector = build_points_selector(ids, points_filter)
        return await call_qdrant(
            lambda: client.delete_payload(collection_name, keys=keys, points=selector)
        )

    async def qdrant_payload_clear(
        collection_name: str,
        ids: list[int | str] | None = None,
        points_filter: Filter | None = None,
    ) -> UpdateResult:
        """Wipe the entire payload of selected points, keeping their
        vectors — exactly one of `ids`/`points_filter`.

        Example: {"collection_name": "docs", "ids": [1]}
        """
        selector = build_points_selector(ids, points_filter)
        return await call_qdrant(
            lambda: client.clear_payload(collection_name, points_selector=selector)
        )

    async def qdrant_payload_facet(
        collection_name: str,
        key: str,
        facet_filter: Filter | None = None,
        limit: int = 10,
        exact: bool = False,
    ) -> FacetResponse:
        """Count distinct values of a payload field across the collection
        (or a filtered subset) — e.g. how many points per `city`. `exact`
        trades speed for an exact count instead of an approximation.

        Example: {"collection_name": "docs", "key": "city", "limit": 20}
        """
        return await call_qdrant(
            lambda: client.facet(
                collection_name, key=key, facet_filter=facet_filter, limit=limit, exact=exact
            )
        )

    async def qdrant_payload_index_create(
        collection_name: str, field_name: str, field_schema: PayloadIndexSchema
    ) -> UpdateResult:
        """Create a payload index on `field_name`, speeding up filters that
        use it. `field_schema` can be a simple type name ("keyword",
        "integer", "float", "geo", "text", "bool", "datetime", "uuid") or a
        detailed params object (e.g. a `text` index with a specific
        tokenizer, or a `keyword` index marked `is_tenant`).

        Example: {"collection_name": "docs", "field_name": "city", "field_schema": "keyword"}
        """
        return await call_qdrant(
            lambda: client.create_payload_index(
                collection_name, field_name=field_name, field_schema=field_schema
            )
        )

    async def qdrant_payload_index_delete(collection_name: str, field_name: str) -> UpdateResult:
        """Delete the payload index on `field_name`.

        Example: {"collection_name": "docs", "field_name": "city"}
        """
        return await call_qdrant(
            lambda: client.delete_payload_index(collection_name, field_name=field_name)
        )

    registry.register(qdrant_payload_set, toolset="payload", annotations=_SET_ANNOTATIONS)
    registry.register(
        qdrant_payload_overwrite, toolset="payload", annotations=_OVERWRITE_ANNOTATIONS
    )
    registry.register(qdrant_payload_delete, toolset="payload", annotations=_DELETE_ANNOTATIONS)
    registry.register(qdrant_payload_clear, toolset="payload", annotations=_CLEAR_ANNOTATIONS)
    registry.register(qdrant_payload_facet, toolset="payload", annotations=_FACET_ANNOTATIONS)
    registry.register(
        qdrant_payload_index_create, toolset="payload", annotations=_INDEX_CREATE_ANNOTATIONS
    )
    registry.register(
        qdrant_payload_index_delete, toolset="payload", annotations=_INDEX_DELETE_ANNOTATIONS
    )
