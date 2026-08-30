"""The `core` toolset: collection CRUD (create/list/info/update/delete/exists)."""

from __future__ import annotations

from typing import Annotated, Literal

from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    CollectionInfo,
    CollectionParamsDiff,
    CollectionsResponse,
    Distance,
    HnswConfigDiff,
    OptimizersConfigDiff,
    VectorParams,
)

from mcp_qdrant.tools.errors import call_qdrant
from mcp_qdrant.tools.registry import ToolRegistry

_CREATE_ANNOTATIONS = ToolAnnotations(
    title="Create Qdrant collection",
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=True,
)
_LIST_ANNOTATIONS = ToolAnnotations(
    title="List Qdrant collections",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_INFO_ANNOTATIONS = ToolAnnotations(
    title="Get Qdrant collection info",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_UPDATE_ANNOTATIONS = ToolAnnotations(
    title="Update Qdrant collection",
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
_DELETE_ANNOTATIONS = ToolAnnotations(
    title="Delete Qdrant collection",
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)
_EXISTS_ANNOTATIONS = ToolAnnotations(
    title="Check Qdrant collection existence",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)


class CollectionDeleteResult(BaseModel):
    """True if the collection existed and was removed; False is a no-op, not
    an error (verified against a real Qdrant instance: DELETE on a missing
    collection returns 200/false, not 404)."""

    deleted: bool


class CollectionExistsResult(BaseModel):
    exists: bool


def register(registry: ToolRegistry, client: AsyncQdrantClient) -> None:
    async def qdrant_collection_create(
        collection_name: str,
        vector_size: Annotated[int, Field(gt=0)],
        distance: Literal["Cosine", "Euclid", "Dot", "Manhattan"] = "Cosine",
    ) -> CollectionInfo:
        """Create a collection with a single unnamed vector (size + distance).

        Fails with a clear error if a collection with this name already exists.

        Example: {"collection_name": "docs", "vector_size": 4, "distance": "Cosine"}
        """
        await call_qdrant(
            lambda: client.create_collection(
                collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance(distance)),
            )
        )
        return await call_qdrant(lambda: client.get_collection(collection_name))

    async def qdrant_collection_list() -> CollectionsResponse:
        """List every collection name in the configured Qdrant instance.

        Example: {}
        """
        return await call_qdrant(lambda: client.get_collections())

    async def qdrant_collection_info(collection_name: str) -> CollectionInfo:
        """Return full config and status of one collection.

        Fails with a clear error if the collection doesn't exist.

        Example: {"collection_name": "docs"}
        """
        return await call_qdrant(lambda: client.get_collection(collection_name))

    async def qdrant_collection_update(
        collection_name: str,
        optimizers_config: OptimizersConfigDiff | None = None,
        hnsw_config: HnswConfigDiff | None = None,
        collection_params: CollectionParamsDiff | None = None,
    ) -> CollectionInfo:
        """Update optimizer/HNSW/collection params on an existing collection.

        Only the fields you pass are changed; omitted ones keep their current
        value. Fails with a clear error if the collection doesn't exist.

        Example: {"collection_name": "docs", "optimizers_config": {"indexing_threshold": 10000}}
        """
        await call_qdrant(
            lambda: client.update_collection(
                collection_name,
                optimizers_config=optimizers_config,
                hnsw_config=hnsw_config,
                collection_params=collection_params,
            )
        )
        return await call_qdrant(lambda: client.get_collection(collection_name))

    async def qdrant_collection_delete(collection_name: str) -> CollectionDeleteResult:
        """Delete a collection and all its points; a no-op if it doesn't exist.

        Example: {"collection_name": "docs"}
        """
        deleted = await call_qdrant(lambda: client.delete_collection(collection_name))
        return CollectionDeleteResult(deleted=deleted)

    async def qdrant_collection_exists(collection_name: str) -> CollectionExistsResult:
        """Check whether a collection exists, without raising if it doesn't.

        Example: {"collection_name": "docs"}
        """
        exists = await call_qdrant(lambda: client.collection_exists(collection_name))
        return CollectionExistsResult(exists=exists)

    registry.register(qdrant_collection_create, toolset="core", annotations=_CREATE_ANNOTATIONS)
    registry.register(qdrant_collection_list, toolset="core", annotations=_LIST_ANNOTATIONS)
    registry.register(qdrant_collection_info, toolset="core", annotations=_INFO_ANNOTATIONS)
    registry.register(qdrant_collection_update, toolset="core", annotations=_UPDATE_ANNOTATIONS)
    registry.register(qdrant_collection_delete, toolset="core", annotations=_DELETE_ANNOTATIONS)
    registry.register(qdrant_collection_exists, toolset="core", annotations=_EXISTS_ANNOTATIONS)
